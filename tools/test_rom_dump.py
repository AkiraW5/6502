import sys
import os


def dump_nes(rom_path):
    with open(rom_path, 'rb') as f:
        data = f.read()
    print(f"Arquivo: {os.path.basename(rom_path)} tamanho={len(data)} bytes")
    if len(data) < 16 or data[:4] != b'NES\x1A':
        print("Nao é iNES (cabecalho NES\\x1A ausente ou arquivo muito pequeno).")
        print("Primeiros 32 bytes:", [hex(b) for b in data[:32]])
        return
    prg_units = data[4]
    chr_units = data[5]
    flags6 = data[6]
    flags7 = data[7]
    trainer = bool(flags6 & 0x04)
    mapper = ((flags7 & 0xF0) | (flags6 >> 4)) & 0xFF
    prg_size = prg_units * 16384
    chr_size = chr_units * 8192
    prg_start = 16 + (512 if trainer else 0)
    prg_end = prg_start + prg_size
    print(f"PRG units: {prg_units} -> {prg_size} bytes")
    print(f"CHR units: {chr_units} -> {chr_size} bytes")
    print(f"Trainer presente: {trainer}")
    print(f"Mapper: {mapper}")
    print(f"PRG start offset: {prg_start} PRG end offset: {prg_end}")
    if prg_start < len(data):
        print("PRG primeiros 32 bytes:", [hex(b) for b in data[prg_start:prg_start+32]])
    else:
        print("PRG start beyond file length")
    if prg_end <= len(data):
        print("PRG ultimos 32 bytes:", [hex(b) for b in data[max(prg_start, prg_end-32):prg_end]])
    else:
        print("PRG end beyond file length; file too small for header-declared PRG size")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python tools/test_rom_dump.py <rom.nes>")
        sys.exit(1)
    dump_nes(sys.argv[1])
