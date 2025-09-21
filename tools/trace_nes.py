"""Trace runner para ROMs .nes usando o NROM mapper e hardware stub.

Uso:
  python tools\trace_nes.py "path/to/rom.nes" --max-instr 20000

O script tentará instalar o mapper, hardware stub (se disponível),
ativar o write logging no barramento e executar instruções até detectar
escritas. Mostra as primeiras escritas encontradas com o PC da instrução.
"""
from src.ppu import FullPPU
from src.mappers import NROMMapper
from src.Cpu import CPU
from src.Bus import Bus
import sys
import os
import argparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)


try:
    from src.hardware_stub import SimpleHardware
except Exception:
    SimpleHardware = None


def load_nes(path):
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) < 16 or data[0:4] != b'NES\x1A':
        raise ValueError('Arquivo não parece ser um .nes iNES válido')
    prg_units = data[4]
    chr_units = data[5]
    trainer = (data[6] & 0x04) != 0
    prg_start = 16 + (512 if trainer else 0)
    prg_size = prg_units * 16384
    prg = data[prg_start: prg_start + prg_size]
    chr_offset = prg_start + prg_size
    chr_size = chr_units * 8192
    chr = data[chr_offset: chr_offset + chr_size] if chr_size > 0 else b''
    return prg, chr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('rom', help='Caminho para o arquivo .nes')
    parser.add_argument('--max-instr', type=int, default=20000)
    parser.add_argument('--nmi-interval-instr', type=int, default=0,
                        help='Se >0, chama cpu.nmi() a cada N instruções para simular VBlank')
    parser.add_argument('--log-range', type=str, default='0x0000-0xFFFF',
                        help='Faixa hexadecimal de logging, ex: 0x8000-0x80FF')
    args = parser.parse_args()

    prg, chr = load_nes(args.rom)

    bus = Bus()
    cpu = CPU(bus)

    mapper = NROMMapper(prg)
    try:
        mapper.map(bus)
    except Exception:
        try:
            bus.install_mapper(mapper)
        except Exception:
            pass

    hw = None
    if SimpleHardware:
        try:
            hw = SimpleHardware()
            hw.map_to_bus(bus)
        except Exception:
            hw = None

    try:
        ppu = FullPPU()
        bus.ppu = ppu
        try:
            def _ppu_nmi_cb():
                try:
                    cpu.nmi()
                except Exception:
                    pass
                return None

            ppu.nmi_callback = _ppu_nmi_cb
        except Exception:
            pass
        try:
            if hw is not None:
                hw.ppu = ppu
        except Exception:
            pass
    except Exception:
        pass

    load_addr = 0x8000
    try:
        for i, b in enumerate(prg):
            bus.write(load_addr + i, b)
    except Exception:
        pass

    # write logging
    if hasattr(bus, 'enable_write_logging'):
        bus.clear_write_log()
        parts = args.log_range.split('-')
        start = int(parts[0], 0)
        end = int(parts[1], 0)
        bus.enable_write_logging(start, end)
    else:
        print('Bus não expõe write logging. Abortando.')
        return 2

    bus.write(0xFFFC, load_addr & 0xFF)
    bus.write(0xFFFD, (load_addr >> 8) & 0xFF)

    cpu.reset()

    if hasattr(bus, 'clear_write_log'):
        try:
            bus.clear_write_log()
        except Exception:
            pass

    instr = 0
    try:
        while instr < args.max_instr:
            instr += 1
            cpu.clock()
            if args.nmi_interval_instr and instr % args.nmi_interval_instr == 0:
                try:
                    cpu.nmi()
                except Exception:
                    pass
    except Exception as e:
        print('Erro durante execução:', e)

    wl = bus.get_write_log()
    print(f'Total writes logged: {len(wl)}')
    if wl:
        print('Writes logged (first 200):')
        for entry in wl[:200]:
            if len(entry) >= 3:
                a, v, pc = entry
                if pc is None:
                    print(f'  ${a:04X} <= ${v:02X} (instr @ None)')
                else:
                    try:
                        print(f'  ${a:04X} <= ${v:02X} (instr @ ${pc:04X})')
                    except Exception:
                        print(f'  ${a:04X} <= ${v:02X} (instr @ {pc})')
            else:
                a, v = entry
                print(f'  ${a:04X} <= ${v:02X}')

    return 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
