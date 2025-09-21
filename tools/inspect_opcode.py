from src.Cpu import CPU
from src.Bus import Bus
from src.mappers import NROMMapper
import sys
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def inspect(rom_path, addr=0x8004):
    data = open(rom_path, 'rb').read()
    prg_units = data[4]
    trainer = (data[6] & 4) != 0
    prg_start = 16 + (512 if trainer else 0)
    prg_size = prg_units * 16384
    prg = data[prg_start: prg_start + prg_size]

    bus = Bus()
    cpu = CPU(bus)
    mapper = NROMMapper(prg)
    mapper.map(bus)
    load_addr = 0x8000
    for i, b in enumerate(prg):
        bus.write(load_addr + i, b)

    cpu.reset()
    opcode = bus.read(addr)
    instr_func, mode, cycles = cpu.lookup[opcode]
    mode_name = mode.__name__ if hasattr(mode, '__name__') else str(mode)
    print(
        f'opcode ${opcode:02X} at ${addr:04X} -> {instr_func.__name__} mode={mode_name} cycles={cycles}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: inspect_opcode.py path/to/rom.nes [addr]')
        sys.exit(1)
    rom = sys.argv[1]
    addr = int(sys.argv[2], 0) if len(sys.argv) >= 3 else 0x8004
    inspect(rom, addr)
