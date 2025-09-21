"""Mappers simples para NES — atualmente implementa apenas NROM (PRG mapping).

NROM: PRG ROM de 16KB ou 32KB mapeada em $8000-$FFFF. Se 16KB, espelha em $C000.
"""
from typing import Callable


class NROMMapper:
    def __init__(self, prg_bytes: bytes):
        self.prg = bytes(prg_bytes)
        self.size = len(self.prg)
        # PRG-RAM (8KB) mapped at $6000-$7FFF for saves or work RAM
        self.prg_ram = bytearray(0x2000)

    def map(self, bus):
        """Instala handlers no bus para mapear leituras de CPU em $8000-$FFFF."""
        # Map PRG-RAM at $6000-$7FFF readable/writable
        def prg_ram_read(addr):
            offset = addr - 0x6000
            return self.prg_ram[offset]

        def prg_ram_write(addr, val):
            offset = addr - 0x6000
            self.prg_ram[offset] = val & 0xFF

        bus.map_region(0x6000, 0x7FFF, read_fn=prg_ram_read,
                       write_fn=prg_ram_write)
        if self.size == 16384:
            # 16KB PRG: mapear $8000-$BFFF e espelhar em $C000-$FFFF
            def read_low(addr):
                offset = addr - 0x8000
                return self.prg[offset]

            def read_high(addr):
                offset = addr - 0xC000
                return self.prg[offset]

            bus.map_region(0x8000, 0xBFFF, read_fn=read_low, write_fn=None)
            bus.map_region(0xC000, 0xFFFF, read_fn=read_high, write_fn=None)
        else:
            # Mapeia sequencialmente a partir de 0x8000 (suporta 32KB PRG)
            def make_read(offset_base):
                def _read(addr):
                    offset = addr - 0x8000 + offset_base
                    if 0 <= offset < self.size:
                        return self.prg[offset]
                    return 0
                return _read

            # mapear todo o PRG a partir de 0x8000 (até 0xFFFF)
            bus.map_region(0x8000, 0xFFFF, read_fn=make_read(0), write_fn=None)

        # ROMs PRG são somente leitura; ignoramos writes
        def write_ignore(addr, val):
            # Ignora escrita em ROM
            return

        # Instalar handlers de escrita para evitar escrita direta na RAM
        bus.map_region(0x8000, 0xFFFF, read_fn=None, write_fn=write_ignore)

    def __repr__(self):
        return f"NROMMapper(prg_size={self.size})"
