import os, sys
repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo not in sys.path:
    sys.path.insert(0, repo)
from src.Bus import Bus
from src.mappers import NROMMapper
from src.Cpu import CPU

rom_name = 'Super Mario Bros. (Europe) (Rev A).nes'
path = os.path.join(repo, rom_name)
if not os.path.exists(path):
    print('ROM not found:', path)
    sys.exit(1)

with open(path, 'rb') as f:
    data = f.read()

prg_units = data[4]
trainer = (data[6] & 0x04) != 0
prg_start = 16 + (512 if trainer else 0)
prg_size = prg_units * 16384
prg = data[prg_start:prg_start+prg_size]

print('PRG len', len(prg))

bus = Bus()
mapper = NROMMapper(prg)
mapper.map(bus)

# Read reset vector via bus
lo = bus.read(0xFFFC)
hi = bus.read(0xFFFD)
reset = (hi<<8)|lo
print('Reset vector via bus: {:04X}'.format(reset))

cpu = CPU(bus)
# set PC to reset
cpu.regs.pc = reset
print('CPU PC set to {:04X}'.format(cpu.regs.pc))

# Dump first 32 bytes at PC
bytes_at_pc = [bus.read((cpu.regs.pc + i) & 0xFFFF) for i in range(32)]
print('Bytes at PC:', ' '.join(f"{b:02X}" for b in bytes_at_pc))

# For each byte, show if CPU has an implementation (not XXX)
for i, b in enumerate(bytes_at_pc[:16]):
    entry = cpu.lookup[b]
    opname = entry[0].__name__ if hasattr(entry[0], '__name__') else str(entry[0])
    mode = entry[1].__name__ if hasattr(entry[1], '__name__') else str(entry[1])
    cycles = entry[2]
    print(f"{i:02}: {b:02X} -> {opname} mode={mode} cycles={cycles}")

print('Done')
