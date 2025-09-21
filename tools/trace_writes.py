"""Harness rápido para montar um arquivo asm, carregar em $8000 e traçar writes na faixa $8000-$80FF.

Uso (executar a partir da raiz do repositório):
    python tools\trace_writes.py path/to/source.asm

O script usa Assembler, Bus e CPU do projeto.
"""
import argparse
from src.Cpu import CPU
from src.Bus import Bus
from src.assembler_6502_final import Assembler
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def main():
    parser = argparse.ArgumentParser(description='Trace writes in $8000-$80FF')
    parser.add_argument('input', nargs='?', default=os.path.join(
        ROOT, 'src', 'temp_code.asm'), help='Arquivo ASM para montar')
    parser.add_argument('--start', type=lambda x: int(x, 0),
                        default=0x8000, help='Endereço para carregar o binário')
    parser.add_argument('--max-instr', type=int, default=1000,
                        help='Máximo de instruções a executar')
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        src = f.read()

    asm = Assembler(debug_mode=False)
    try:
        binary = asm.assemble(src)
    except Exception as e:
        print('Assembly failed:', e)
        return 1

    bus = Bus()
    cpu = CPU(bus)

    load_addr = args.start & 0xFFFF
    for i, b in enumerate(binary):
        bus.write(load_addr + i, b)

    bus.write(0xFFFC, load_addr & 0xFF)
    bus.write(0xFFFD, (load_addr >> 8) & 0xFF)

    cpu.reset()

    if hasattr(bus, 'enable_write_logging'):
        bus.clear_write_log()
        bus.enable_write_logging(0x8000, 0x80FF)
    else:
        print('Bus não suporta write logging instrumentado nesta versão')

    print(
        f'Loaded {len(binary)} bytes at ${load_addr:04X}, PC=${cpu.regs.pc:04X}')

    instr = 0
    try:
        while instr < args.max_instr:
            pc_before = cpu.regs.pc
            cycles = cpu.clock()
            instr += 1
            wl = bus.get_write_log() if hasattr(bus, 'get_write_log') else []
            if wl:
                print('Writes logged (first 32):')
                for entry in wl[:32]:
                    if len(entry) >= 3:
                        a, v, pc = entry
                        pc_str = f' (instr @ ${pc:04X})' if pc is not None else ''
                        print(f'  ${a:04X} <= ${v:02X}{pc_str}')
                    else:
                        a, v = entry
                        print(f'  ${a:04X} <= ${v:02X}')
                break
            if not (0x0000 <= cpu.regs.pc <= 0xFFFF):
                break
        else:
            print('Máximo de instruções executadas sem writes detectadas')

    except Exception as e:
        print('Erro durante execução:', e)

    # Estatísticas finais
    if hasattr(bus, 'get_write_log'):
        wl = bus.get_write_log()
        print(f'Total writes logged: {len(wl)}')

    print('Done')
    return 0


if __name__ == "__main__":
    sys.exit(main())
