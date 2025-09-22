import os
import sys
from src.emulador_gui import EmuladorGUI
import tkinter as tk

rom_path = sys.argv[1] if len(sys.argv) > 1 else None
if not rom_path:
    print('Uso: python tools/headless_load_and_dump.py <rom.nes>')
    sys.exit(1)

root = tk.Tk()
root.withdraw()
app = EmuladorGUI(root)
# Carregar ROM sem filedialog: replicar lógica de load_rom usando caminho fornecido
with open(rom_path, 'rb') as f:
    data = f.read()

# copiar lógica simplificada de load_rom
prg = b''
if len(data) >= 16 and data[0:4] == b'NES\x1A':
    prg_size_units = data[4]
    prg_size = prg_size_units * 16384
    trainer_present = (data[6] & 0x04) != 0
    prg_start = 16 + (512 if trainer_present else 0)
    prg_size_limited = min(prg_size, 32768)
    prg = data[prg_start:prg_start + prg_size_limited]
else:
    prg = data

# instalar mapper
from src.mappers import NROMMapper
app.reset_cpu()
mapper = NROMMapper(prg)
app.bus.install_mapper(mapper)
app.binary_data = bytearray(prg)

# Forçar update_memory_view e pegar o conteúdo do widget
app.update_memory_view()
content = app.memory_view.get('1.0', 'end-1c')
print(content)

root.destroy()
