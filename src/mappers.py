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


class UNROMMapper:
    """Mapper 2 (UNROM/UXROM) básico.

    - PRG is arranged in 16KB banks.
    - $8000-$BFFF is the switchable bank (selectable via write to $8000-$FFFF).
    - $C000-$FFFF is fixed to the last bank.
    - Writes to the bank select range will update the bank mapping.
    """
    def __init__(self, prg_bytes: bytes):
        self.prg = bytes(prg_bytes)
        self.prg_size = len(self.prg)
        self.bank_count = max(1, self.prg_size // 0x4000)
        # Current bank number mapped at $8000-$BFFF (0-based)
        self.cur_bank = 0
        # PRG-RAM 8KB at $6000-$7FFF
        self.prg_ram = bytearray(0x2000)

    def map(self, bus):
        # PRG-RAM handlers
        def prg_ram_read(addr):
            return self.prg_ram[addr - 0x6000]

        def prg_ram_write(addr, val):
            self.prg_ram[addr - 0x6000] = val & 0xFF

        bus.map_region(0x6000, 0x7FFF, read_fn=prg_ram_read,
                       write_fn=prg_ram_write)

        # Read handler for $8000-$BFFF (switchable bank)
        def read_bank_switchable(addr):
            offset_in_bank = addr - 0x8000
            bank = self.cur_bank % self.bank_count
            global_offset = bank * 0x4000 + offset_in_bank
            if 0 <= global_offset < self.prg_size:
                return self.prg[global_offset]
            return 0xFF

        # Read handler for $C000-$FFFF (fixed to last bank)
        def read_bank_fixed(addr):
            offset_in_bank = addr - 0xC000
            bank = max(0, self.bank_count - 1)
            global_offset = bank * 0x4000 + offset_in_bank
            if 0 <= global_offset < self.prg_size:
                return self.prg[global_offset]
            return 0xFF

        bus.map_region(0x8000, 0xBFFF, read_fn=read_bank_switchable, write_fn=None)
        bus.map_region(0xC000, 0xFFFF, read_fn=read_bank_fixed, write_fn=None)

        # Writes to $8000-$FFFF select bank (lower bits)
        def bank_select_write(addr, val):
            # Typical UNROM: lower 3 bits select bank; but we'll allow full value
            try:
                new_bank = val & 0xFF
                # clamp to available banks
                new_bank = new_bank % max(1, self.bank_count)
                if new_bank != self.cur_bank:
                    self.cur_bank = new_bank
                    # notify bus/GUI if callback present
                    try:
                        if hasattr(bus, 'mapper_write_callback') and callable(getattr(bus, 'mapper_write_callback')):
                            try:
                                bus.mapper_write_callback()
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

        # Install write handler for the whole PRG area to catch bank selects
        bus.map_region(0x8000, 0xFFFF, read_fn=None, write_fn=bank_select_write)

    def __repr__(self):
        return f"UNROMMapper(prg_size={self.prg_size}, banks={self.bank_count}, cur_bank={self.cur_bank})"
