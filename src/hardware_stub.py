"""Stubs de hardware (PPU registers e controllers) simples para integração NES-lite.

- Mapeia $2000-$2007 (PPU registers) com mirror até $3FFF (every 8 bytes).
- Mapeia $4016/$4017 (controllers) com handlers simples (lê sempre 0) e aceita escritos para latch.

Esses stubs não implementam PPU real, apenas previnem crashes e permitem que ROMs que testem I/O
não escrevam na RAM ou causem exceções durante leitura.
"""


class SimpleHardware:
    def __init__(self):
        self.controller_latch = 0
        # controller_state armazena o estado atual de 8 bits para cada controle (botões)
        # bits: A, B, Select, Start, Cima, Baixo, Esquerda, Direita (geralmente mapeados de forma diferente por ROM)
        self.controller_state = [0x00, 0x00]  # 2 controles
        self.ppu = None
        self._ppu_read_count = 0
        # flag 'verbose' para controlar a saída de depuração
        self.verbose = False
        self._shift_regs = [0x00, 0x00]

    def map_to_bus(self, bus):
        # Compatibilidade retroativa: se o barramento tiver o atributo 'ppu', use-o
        if hasattr(bus, 'ppu') and getattr(bus, 'ppu') is not None:
            self.ppu = getattr(bus, 'ppu')

        # Mapear PPU registers (mirror every 8 bytes from 0x2000..0x3FFF)
        def ppu_read(addr):
            if self.ppu:
                try:
                    val = self.ppu.ppu_read_register(addr)
                    try:
                        if not hasattr(self, '_ppu_read_count'):
                            self._ppu_read_count = 0
                        self._ppu_read_count += 1
                        pc = getattr(bus, '_last_instr_pc', None)
                        try:
                            import logging
                            _logger = logging.getLogger(__name__)
                        except Exception:
                            _logger = None
                        if self.verbose and self._ppu_read_count <= 100:
                            if pc is None:
                                if _logger:
                                    _logger.debug(
                                        f"SimpleHardware: PPU read addr=${addr:04X} -> ${val:02X}")
                                else:
                                    # fallback
                                    print(
                                        f"SimpleHardware: PPU read addr=${addr:04X} -> ${val:02X}")
                            else:
                                if _logger:
                                    _logger.debug(
                                        f"SimpleHardware: PPU read addr=${addr:04X} -> ${val:02X} (instr @ ${pc:04X})")
                                else:
                                    print(
                                        f"SimpleHardware: PPU read addr=${addr:04X} -> ${val:02X} (instr @ ${pc:04X})")
                        elif self._ppu_read_count == 101:
                            if self.verbose:
                                if _logger:
                                    _logger.debug(
                                        "SimpleHardware: further PPU read logs suppressed")
                                else:
                                    print(
                                        "SimpleHardware: further PPU read logs suppressed")
                    except Exception:
                        pass
                    return val
                except Exception:
                    return 0
            return 0

        def ppu_write(addr, val):
            if self.ppu:
                try:
                    self.ppu.ppu_write_register(addr, val)
                    return
                except Exception:
                    pass
            return

        # instalamos handlers para a faixa 0x2000-0x3FFF
        bus.map_region(0x2000, 0x3FFF, read_fn=ppu_read, write_fn=ppu_write)

        # Mapear controllers: $4016 (write: latch), $4016/$4017 read return serial
        def controller_write(_, val):
            # Escritas em $4016: o bit0 (latch) quando definido como 1; quando 0 o controle está pronto para ser lido
            # Na transição de 1 para 0, devemos carregar os registradores de deslocamento com o estado do controle
            prev = self.controller_latch
            self.controller_latch = val & 1
            if prev == 1 and self.controller_latch == 0:
                # latch: carregar os registradores de deslocamento (iremos deslocar nos reads)
                # copiar controller_state para uma lista mutável de bits convertendo para int
                self._shift_regs = [
                    self.controller_state[0], self.controller_state[1]]

        def dma_write(_, val):
            if self.ppu and hasattr(self.ppu, 'oam_dma'):
                try:
                    self.ppu.oam_dma(bus, val)
                except Exception:
                    pass
            return

        def controller_read(addr):
            idx = 0 if addr == 0x4016 else 1
            if not hasattr(self, '_shift_regs'):
                self._shift_regs = [
                    self.controller_state[0], self.controller_state[1]]
            val = self._shift_regs[idx] & 1
            self._shift_regs[idx] = (self._shift_regs[idx] >> 1) | 0x80
            return val

        bus.map_region(0x4016, 0x4016, read_fn=controller_read,
                       write_fn=controller_write)
        bus.map_region(0x4017, 0x4017, read_fn=controller_read, write_fn=None)
        bus.map_region(0x4014, 0x4014, read_fn=None, write_fn=dma_write)

        # Também podemos mapear APU e I/O se necessário no futuro
        return (0x2000, 0x3FFF)
