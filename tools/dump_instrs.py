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


def format_operand(bus, cpu, addr, mode_fn):
    try:
        if mode_fn == cpu.IMM:
            v = bus.read(addr+1)
            return f"#${v:02X}"
        if mode_fn == cpu.ZP0:
            v = bus.read(addr+1)
            return f"${v:02X}"
        if mode_fn == cpu.ZPX:
            v = bus.read(addr+1)
            return f"${v:02X},X"
        if mode_fn == cpu.ZPY:
            v = bus.read(addr+1)
            return f"${v:02X},Y"
        if mode_fn == cpu.IZX:
            v = bus.read(addr+1)
            return f"(${v:02X},X)"
        if mode_fn == cpu.IZY:
            v = bus.read(addr+1)
            return f"(${v:02X}),Y"
        if mode_fn == cpu.REL:
            off = bus.read(addr+1)
            if off & 0x80:
                off -= 0x100
            tgt = (addr + 2 + off) & 0xFFFF
            return f"${tgt:04X}"
        if mode_fn == cpu.ABS:
            lo = bus.read(addr+1)
            hi = bus.read(addr+2)
            return f"${(hi << 8 | lo):04X}"
        if mode_fn == cpu.ABX:
            lo = bus.read(addr+1)
            hi = bus.read(addr+2)
            return f"${(hi << 8 | lo):04X},X"
        if mode_fn == cpu.ABY:
            lo = bus.read(addr+1)
            hi = bus.read(addr+2)
            return f"${(hi << 8 | lo):04X},Y"
        if mode_fn == cpu.IND:
            lo = bus.read(addr+1)
            hi = bus.read(addr+2)
            return f"(${(hi << 8 | lo):04X})"
    except Exception:
        pass
    return ''


def dump(rom, addrs):
    data = open(rom, 'rb').read()
    prg_units = data[4]
    trainer = (data[6] & 4) != 0
    prg_start = 16 + (512 if trainer else 0)
    prg_size = prg_units * 16384
    prg = data[prg_start:prg_start+prg_size]

    bus = Bus()
    cpu = CPU(bus)
    mapper = NROMMapper(prg)
    mapper.map(bus)
    load_addr = 0x8000
    for i, b in enumerate(prg):
        bus.write(load_addr+i, b)
    cpu.reset()

    for a in addrs:
        opcode = bus.read(a)
        instr_func, mode, cycles = cpu.lookup[opcode]
        mnemonic = instr_func.__name__.upper()
        op_text = format_operand(bus, cpu, a, mode)
        print(f'${a:04X}: {opcode:02X}  {mnemonic} {op_text}  (cycles base={cycles})')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: dump_instrs.py rom.nes addr1 [addr2 addr3 ...]')
        sys.exit(1)
    rom = sys.argv[1]
    addrs = [int(x, 0) for x in sys.argv[2:]]
    dump(rom, addrs)
