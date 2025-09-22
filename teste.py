import sys

def dump_rom_info(rom_path):
    with open(rom_path, 'rb') as f:
        data = f.read()
    print(f"Tamanho total: {len(data)} bytes")
    print(f"Primeiros 16 bytes do arquivo (cabeçalho iNES): {[hex(b) for b in data[:16]]}")
    if data[:4] == b'NES\x1A':
        prg_units = data[4]
        chr_units = data[5]
        trainer = (data[6] & 0x04) != 0
        prg_start = 16 + (512 if trainer else 0)
        prg_size = prg_units * 16384
        prg_size_limited = min(prg_size, 32768)  # Limite NROM
        chr_size = chr_units * 8192
        print(f"PRG units: {prg_units} ({prg_size} bytes, limitado a {prg_size_limited})")
        print(f"CHR units: {chr_units} ({chr_size} bytes)")
        print(f"Trainer: {'sim' if trainer else 'nao'}")
        print(f"PRG start: {prg_start}")
        print(f"Primeiros 16 bytes da PRG ROM: {[hex(b) for b in data[prg_start:prg_start+16]]}")
        print(f"Ultimos 16 bytes da PRG ROM: {[hex(b) for b in data[prg_start+prg_size_limited-16:prg_start+prg_size_limited]]}")
    else:
        print("Arquivo não possui cabeçalho iNES.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python test_rom_dump.py \"<C:/dev/6502/Castlevania (E).nes>\"')
    else:
        dump_rom_info(sys.argv[1])