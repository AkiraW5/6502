from src.Cpu import CPU, Bus

def main():
    bus = Bus()
    cpu = CPU(bus)

    # Program (at 0x0200): LDA #$01 ; STA $0020 ; BRK
    program = [0xA9, 0x01,  # LDA #$01
               0x8D, 0x20, 0x00,  # STA $0020 (little-endian)
               0x00]  # BRK

    start_addr = 0x0200
    for i, b in enumerate(program):
        bus.write(start_addr + i, b)

    bus.write(0xFFFC, start_addr & 0xFF)
    bus.write(0xFFFD, (start_addr >> 8) & 0xFF)

    cpu.reset()

    print(f"PC after reset: {cpu.regs.pc:04X}")

    max_cycles = 50
    cycles = 0
    while not cpu.halted and cycles < max_cycles:
        cpu.clock()
        cycles += 1

    print(f"Ran {cycles} cycles")
    print(f"Registers: A={cpu.regs.a:02X} X={cpu.regs.x:02X} Y={cpu.regs.y:02X} SP={cpu.regs.sp:02X} PC={cpu.regs.pc:04X}")
    value = bus.read(0x0020)
    print(f"Memory[0x0020] = {value:02X}")

    if value == 0x01:
        print("Smoke test PASSED: STA stored the value correctly.")
    else:
        print("Smoke test FAILED: unexpected memory value.")

if __name__ == '__main__':
    main()
