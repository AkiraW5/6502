from typing import Optional


class Bus:
    """Representa o barramento de memória, conectando CPU, RAM e dispositivos.

    Suporta mapeamento de regiões através de handlers de leitura/escrita.
    Se nenhum handler corresponder, acessa a RAM interna (64KB).
    """

    def __init__(self):
        self.ram = bytearray(64 * 1024)
        self.mapped_regions = []
        self.write_logger_enabled = False
        self.write_log_range = (0x0000, 0xFFFF)
        self.write_log = []
        self.ppu: Optional[object] = None
        # callback para mudanças de mapper (por exemplo, bank switch)
        self.mapper_write_callback = None
        # Mapeia $4014 para DMA do OAM
        def oam_dma_handler(addr, value):
            print(f"[Bus.write] DMA solicitado em $4014 com value={value}")
            if self.ppu:
                print(f"[Bus.write] Tipo da PPU: {type(self.ppu)}")
            if self.ppu and hasattr(self.ppu, 'oam_dma'):
                self.ppu.oam_dma(self, value)
        self.map_region(0x4014, 0x4014, None, oam_dma_handler)

    def map_region(self, start: int, end: int, read_fn=None, write_fn=None):
        """Registra um handler para a faixa [start, end] (inclusive).

        read_fn: callable(address) -> byte
        write_fn: callable(address, value) -> None
        """
        start &= 0xFFFF
        end &= 0xFFFF
        if end < start:
            raise ValueError("endereço final deve ser >= início")
        self.mapped_regions.append((start, end, read_fn, write_fn))

    def install_mapper(self, mapper):
        """Instala um mapper que implementa método map(bus).

        O mapper deve chamar bus.map_region para instalar seus handlers.
        """
        if hasattr(mapper, 'map'):
            mapper.map(self)

    def load_cartridge(self, cartridge):
        """Instala um cartucho/cartridge no barramento via seu mapper (se houver)."""
        mapper_obj = None
        if hasattr(cartridge, 'mapper_obj'):
            mapper_obj = cartridge.mapper_obj
        elif hasattr(cartridge, 'mapper') and not isinstance(cartridge.mapper, int):
            mapper_obj = cartridge.mapper
        elif hasattr(cartridge, 'get_mapper') and callable(cartridge.get_mapper):
            mapper_obj = cartridge.get_mapper()

        if mapper_obj is not None:
            try:
                self.install_mapper(mapper_obj)
            except Exception:
                pass

    def write_reset_vector(self, address: int):
        """Escreve o vetor de reset em $FFFC/$FFFD apontando para address (16-bit)."""
        low = address & 0xFF
        high = (address >> 8) & 0xFF
        self.write(0xFFFC, low)
        self.write(0xFFFD, high)

    def _find_region(self, address: int, mode: str = 'read'):
        """Encontra a região que corresponde ao endereço.

        mode: 'read' ou 'write' determina a preferência por handlers que
        suportam a operação (read_fn ou write_fn). Se não encontrar um
        handler específico para a operação, retorna a primeira região que
        cobre o endereço.
        """
        address &= 0xFFFF
        # Prefer regions that explicitly provide the requested handler
        if mode == 'read':
            for start, end, read_fn, write_fn in self.mapped_regions:
                if start <= address <= end and read_fn is not None:
                    return (start, end, read_fn, write_fn)
        elif mode == 'write':
            for start, end, read_fn, write_fn in self.mapped_regions:
                if start <= address <= end and write_fn is not None:
                    return (start, end, read_fn, write_fn)
        # Fallback: return first matching region regardless of handler
        for start, end, read_fn, write_fn in self.mapped_regions:
            if start <= address <= end:
                return (start, end, read_fn, write_fn)
        return None

    def read(self, address: int) -> int:
        """Lê um byte da memória no endereço especificado."""
        address &= 0xFFFF
        region = self._find_region(address, mode='read')
        if region and region[2]:
            return region[2](address) & 0xFF
        return self.ram[address]

    def read_word(self, address: int) -> int:
        """Lê uma palavra (16 bits, little-endian) da memória."""
        address &= 0xFFFF
        low = self.read(address)
        high = self.read((address + 1) & 0xFFFF)
        return (high << 8) | low

    def write(self, address: int, value: int):
        """Escreve um byte na memória no endereço especificado."""
        address &= 0xFFFF
        value &= 0xFF
        region = self._find_region(address, mode='write')
        if self.write_logger_enabled:
            start, end = self.write_log_range
            if start <= address <= end:
                try:
                    instr_pc = None
                    try:
                        instr_pc = getattr(self, '_last_instr_pc', None)
                    except Exception:
                        instr_pc = None
                    self.write_log.append((address, value, instr_pc))
                except Exception:
                    pass
        # Log detalhado das escritas na faixa $0200-$02FF
        if 0x0200 <= address <= 0x02FF:
            import json, os
            log_path = os.path.join(os.getcwd(), 'ram_write_log_02.json')
            try:
                with open(log_path, 'a', encoding='utf-8') as jf:
                    json.dump({'address': address, 'value': value}, jf)
                    jf.write('\n')
            except Exception as e:
                print(f"[Bus.write] Falha ao logar escrita em $02xx: {e}")
        if region and region[3]:
            region[3](address, value)
            return
        # If mapped region exists but has no write handler, behave as RAM
        self.ram[address] = value

    def enable_write_logging(self, start: int = 0x0000, end: int = 0xFFFF):
        """Ativa logging de gravações na faixa [start, end]."""
        self.write_logger_enabled = True
        self.write_log_range = (start & 0xFFFF, end & 0xFFFF)

    def disable_write_logging(self):
        self.write_logger_enabled = False

    def get_write_log(self):
        """Retorna uma cópia do log de gravações."""
        return list(self.write_log)

    def set_mapper_callback(self, fn):
        """Registra uma função a ser chamada quando o mapper realiza uma ação que
        deva provocar atualização de UI (ex: troca de banco)."""
        self.mapper_write_callback = fn

    def clear_write_log(self):
        """Limpa o log de gravações."""
        self.write_log.clear()
