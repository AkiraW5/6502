import os, sys
repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo not in sys.path:
    sys.path.insert(0, repo)
from src.Bus import Bus
from src.mappers import UNROMMapper

path = os.path.join(repo, 'Castlevania (E).nes')
with open(path, 'rb') as f:
    data = f.read()

prg_units = data[4]
trainer = (data[6] & 0x04) != 0
prg_start = 16 + (512 if trainer else 0)
prg_size = prg_units * 16384
prg = data[prg_start:prg_start+prg_size]

print('PRG len', len(prg))
bus = Bus()
mapper = UNROMMapper(prg)
mapper.map(bus)

print('Mapper:', mapper)
bus.write(0x8000, 3)
print('After bank select 3: read $8000 =', hex(bus.read(0x8000)))
print('Read $C000 =', hex(bus.read(0xC000)))

print('Done')
