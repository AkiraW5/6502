# Simple runner to test FullPPU.oam_dma debug outputs
import os
from src.ppu import FullPPU

class BusStub:
    def __init__(self):
        # make 64KB of zeros
        self.mem = [0]*0x10000
        # Put some test pattern in page 0x02 (addresses 0x0200..0x02FF)
        for i in range(256):
            self.mem[0x0200 + i] = (i % 256)
    def read(self, addr):
        return self.mem[addr & 0xFFFF]

if __name__ == '__main__':
    print('Runner: creating FullPPU')
    ppu = FullPPU()
    # set some CHR data to emulate loaded CHR (values must be 0..255)
    ppu.set_chr(bytes([i % 256 for i in range(512)]))
    bus = BusStub()
    print('Runner: calling oam_dma(page=2)')
    ppu.oam_dma(bus, 2)
    # check files
    for fname in ('ram_dma_page_02.json','oam_dump_dma.json','ppu_chr_debug.json'):
        path = os.path.join(os.getcwd(), fname)
        print('Exists', fname, os.path.exists(path))
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
                print('---', fname, 'preview ---')
                print(data[:1000])
                print('--- end preview ---')
            except Exception as e:
                print('Failed reading', fname, e)
