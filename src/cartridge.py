class Cartridge:
    """Representa uma ROM de cartucho simples com PRG e CHR.

    Atributos esperados:
    - prg: bytes ou bytearray contendo PRG ROM
    - chr: bytes ou bytearray contendo CHR ROM (não usado aqui)
    - mapper: número do mapper (suportamos 0 = NROM)
    - prg_size: tamanho em bytes de PRG
    """
    def __init__(self, prg: bytes, chr: bytes = b'', mapper: int = 0):
        self.prg = bytearray(prg)
        self.chr = bytearray(chr)
        self.mapper = mapper
        self.prg_size = len(self.prg)
        self.mapper_obj = None
        if self.mapper == 0:
            try:
                self.mapper_obj = NROMMapper(self)
            except Exception:
                self.mapper_obj = None


class NROMMapper:
    """Mapper NROM (mapper 0) mínimo.

    Mapeamento simplificado:
    - PRG 16KB: espelhado em $8000-$BFFF e $C000-$FFFF
    - PRG 32KB: carregado em $8000-$FFFF
    - PPU registers ($2000-$2007) espelhados até $3FFF (mirror every 8)
    - RAM $0000-$07FF espelhada em $0000-$1FFF
    - APU/IO $4000-$4017: stubs (reads return 0, writes ignored)

    Este mapper fornece handlers para bus.map_region.
    """
    def __init__(self, cartridge: Cartridge):
        self.cart = cartridge

    def map(self, bus):
        # RAM $0000-$07FF espelhada em $0000-$1FFF (espelha a cada 2KB)
        def ram_read(addr):
            return bus.ram[addr & 0x07FF]
        def ram_write(addr, val):
            bus.ram[addr & 0x07FF] = val & 0xFF
        bus.map_region(0x0000, 0x1FFF, read_fn=ram_read, write_fn=ram_write)

        # PPU registers $2000-$2007 mirrored to $2000-$3FFF (mirror every 8)
        def ppu_read(addr):
            # stub: retorna 0
            return 0
        def ppu_write(addr, val):
            # stub: ignora
            return
        bus.map_region(0x2000, 0x3FFF, read_fn=ppu_read, write_fn=ppu_write)

        # APU/IO $4000-$4017: stubs
        def apu_read(addr):
            return 0
        def apu_write(addr, val):
            return
        bus.map_region(0x4000, 0x4017, read_fn=apu_read, write_fn=apu_write)

        # Mapeamento da PRG ROM
        prg = self.cart.prg
        if len(prg) == 0:
            # nada para mapear
            return
        if len(prg) == 0x4000:  # 16KB
            # espelha 16KB em 0x8000-0xBFFF e 0xC000-0xFFFF
            def prg_read_16(addr):
                offset = addr - 0x8000
                offset = offset & 0x3FFF
                return prg[offset]
            bus.map_region(0x8000, 0xFFFF, read_fn=prg_read_16, write_fn=None)
        else:
            # assume 32KB ou maior; mapeia os primeiros 32KB em 0x8000-0xFFFF
            def prg_read_32(addr):
                offset = addr - 0x8000
                offset = offset & 0x7FFF
                return prg[offset]
            bus.map_region(0x8000, 0xFFFF, read_fn=prg_read_32, write_fn=None)
