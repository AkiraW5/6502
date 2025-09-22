"""Visualizador mínimo de pattern-table do PPU usado pela interface gráfica do emulador.

Este é um helper leve que sabe como pegar dados CHR (pattern table)
de um arquivo .nes e desenhar os tiles 8x8 em um Canvas do tkinter. Não é uma
implementação completa do PPU — apenas o suficiente para visualizar pattern tables para depuração
e visualização.

API:
    SimplePPU(chr_bytes=None)
        - chr_bytes: objeto bytes contendo CHR-ROM (múltiplo de 8192 bytes)
    set_chr(chr_bytes)
    render_pattern_table(canvas, table_index=0, scale=2)

"""
# TODO: Adicionar suporte a mirroring de name table e atributos
from typing import Optional, Callable, Any
import logging
import os, sys, time

# Module-load diagnostic: helps confirm which file/version is imported at runtime
try:
    print(f"[MODULE LOAD] src.ppu __file__={__file__} cwd={os.getcwd()} pid={os.getpid()} ts={time.time()}")
except Exception:
    print("[MODULE LOAD] src.ppu loaded (path unknown)")
try:
    from typing import Protocol  # type: ignore
    PPUProtocol = Protocol  # type: ignore
except Exception:
    PPUProtocol = Any


class SimplePPU:
    def __init__(self, chr_bytes: Optional[bytes] = None):
        self.chr = chr_bytes or b''
    def set_chr(self, chr_bytes: bytes):
        self.chr = chr_bytes or b''
    def set_chr(self, chr_bytes: bytes):
        self.chr = chr_bytes or b''

    def get_tile_map(self, table_index: int = 0):
        tiles_per_row = 32
        rows = 30
        tile_map = [[0] * tiles_per_row for _ in range(rows)]
        pattern_base = (table_index & 1) * 256
        for ty in range(rows):
            for tx in range(tiles_per_row):
                tindex = (ty * tiles_per_row + tx) % 256
                pixels = self._get_tile_pixels(pattern_base + tindex)
                try:
                    total = 0
                    for r in pixels:
                        for v in r:
                            total += (v & 0x3)
                    rep = (total // 64) & 0x3
                except Exception:
                    rep = pixels[0][0] & 0x3
                tile_map[ty][tx] = rep
        return tile_map

    def get_name_table_color_grid(self, table_index: int = 0):
        width = 32 * 8
        height = 30 * 8
        palette = ['#000000', '#555555', '#AAAAAA', '#FFFFFF']
        grid = [[palette[0] for _ in range(width)] for _ in range(height)]
        pattern_base = (table_index & 1) * 256
        for ty in range(30):
            for tx in range(32):
                tindex = (ty * 32 + tx) % 256
                pixels = self._get_tile_pixels(pattern_base + tindex)
                px0 = tx * 8
                py0 = ty * 8
                for ry in range(8):
                    for rx in range(8):
                        pv = pixels[ry][rx] & 0x3
                        gx = px0 + rx
                        gy = py0 + ry
                        if 0 <= gx < width and 0 <= gy < height:
                            grid[gy][gx] = palette[pv]
        return grid

    def _get_tile_pixels(self, tile_index: int):
        base = tile_index * 16
        if base + 15 >= len(self.chr):
            return [[0]*8 for _ in range(8)]
        plane0 = self.chr[base:base+8]
        plane1 = self.chr[base+8:base+16]
        pixels = [[0]*8 for _ in range(8)]
        for y in range(8):
            b0 = plane0[y]
            b1 = plane1[y]
            for x in range(8):
                bit = 7 - x
                lo = (b0 >> bit) & 1
                hi = (b1 >> bit) & 1
                pixels[y][x] = (hi << 1) | lo
        return pixels

    def render_pattern_table(self, canvas, table_index: int = 0, scale: int = 2):
        if not canvas:
            return
        canvas.delete('all')
        table_size = 4096
        start = table_index * table_size
        end = start + table_size
        chunk = self.chr[start:end]
        if not chunk:
            return
        tiles_per_row = 16
        tile_w = 8
        tile_h = 8
        palette = ['#000000', '#555555', '#AAAAAA', '#FFFFFF']
        width = tiles_per_row * tile_w * scale
        rows = (len(chunk) // 16) // tiles_per_row
        height = rows * tile_h * scale
        try:
            canvas.config(width=width, height=height)
        except Exception:
            pass
        num_tiles = len(chunk) // 16
        for t in range(num_tiles):
            tile_x = (t % tiles_per_row) * tile_w * scale
            tile_y = (t // tiles_per_row) * tile_h * scale
            pixels = self._get_tile_pixels(t + table_index * 256)
            for y in range(8):
                for x in range(8):
                    color = palette[pixels[y][x] & 0x3]
                    x0 = tile_x + x * scale
                    y0 = tile_y + y * scale
                    x1 = x0 + scale
                    y1 = y0 + scale
                    canvas.create_rectangle(x0, y0, x1, y1, outline=color, fill=color)


class FullPPU:
    """PPU simplificado, com precisão razoável de ciclos, usado para sincronização CPU<->PPU.

    Não é uma implementação totalmente fiel do PPU, mas fornece:
      - VRAM (2KB) para armazenamento das name tables
      - OAM (256 bytes) e suporte a OAM DMA
      - Registradores do PPU (2000-2007) com comportamento mínimo
      - step(ppu_cycles) para avançar ciclos/scanlines/frames
      - Sinalização do VBlank e callback opcional de NMI quando o VBlank inicia

    Modelo de tempo (simplificado): 341 clocks PPU por scanline, 262 scanlines por quadro
    O VBlank começa na scanline 241 e termina na pré-renderização (261).
    """

    def __init__(self, chr_bytes: Optional[bytes] = None, verbose: bool = False):
        self.chr = chr_bytes or b''
        self.regs = {0x2000: 0, 0x2001: 0, 0x2002: 0, 0x2003: 0,
                     0x2004: 0, 0x2005: 0, 0x2006: 0, 0x2007: 0}
        self.vram = bytearray(0x800)
        self.oam = bytearray(256)
        self.ppu_cycle = 0  # 0..340
        self.scanline = 0    # 0..261 (261 = pre-render)
        self.frame = 0
        self.in_vblank = False
        self.nmi_callback: Optional[Callable[[], None]] = None
        self._nmi_fired = False
        self._addr_latch = 0
        self._read_buffer = 0
        self._temp_addr = 0
        self.palette = bytearray(0x20)
        self._vram_write_count = 0
        self._vram_write_log = []
        self._ppustatus_read_count = 0
        self.verbose = bool(verbose)
        self.log_oam = False
        self._oam_log_count = 0
        self._logger = logging.getLogger(__name__)

    def set_chr(self, chr_bytes: bytes):
        try:
            self.chr = chr_bytes or b''
        except Exception:
            self.chr = b''

    def ppu_read_register(self, addr: int) -> int:
        addr = 0x2000 | (addr & 0x7)
        if addr == 0x2002:
            val = self.regs.get(0x2002, 0) & 0xFF
            self.regs[0x2002] = val & (~0x80)
            self._addr_latch = 0
            self._nmi_fired = False
            try:
                self._ppustatus_read_count += 1
                if self._ppustatus_read_count <= 20:
                    if self.verbose:
                        self._logger.debug(f"FullPPU: PPUSTATUS read #{self._ppustatus_read_count} -> ${val:02X}")
                elif self._ppustatus_read_count == 21:
                    if self.verbose:
                        self._logger.debug("FullPPU: further PPUSTATUS reads will be suppressed")
            except Exception:
                pass
            return val
        if addr == 0x2007:
            addr_v = self.regs.get(0x2006, 0)
            if 0x3F00 <= (addr_v & 0xFFFF) <= 0x3FFF:
                val = self._read_palette(addr_v & 0xFF)
            else:
                val = self._read_buffer & 0xFF
                inc = 32 if (self.regs.get(0x2000, 0) & 0x04) else 1
                next_addr = (addr_v + inc) & 0x7FF
                self._read_buffer = self.vram[self._vram_index(next_addr & 0x7FF)] if len(self.vram) else 0
            self.regs[0x2006] = (self.regs.get(0x2006, 0) + (32 if (self.regs.get(0x2000, 0) & 0x04) else 1)) & 0xFFFF
            return val
        return self.regs.get(addr, 0) & 0xFF

    def ppu_write_register(self, addr: int, val: int):
        addr = 0x2000 | (addr & 0x7)
        val &= 0xFF
        if addr == 0x2000:
            self.regs[0x2000] = val
            return
        if addr == 0x2001:
            self.regs[0x2001] = val
            return
        if addr == 0x2002:
            return
        if addr == 0x2003:
            self.regs[0x2003] = val
            return
        if addr == 0x2004:
            oamaddr = self.regs.get(0x2003, 0) & 0xFF
            self.oam[oamaddr] = val
            self.regs[0x2003] = (oamaddr + 1) & 0xFF
            try:
                if getattr(self, 'log_oam', False):
                    self._oam_log_count = getattr(self, '_oam_log_count', 0) + 1
                    if self._oam_log_count <= 200:
                        neigh = []
                        for k in range(max(0, oamaddr-4), min(256, oamaddr+4)):
                            neigh.append(int(self.oam[k]))
                        self._logger.debug(f"FullPPU: OAM write idx={oamaddr} val=${val:02X} neigh={neigh}")
                    elif self._oam_log_count == 201:
                        self._logger.debug("FullPPU: further OAM write logs suppressed")
            except Exception:
                pass
            return
        if addr == 0x2005:
            self.regs[0x2005] = val
            return
        if addr == 0x2006:
            if self._addr_latch == 0:
                self._addr_latch = 1
                self._temp_addr = (val & 0xFF) << 8
            else:
                self._addr_latch = 0
                self._temp_addr = (self._temp_addr & 0xFF00) | (val & 0xFF)
                self.regs[0x2006] = self._temp_addr & 0xFFFF
                a = self.regs.get(0x2006, 0)
                try:
                    self._read_buffer = self.vram[self._vram_index(a & 0x7FF)]
                except Exception:
                    self._read_buffer = 0
            return
        if addr == 0x2007:
            addr_v = self.regs.get(0x2006, 0) & 0xFFFF
            if 0x3F00 <= (addr_v & 0xFFFF) <= 0x3FFF:
                try:
                    pal_index = (addr_v - 0x3F00) & 0x1F
                    if (pal_index & 0x03) == 0:
                        self.palette[0] = val & 0xFF
                    else:
                        self.palette[pal_index] = val & 0xFF
                except Exception:
                    pass
            else:
                idx = self._vram_index(addr_v & 0x7FF)
                self.vram[idx] = val
                try:
                    self._vram_write_count += 1
                    if len(self._vram_write_log) < 20:
                        self._vram_write_log.append((addr_v & 0xFFFF, val))
                    if self._vram_write_count <= 20:
                        if self.verbose:
                            self._logger.debug(f"FullPPU: PPUDATA write #{self._vram_write_count} addr=${addr_v:04X} -> ${val:02X}")
                    elif self._vram_write_count == 21:
                        if self.verbose:
                            self._logger.debug("FullPPU: further PPUDATA writes will be suppressed in logs")
                except Exception:
                    pass
            inc = 32 if (self.regs.get(0x2000, 0) & 0x04) else 1
            self.regs[0x2006] = (self.regs.get(0x2006, 0) + inc) & 0xFFFF
            return

    def _vram_index(self, index: int) -> int:
        return index & 0x7FF

    def _read_palette(self, addr_byte: int) -> int:
        idx = addr_byte & 0x1F
        try:
            if (idx & 0x03) == 0:
                return self.palette[0] & 0xFF
            return self.palette[idx] & 0xFF
        except Exception:
            return 0

    def oam_dma(self, bus, page: int):
        import json, os, traceback
        base = (page & 0xFF) << 8

        # 1) Ler 256 bytes da RAM (fonte DMA)
        ram_bloco = []
        try:
            ram_bloco = [bus.read((base + i) & 0xFFFF) for i in range(256)]
        except Exception:
            # fallback: preencher zeros caso a leitura falhe
            ram_bloco = [0] * 256

        # 2) Salvar dump da RAM (CWD e ABS)
        try:
            out_cwd = os.path.join(os.getcwd(), f'ram_dma_page_{page:02X}.json')
            print(f"[FullPPU.oam_dma] Tentando dump da RAM em: {out_cwd}", flush=True)
            with open(out_cwd, 'w', encoding='utf-8') as jf:
                json.dump(ram_bloco, jf, indent=2)
            print(f"[FullPPU.oam_dma] Dump da RAM salvo com sucesso: {out_cwd}", flush=True)
        except Exception as e:
            print(f"[FullPPU.oam_dma] Falha ao salvar dump da RAM (CWD): {e}", flush=True)
            traceback.print_exc()
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            out_abs = os.path.join(repo_root, f'ram_dma_page_{page:02X}.json')
            with open(out_abs, 'w', encoding='utf-8') as jf2:
                json.dump(ram_bloco, jf2, indent=2)
            print(f"[FullPPU.oam_dma] Dump da RAM salvo (ABS): {out_abs}", flush=True)
        except Exception as e:
            print(f"[FullPPU.oam_dma] Falha ao salvar dump da RAM (ABS): {e}", flush=True)
            traceback.print_exc()

        # 3) Preencher OAM com os bytes lidos
        for i in range(256):
            try:
                self.oam[i] = int(ram_bloco[i]) & 0xFF
            except Exception:
                self.oam[i] = 0

        # 4) Salvar OAM dump (CWD e ABS)
        try:
            out_oam_cwd = os.path.join(os.getcwd(), 'oam_dump_dma.json')
            print(f"[FullPPU.oam_dma] Writing OAM dump to: {out_oam_cwd}", flush=True)
            with open(out_oam_cwd, 'w', encoding='utf-8') as jf:
                json.dump({'page': page, 'base': base, 'oam': list(self.oam)}, jf, indent=2)
            print(f"[FullPPU.oam_dma] OAM dump salvo (CWD): {out_oam_cwd}", flush=True)
        except Exception as e:
            print(f"[FullPPU.oam_dma] Failed to save OAM dump (CWD): {e}", flush=True)
            traceback.print_exc()
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            out_oam_abs = os.path.join(repo_root, 'oam_dump_dma.json')
            with open(out_oam_abs, 'w', encoding='utf-8') as jf2:
                json.dump({'page': page, 'base': base, 'oam': list(self.oam)}, jf2, indent=2)
            print(f"[FullPPU.oam_dma] OAM dump salvo (ABS): {out_oam_abs}", flush=True)
        except Exception as e:
            print(f"[FullPPU.oam_dma] Failed to save OAM dump (ABS): {e}", flush=True)
            traceback.print_exc()

        # 5) Salvar debug do CHR (CWD e ABS)
        try:
            chr_info = {
                'chr_len': len(getattr(self, 'chr', b'')),
                'chr_head': list(getattr(self, 'chr', b'')[:64])
            }
            out_chr_cwd = os.path.join(os.getcwd(), 'ppu_chr_debug.json')
            print(f"[FullPPU.oam_dma] Writing CHR debug to: {out_chr_cwd} (len={chr_info['chr_len']})", flush=True)
            with open(out_chr_cwd, 'w', encoding='utf-8') as jf:
                json.dump(chr_info, jf, indent=2)
            print(f"[FullPPU.oam_dma] CHR debug salvo (CWD): {out_chr_cwd}", flush=True)
        except Exception as e:
            print(f"[FullPPU.oam_dma] Failed to save CHR debug (CWD): {e}", flush=True)
            traceback.print_exc()
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            out_chr_abs = os.path.join(repo_root, 'ppu_chr_debug.json')
            with open(out_chr_abs, 'w', encoding='utf-8') as jf2:
                json.dump(chr_info, jf2, indent=2)
            print(f"[FullPPU.oam_dma] CHR debug salvo (ABS): {out_chr_abs}", flush=True)
        except Exception as e:
            print(f"[FullPPU.oam_dma] Failed to save CHR debug (ABS): {e}", flush=True)
            traceback.print_exc()

        # 6) Marcar DMA ativo (emulação de timing)
        self._oam_dma_cycles = 514
        self._oam_dma_active = True
        try:
            if getattr(self, 'log_oam', False):
                pc_info = None
                try:
                    pc_info = getattr(bus, 'last_write_pc', None)
                except Exception:
                    pc_info = None
                try:
                    sample = [int(b) for b in self.oam[:16]]
                except Exception:
                    sample = []
                if pc_info is not None:
                    self._logger.debug(f"FullPPU: OAM DMA page=${page:02X} triggered (bus last_write_pc={pc_info}) sample={sample}")
                else:
                    self._logger.debug(f"FullPPU: OAM DMA page=${page:02X} triggered sample={sample}")
        except Exception:
            pass

    def _chr_get_tile_pixels(self, tile_index: int):
        base = tile_index * 16
        if base + 15 >= len(self.chr):
            return [[0]*8 for _ in range(8)]
        plane0 = self.chr[base:base+8]
        plane1 = self.chr[base+8:base+16]
        pixels = [[0]*8 for _ in range(8)]
        for y in range(8):
            b0 = plane0[y]
            b1 = plane1[y]
            for x in range(8):
                bit = 7 - x
                lo = (b0 >> bit) & 1
                hi = (b1 >> bit) & 1
                pixels[y][x] = (hi << 1) | lo
        return pixels

    def render_pattern_table(self, canvas, table_index: int = 0, scale: int = 2):
        if not canvas:
            return
        try:
            canvas.delete('all')
        except Exception:
            pass
        table_size = 4096
        start = table_index * table_size
        chunk = self.chr[start:start + table_size]
        if not chunk:
            return
        tiles_per_row = 16
        tile_w = 8
        tile_h = 8
        palette = ['#000000', '#555555', '#AAAAAA', '#FFFFFF']
        num_tiles = len(chunk) // 16
        for t in range(num_tiles):
            tile_x = (t % tiles_per_row) * tile_w * scale
            tile_y = (t // tiles_per_row) * tile_h * scale
            pixels = self._chr_get_tile_pixels(t + table_index * 256)
            for y in range(8):
                for x in range(8):
                    color = palette[pixels[y][x] & 0x3]
                    x0 = tile_x + x * scale
                    y0 = tile_y + y * scale
                    x1 = x0 + scale
                    y1 = y0 + scale
                    try:
                        canvas.create_rectangle(x0, y0, x1, y1, outline=color, fill=color)
                    except Exception:
                        pass

    def get_tile_map(self, table_index: int = 0):
        base = (table_index & 1) * 0x400
        tile_map = [[0]*32 for _ in range(30)]
        pattern_table_select = (self.regs.get(0x2000, 0) >> 4) & 0x1
        pattern_base = pattern_table_select * 256
        if not hasattr(self, '_one_shot_detailed_diag'):
            try:
                found = False
                for ty_d in range(30):
                    for tx_d in range(32):
                        idxd = base + ty_d*32 + tx_d
                        if idxd < len(self.vram) and self.vram[idxd] != 0:
                            tix = self.vram[idxd]
                            found = True
                            break
                    if found:
                        break
                if found:
                    self._one_shot_detailed_diag = True
                    try:
                        if self.verbose:
                            self._logger.debug(f"FullPPU: DETAILED DIAG at tile (tx={tx_d},ty={ty_d}) idx=${idxd:04X} tile_index={tix} pattern_base={pattern_base}")
                            pixels = self._chr_get_tile_pixels(tix + pattern_base)
                            pix_lines = [''.join(str((v & 0x3)) for v in r) for r in pixels]
                            for ln in pix_lines:
                                self._logger.debug(f"FullPPU: DETAILED pixels: {ln}")
                            attr_base = base + 0x3C0
                            attr_x = tx_d // 4
                            attr_y = ty_d // 4
                            attr_idx = attr_base + attr_y * 8 + attr_x
                            attr = self.vram[self._vram_index(attr_idx & 0x7FF)] if len(self.vram) else 0
                            local_tx = tx_d % 4
                            local_ty = ty_d % 4
                            if local_tx < 2 and local_ty < 2:
                                shift = 0
                            elif local_tx >= 2 and local_ty < 2:
                                shift = 2
                            elif local_tx < 2 and local_ty >= 2:
                                shift = 4
                            else:
                                shift = 6
                            palette_select = (attr >> shift) & 0x3
                            pal_base = palette_select * 4
                            self._logger.debug(f"FullPPU: DETAILED attr_idx=${attr_idx:04X} attr_byte=${attr:02X} shift={shift} palette_select={palette_select} pal_base={pal_base}")
                            for pv in range(4):
                                try:
                                    pal_byte = self._palette_read(pal_base + pv)
                                except Exception:
                                    pal_byte = 0
                                color_idx = pal_byte & 0x3F
                                color = self.NES_PALETTE[color_idx] if color_idx < len(self.NES_PALETTE) else self.NES_PALETTE[0]
                                self._logger.debug(f"FullPPU: DETAILED pv={pv} pal_byte=${pal_byte:02X} color_idx={color_idx} color={color}")
                    except Exception:
                        pass
            except Exception:
                pass
            # Gravando dumps de debug (OAM e CHR) para diagnóstico
            try:
                import json, os
                out_oam = os.path.join(os.getcwd(), 'oam_dump_dma.json')
                try:
                    with open(out_oam, 'w', encoding='utf-8') as jf:
                        json.dump({'page': base, 'oam': list(self.oam)}, jf, indent=2)
                except Exception:
                    pass
                chr_info = {
                    'chr_len': len(getattr(self, 'chr', b'')),
                    'chr_head': list((getattr(self, 'chr', b'')[:64]))
                }
                out_chr = os.path.join(os.getcwd(), 'ppu_chr_debug.json')
                try:
                    with open(out_chr, 'w', encoding='utf-8') as jf:
                        json.dump(chr_info, jf, indent=2)
                except Exception:
                    pass
            except Exception:
                pass
            # Adicional: salvar dump de OAM e debug do CHR quando FullPPU é usado
            try:
                import json, os
                out_path2 = os.path.join(os.getcwd(), 'oam_dump_dma.json')
                try:
                    with open(out_path2, 'w', encoding='utf-8') as jf:
                        json.dump({'page': base, 'oam': list(self.oam)}, jf, indent=2)
                except Exception:
                    pass
                # salvar debug do CHR
                chr_info = {
                    'chr_len': len(getattr(self, 'chr', b'')),
                    'chr_head': list((getattr(self, 'chr', b'')[:64]))
                }
                out_chr = os.path.join(os.getcwd(), 'ppu_chr_debug.json')
                try:
                    with open(out_chr, 'w', encoding='utf-8') as jf:
                        json.dump(chr_info, jf, indent=2)
                except Exception:
                    pass
            except Exception:
                pass
        for ty in range(30):
            for tx in range(32):
                idx = base + ty*32 + tx
                if idx < len(self.vram):
                    tile_index = self.vram[idx]
                else:
                    tile_index = 0
                pixels = self._chr_get_tile_pixels(tile_index + pattern_base)
                try:
                    total = 0
                    for row in pixels:
                        for v in row:
                            total += (v & 0x3)
                    rep = (total // 64) & 0x3
                except Exception:
                    rep = pixels[0][0] & 0x3
                tile_map[ty][tx] = rep
        return tile_map

    NES_PALETTE = [
        '#7C7C7C', '#0000FC', '#0000BC', '#4428BC', '#940084', '#A80020', '#A81000', '#5C2C00',
        '#104000', '#000000', '#064214', '#000000', '#000000', '#000000', '#000000', '#000000',
        '#BCBCBC', '#0074FF', '#0054FF', '#6858FF', '#D800CC', '#E40058', '#F05820', '#BC7C00',
        '#007800', '#006800', '#005800', '#004058', '#000000', '#000000', '#000000', '#000000',
        '#FFFFFF', '#3CB8FF', '#5CB8FF', '#A8B8FF', '#F8B8FF', '#FFC8B8', '#FFD8A8', '#FFECB0',
        '#B8F8B8', '#B8F8D8', '#B8F8F8', '#B8E8F8', '#000000', '#000000', '#000000', '#000000',
        '#FFFCFC', '#A4E4FC', '#C8D8FF', '#E8D8FF', '#FCE4FC', '#FFF0E0', '#FFF8D8', '#FFF8C8',
        '#D8F8D8', '#D8F8E8', '#D8F8F8', '#D8EEF8', '#000000', '#000000', '#000000', '#000000'
    ]

    def _palette_read(self, index: int) -> int:
        idx = index & 0x1F
        try:
            if (idx & 0x03) == 0:
                return self.palette[0] & 0xFF
            return self.palette[idx] & 0xFF
        except Exception:
            return 0

    def get_name_table_color_grid(self, table_index: int = 0):
        if not hasattr(self, '_one_shot_chr_diag'):
            self._one_shot_chr_diag = True
            try:
                if self.verbose:
                    self._logger.debug(f"FullPPU: CHR len={len(self.chr)} bytes")
                    sample = bytes(self.chr[:32]) if len(self.chr) >= 32 else bytes(self.chr)
                    self._logger.debug(f"FullPPU: CHR[0..31]={sample.hex()}")
            except Exception:
                pass
        width = 32 * 8
        height = 30 * 8
        grid = [[self.NES_PALETTE[0] for _ in range(width)] for _ in range(height)]
        base0 = 0x000
        base1 = 0x400
        if not hasattr(self, '_one_shot_table_diag'):
            self._one_shot_table_diag = True
            try:
                idx0 = [self.vram[base0 + i] for i in range(8)]
                idx1 = [self.vram[base1 + i] for i in range(8)]
                if self.verbose:
                    self._logger.debug(f"FullPPU: DIAG name-table0 indices={idx0}")
                    self._logger.debug(f"FullPPU: DIAG name-table1 indices={idx1}")
            except Exception:
                pass
        if sum(self.vram[base0:base0+32]) > sum(self.vram[base1:base1+32]):
            base = base0
            if not hasattr(self, '_test_fill_done'):
                self._test_fill_done = True
                try:
                    if self.verbose:
                        self._logger.debug(f"FullPPU: TESTE - preenchendo name-table em base={base} (VRAM[{base}:{base+32}])")
                    for ty in range(30):
                        for tx in range(32):
                            self.vram[base + ty*32 + tx] = ((ty*32 + tx) % 240) + 1
                    if self.verbose:
                        self._logger.debug("FullPPU: TESTE - name-table preenchida com valores de 1 a 240 para validação de renderização.")
                        self._logger.debug(f"FullPPU: TESTE - primeiros índices da name-table: {list(self.vram[base:base+32])}")
                except Exception:
                    pass
        else:
            base = base1
            if not hasattr(self, '_test_fill_done'):
                self._test_fill_done = True
                try:
                    if self.verbose:
                        self._logger.debug(f"FullPPU: TESTE - preenchendo name-table em base={base} (VRAM[{base}:{base+32}])")
                    for ty in range(30):
                        for tx in range(32):
                            self.vram[base + ty*32 + tx] = ((ty*32 + tx) % 240) + 1
                    if self.verbose:
                        self._logger.debug("FullPPU: TESTE - name-table preenchida com valores de 1 a 240 para validação de renderização.")
                        self._logger.debug(f"FullPPU: TESTE - primeiros índices da name-table: {list(self.vram[base:base+32])}")
                except Exception:
                    pass
        attr_base = base + 0x3C0
        if not hasattr(self, '_one_shot_palette_fill'):
            self._one_shot_palette_fill = True
            try:
                for i in range(0x20):
                    self.palette[i] = i % len(self.NES_PALETTE)
                if self.verbose:
                    self._logger.debug("FullPPU: TESTE - palette RAM (self.palette) preenchida com valores de teste.")
            except Exception:
                pass
        if not hasattr(self, '_one_shot_palette_diag'):
            self._one_shot_palette_diag = True
            try:
                samples = [(0, 0), (0, 1), (1, 0), (1, 1)]
                for (ty_s, tx_s) in samples:
                    try:
                        attr_x = tx_s // 4
                        attr_y = ty_s // 4
                        attr_idx = attr_base + attr_y * 8 + attr_x
                        attr = self.vram[self._vram_index(attr_idx & 0x7FF)] if len(self.vram) else 0
                        local_tx = tx_s % 4
                        local_ty = ty_s % 4
                        if local_tx < 2 and local_ty < 2:
                            shift = 0
                        elif local_tx >= 2 and local_ty < 2:
                            shift = 2
                        elif local_tx < 2 and local_ty >= 2:
                            shift = 4
                        else:
                            shift = 6
                        palette_select = (attr >> shift) & 0x3
                        pal_base = palette_select * 4
                        for pv in range(4):
                            pal_byte = self._palette_read(pal_base + pv)
                            color_idx = pal_byte & 0x3F
                            color = self.NES_PALETTE[color_idx] if color_idx < len(self.NES_PALETTE) else self.NES_PALETTE[0]
                            msg = (
                                f"FullPPU: ONE_SHOT PALETTE DIAG tx={tx_s} ty={ty_s} "
                                f"attr_idx=0x{attr_idx:03X} attr=0x{attr:02X} shift={shift} "
                                f"palette_select={palette_select} pal_base={pal_base} pv={pv} "
                                f"pal_byte=0x{pal_byte:02X} color_idx={color_idx} color={color}"
                            )
                            try:
                                if self.verbose:
                                    self._logger.debug(msg)
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass
        if not hasattr(self, '_test_fill_done'):
            self._test_fill_done = True
            try:
                for ty in range(30):
                    for tx in range(32):
                        self.vram[base + ty*32 + tx] = ((ty*32 + tx) % 240) + 1
                if self.verbose:
                    self._logger.debug("FullPPU: TESTE - name-table preenchida com valores de 1 a 240 para validação de renderização.")
            except Exception:
                pass
        if not hasattr(self, '_one_shot_lines_diag'):
            self._one_shot_lines_diag = True
            try:
                for l in range(20, 30):
                    idxs = [self.vram[base + l*32 + i] for i in range(8)]
                    if self.verbose:
                        self._logger.debug(f"FullPPU: DIAG name-table line {l}: {idxs}")
            except Exception:
                pass
        pattern_table_select = (self.regs.get(0x2000, 0) >> 4) & 0x1
        pattern_base = pattern_table_select * 256
        if not hasattr(self, '_one_shot_name_table_diag'):
            try:
                self._one_shot_name_table_diag = True
                if self.verbose:
                    self._logger.debug(f"FullPPU: DIAG name_table render (table={table_index}) pattern_table_select={pattern_table_select} pattern_base={pattern_base}")
                    row_indices = []
                    for txd in range(8):
                        idxd = base + 0*32 + txd
                        row_indices.append(self.vram[idxd] if idxd < len(self.vram) else 0)
                    self._logger.debug(f"FullPPU: DIAG first_row_tile_indices={row_indices}")
                    try:
                        attr0 = self.vram[self._vram_index(attr_base & 0x7FF)] if len(self.vram) else 0
                    except Exception:
                        attr0 = 0
                    self._logger.debug(f"FullPPU: DIAG attr0_byte=${attr0:02X}")
                    t0 = row_indices[0] if row_indices else 0
                    pix0 = self._chr_get_tile_pixels(t0 + pattern_base)
                    pix_rows = [''.join(str(p) for p in r) for r in pix0[:2]]
                    self._logger.debug(f"FullPPU: DIAG tile0={t0} sample_rows={pix_rows}")
            except Exception:
                pass
        for ty in range(30):
            for tx in range(32):
                idx = base + ty*32 + tx
                if idx < len(self.vram):
                    tile_index = self.vram[idx]
                else:
                    tile_index = 0
                pixels = self._chr_get_tile_pixels(tile_index + pattern_base)
                attr_x = tx // 4
                attr_y = ty // 4
                attr_idx = attr_base + attr_y * 8 + attr_x
                attr = self.vram[self._vram_index(attr_idx & 0x7FF)] if len(self.vram) else 0
                local_tx = tx % 4
                local_ty = ty % 4
                if local_tx < 2 and local_ty < 2:
                    shift = 0
                elif local_tx >= 2 and local_ty < 2:
                    shift = 2
                elif local_tx < 2 and local_ty >= 2:
                    shift = 4
                else:
                    shift = 6
                palette_select = (attr >> shift) & 0x3
                pal_base = palette_select * 4
                px0 = tx * 8
                py0 = ty * 8
                for ry in range(8):
                    for rx in range(8):
                        pv = pixels[ry][rx] & 0x3
                        pal_byte = self._palette_read(pal_base + pv)
                        color_idx = pal_byte & 0x3F
                        color = self.NES_PALETTE[color_idx] if color_idx < len(self.NES_PALETTE) else self.NES_PALETTE[0]
                        gx = px0 + rx
                        gy = py0 + ry
                        if 0 <= gx < width and 0 <= gy < height:
                            grid[gy][gx] = color
        return grid

    def step(self, ppu_clocks: int):
        if ppu_clocks <= 0:
            return
        self.ppu_cycle += ppu_clocks
        while self.ppu_cycle >= 341:
            self.ppu_cycle -= 341
            self.scanline += 1
            if self.scanline == 241:
                self.in_vblank = True
                self.regs[0x2002] = self.regs.get(0x2002, 0) | 0x80
                if (self.regs.get(0x2000, 0) & 0x80) and self.nmi_callback and not self._nmi_fired:
                    try:
                        self.nmi_callback()
                        self._nmi_fired = True
                    except Exception:
                        pass
                try:
                    if not hasattr(self, '_vblank_log_count'):
                        self._vblank_log_count = 0
                    self._vblank_log_count += 1
                    if self._vblank_log_count <= 5:
                        if self.verbose:
                            self._logger.debug(f"FullPPU: VBlank start (scanline=241) frame={self.frame} (log #{self._vblank_log_count})")
                            try:
                                vram_sample = bytes(self.vram[:16])
                                chr_sample = bytes(self.chr[:32])
                                ctrl = self.regs.get(0x2000, 0)
                                mask = self.regs.get(0x2001, 0)
                                self._logger.debug(f"FullPPU: DIAG VRAM[0..15]={vram_sample.hex()} CHR[0..31]={chr_sample[:16].hex()}... regs:CTRL=${ctrl:02X} MASK=${mask:02X}")
                            except Exception:
                                pass
                    elif self._vblank_log_count == 6:
                        if self.verbose:
                            self._logger.debug("FullPPU: further VBlank logs suppressed")
                except Exception:
                    pass
            if getattr(self, '_oam_dma_active', False):
                cpu_cycles = ppu_clocks // 3
                self._oam_dma_cycles = max(0, getattr(self, '_oam_dma_cycles', 0) - cpu_cycles)
                if self._oam_dma_cycles == 0:
                    self._oam_dma_active = False
            if self.scanline > 260:
                self.scanline = 0
                self.frame += 1
                self.in_vblank = False
                self.regs[0x2002] = self.regs.get(0x2002, 0) & (~0x80)
                self._nmi_fired = False
                try:
                    if not hasattr(self, '_frame_log_count'):
                        self._frame_log_count = 0
                    self._frame_log_count += 1
                    if self._frame_log_count <= 5:
                        if self.verbose:
                            self._logger.debug(f"FullPPU: frame end -> new frame={self.frame} (log #{self._frame_log_count})")
                    elif self._frame_log_count == 6:
                        if self.verbose:
                            self._logger.debug("FullPPU: further frame logs suppressed")
                except Exception:
                    pass
