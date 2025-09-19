# Copilot instructions for the 6502 emulator repository

- Goal: implement and improve a MOS 6502 emulator (CPU, Bus, assembler, simple GUI). Primary files: `Cpu.py`, `Bus.py`, `assembler_6502_final.py`, `addressing_mode_detector.py`, `opcodes_table.py`, `emulador_gui.py`.

- Big picture:
  - `Bus` models a 64KB memory (bytearray). CPU reads/writes via `Bus.read`/`Bus.write`.
  - `CPU` (in `Cpu.py`) contains Registers, addressing-mode implementations, instruction implementations and a 256-entry lookup table mapping opcode -> (instr_func, addr_mode_func, base_cycles).
  - `assembler_6502_final.py` + `addressing_mode_detector.py` transform assembly source into machine bytes using `opcodes_table.OPCODE_TABLE`.
  - Tests under root (e.g., `test_Cpu.py`) show common usage patterns: instantiate `Bus()`, `CPU(bus)`, set PC (often 0x0200), write program bytes into memory and call `cpu.clock()` in a loop.

- Project-specific conventions and patterns (actionable):
  - Addressing-mode functions return (address_or_placeholder, page_crossed). Many instruction functions expect the addr-mode helper to advance PC or compute an address; use `fetch_operand(addr_mode_func)` helper to get operand value and page-crossing info. See `CPU.fetch_operand`.
  - Registers are stored in `Registers` fields (`a, x, y, sp, pc`) and status flags as booleans (`c, z, i, d, b, u, v, n`). Use `regs.get_status_byte(pushing=True/False)` and `regs.set_status_byte()` when manipulating status on stack.
  - The lookup table entries use bound methods: table[opcode] = (self.LDA, self.IMM, 2). New instructions should follow the same signature: instr(addr_mode_func) -> extra_cycles (int).
  - Stack is at page 0x01: push/pop helpers use addresses 0x0100 + SP. SP wraps at 0x00/0xFF.
  - Addressing-mode helper bugs are intentionally modeled to match real 6502 quirks (e.g., indirect JMP page‑boundary bug in `IND`). Preserve these for compatibility tests.
  - Assembler: `AddressingModeDetector.detect_addressing_mode(operand)` implements simple heuristics. The assembler computes branch offsets relative to PC+2 and enforces -128..127 range.

- Common developer workflows / commands (discoverable from tests and file layout):
  - Run unit tests quickly (uses Python unittest). From repository root:

    python -m unittest discover -v

  - Quick smoke test pattern (from tests): create `Bus()`, `CPU(bus)`, set `cpu.regs.pc = 0x0200`, write program bytes at that address via `bus.write(addr, byte)` and call `cpu.clock()` repeatedly.

- Integration points & extension notes for contributors:
  - Memory mapping: `Bus.read`/`write` directly access `ram` (bytearray). To add devices (PPU/APU/cartridge), modify `Bus` to route addresses to devices before reading/writing `ram`.
  - Assembler <-> Opcode table: `opcodes_table.py` is the authoritative mapping. Keep this in sync with assembler and addressing-mode detector.
  - GUI (`emulador_gui.py`) and tests expect CPU/Bus classes at project root. If refactoring into packages, update imports in tests.

- Examples to reference when implementing changes:
  - Implementing LDA immediate: see `Cpu.LDA` + `CPU.IMM` + table entry 0xA9 in `CPU._build_lookup_table`.
  - Generating machine code for relative branches: see `addressing_mode_detector.generate_machine_code` which calculates offset = target - (current_address + 2).
  - Stack push/pop conventions: `push_byte`, `push_word`, `pop_byte`, `pop_word` in `Cpu.py`.

- Tests & pitfalls seen in repo (explicit):
  - Tests import path may be stale: `test_Cpu.py` imports from `upload.Cpu` in some versions — current project places `Cpu.py` at repository root. If tests fail with import errors, adjust `PYTHONPATH` or tests to import `Cpu` from root.
  - Some methods referenced by tests (e.g., `CPU.set_reset_vector`) are not present — tests might be older. Prefer using `bus.write(0xFFFC, low); bus.write(0xFFFD, high)` to set reset vector before `cpu.reset()`.

- When making changes, keep these small rules:
  - Do not change the public API of `CPU(bus)` (it is used across tests and GUI). Preserve method signatures for `clock()`, `reset()`, `irq()`, `nmi()`.
  - Preserve 6502-specific behaviors (page-cross penalties, indirect JMP bug) unless explicitly intended to fix compatibility.
  - Keep `opcodes_table.py` as the single source of truth for opcodes; update assembler to use helper functions `get_opcode_info`.

- Where to look first when debugging:
  - `Cpu.clock()` — instruction fetch/decode/execute flow.
  - `CPU.lookup` construction — missing opcode entries result in `XXX` logging errors.
  - `Bus.read`/`Bus.write` — memory-related test failures often come from incorrect address or endian handling.

If any section is unclear or you'd like me to add brief code snippets (examples of a unit-test skeleton or a recipe to run a single test file) I can iterate — tell me what to expand.