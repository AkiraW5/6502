from src.ppu import FullPPU
from PIL import Image
import sys
sys.path.insert(0, r'c:\dev\6502')

ppu = FullPPU(verbose=True)
ppu.set_chr(bytes([0xFF] * 8192))

chosen = [0, 52, 34, 24, 16, 8, 4, 2, 48, 36, 20, 12, 30, 14, 6, 10,
          1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31]
for i in range(0x20):
    ppu.palette[i] = chosen[i] % len(ppu.NES_PALETTE)

base = 0x400
for ty in range(30):
    for tx in range(32):
        ppu.vram[base + ty*32 + tx] = (ty*32 + tx) % 256
attr_base = base + 0x3C0
for ay in range(8):
    for ax in range(8):
        b = ((ax + ay) & 0x3) | (((ax + ay + 1) & 0x3) <<
                                 2) | (((ax + ay + 2) & 0x3) << 4) | (((ax + ay + 3) & 0x3) << 6)
        ppu.vram[attr_base + ay*8 + ax] = b

grid = ppu.get_name_table_color_grid(0)
height = len(grid)
width = len(grid[0])
img = Image.new('RGB', (width, height))
for y in range(height):
    for x in range(width):
        hexc = grid[y][x].lstrip('#')
        r = int(hexc[0:2], 16)
        g = int(hexc[2:4], 16)
        b = int(hexc[4:6], 16)
        img.putpixel((x, y), (r, g, b))
img.save(r'c:\dev\6502\ppu_palette_test.png')
print('Saved image to c:\dev\6502\ppu_palette_test.png')
