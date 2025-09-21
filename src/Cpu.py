# -*- coding: utf-8 -*-
"""
Emulador do microprocessador MOS 6502 em Python.

Este módulo contém as classes para simular os Registradores (`Registers`),
o Barramento de Memória (`Bus`) e a Unidade Central de Processamento (`CPU`).
O objetivo é fornecer uma simulação funcional básica da arquitetura 6502.
"""

import logging
from typing import Callable, List, Tuple, Any

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class Registers:
    """Representa os registradores da CPU 6502."""

    def __init__(self):
        """Inicializa todos os registradores com valores padrão de reset.
        Nota: SP é inicializado em 0xFD, e a flag I (Interrupt Disable) em 1.
        """
        # Registradores principais de 8 bits
        self.a = 0x00  # Acumulador
        self.x = 0x00  # Registrador X
        self.y = 0x00  # Registrador Y
        self.sp = 0xFD  # Ponteiro de Pilha (Stack Pointer)

        # Contador de Programa (Program Counter) de 16 bits
        self.pc = 0x0000

        # Registrador de Status (P) - Flags representadas como atributos individuais
        self.c = 0  # Carry Flag (Bit 0)
        self.z = 0  # Zero Flag (Bit 1)
        self.i = 1  # Interrupt Disable Flag (Bit 2)
        # Decimal Mode Flag (Bit 3) - Não suportado funcionalmente neste emulador
        self.d = 0
        # Break Command Flag (Bit 4) - Usado ao empilhar durante BRK/IRQ/NMI
        self.b = 0
        self.u = 1  # Unused Flag (Bit 5) - Sempre 1
        self.v = 0  # Overflow Flag (Bit 6)
        self.n = 0  # Negative Flag (Bit 7)

    def get_status_byte(self, pushing=False):
        """Monta e retorna o valor do registrador de status (P) como um byte.

        Args:
            pushing (bool): Indica se o status está sendo empilhado (PHP, BRK, IRQ, NMI).
                          Se True, a flag B é considerada 1.
                          Se False (PLP), a flag B é considerada 0.
                          A flag U (Unused) é sempre 1.

        Returns:
            int: O valor de 8 bits do registrador de status.
        """
        # A flag B só é 1 no byte empilhado se for um BRK ou uma interrupção (ou PHP)
        # PHP explicitamente seta B=1 no valor empilhado.
        # BRK/IRQ/NMI setam B=1 implicitamente no valor empilhado.
        # PLP ignora os bits B e U do valor desempilhado.
        b_flag_val = self.b
        if pushing:
            b_flag_val = 1  # B é 1 quando empurrado por PHP, BRK, IRQ, NMI

        return (
            (self.n << 7) |
            (self.v << 6) |
            (1 << 5) |  # Flag U (Unused) é sempre 1
            (b_flag_val << 4) |
            (self.d << 3) |
            (self.i << 2) |
            (self.z << 1) |
            self.c
        )

    def set_status_byte(self, value):
        """Define as flags do registrador de status (P) a partir de um byte.

        As flags B (Break) e U (Unused) são ignoradas ao definir o status via PLP,
        conforme o comportamento do hardware 6502.

        Args:
            value (int): O byte contendo o novo estado das flags.
        """
        self.n = (value >> 7) & 1
        self.v = (value >> 6) & 1
        # Bit 5 (U) é ignorado, mantido como 1 internamente.
        self.u = 1
        # Bit 4 (B) é ignorado, mantém seu valor interno.
        # self.b = (value >> 4) & 1 # Não faz isso
        self.d = (value >> 3) & 1
        self.i = (value >> 2) & 1
        self.z = (value >> 1) & 1
        self.c = value & 1

    def update_flag_z(self, result):
        """Atualiza a flag Zero (Z) se o resultado for 0."""
        self.z = 1 if (result & 0xFF) == 0 else 0

    def update_flag_n(self, result):
        """Atualiza a flag Negativa (N) se o bit 7 do resultado for 1."""
        self.n = 1 if (result & 0x80) else 0


class Bus:
    """Representa o barramento de memória, conectando CPU e RAM (e potencialmente outros dispositivos)."""

    def __init__(self):
        """Inicializa a memória RAM com 64KB (0x0000 - 0xFFFF) de zeros."""
        # Simula 64KB de RAM usando bytearray para eficiência
        self.ram = bytearray(64 * 1024)

    def read(self, address):
        """Lê um byte da memória no endereço especificado.

        Args:
            address (int): O endereço de 16 bits para leitura.

        Returns:
            int: O valor do byte lido (0-255).
        """
        address &= 0xFFFF  # Garante que o endereço esteja dentro do espaço de 16 bits
        # TODO: Implementar mapeamento de memória para PPU, APU, cartucho, etc.
        #       se este emulador for expandido para um sistema completo (ex: NES).
        #       Por enquanto, lê diretamente da RAM simulada.
        return self.ram[address]

    def read_word(self, address):
        """Lê uma palavra (16 bits, little-endian) da memória.

        Args:
            address (int): O endereço de 16 bits do byte menos significativo.

        Returns:
            int: O valor da palavra de 16 bits lida.
        """
        address &= 0xFFFF
        low_byte = self.read(address)
        # Garante wrap-around se ler em 0xFFFF
        high_byte = self.read((address + 1) & 0xFFFF)
        return (high_byte << 8) | low_byte

    def write(self, address, value):
        """Escreve um byte na memória no endereço especificado.

        Args:
            address (int): O endereço de 16 bits para escrita.
            value (int): O valor do byte (0-255) a ser escrito.
        """
        address &= 0xFFFF
        value &= 0xFF  # Garante que o valor seja um byte
        # TODO: Implementar mapeamento de memória para escrita.
        self.ram[address] = value


class CPU:
    """Representa a unidade central de processamento (CPU) MOS 6502."""

    def __init__(self, bus):
        """Inicializa a CPU, conectando-a ao barramento fornecido.

        Args:
            bus (Bus): A instância do barramento de memória a ser usada pela CPU.
        """
        self.bus = bus  # Usa o barramento passado, não cria um novo
        self.regs = Registers()
        self.verbose = False  # verbosity flag to enable periodic debug prints
        self.halted = False
        self.cycles = 0  # Contador de ciclos para a instrução *atual*
        self.total_cycles = 0  # Contador de ciclos *total* desde o reset
        self.addr_rel = 0  # Endereço relativo para instruções de branch
        self.addr_abs = 0  # Endereço absoluto para acesso à memória

        # Tipagem explícita para ajudar analisadores estáticos: cada entrada é
        # Tuple[Callable[[Callable[..., Any]], int], Callable[..., Tuple[int, bool]], int]
        self.lookup: List[Tuple[Callable[[Any], int], Callable[[],
                                                               Tuple[int, bool]], int]] = self._build_lookup_table()

    def _build_lookup_table(self):
        """Constrói e retorna a tabela de lookup para decodificação rápida de opcodes."""
        # Inicializa a tabela com uma instrução ilegal padrão (XXX)
        # Isso garante que opcodes não mapeados sejam tratados.
        # Create a fresh list with the default entry cloned per slot to avoid
        # confusing the type checker with a single repeated tuple instance.
        default_entry: Tuple[Callable[[Any], int], Callable[[],
                                                            Tuple[int, bool]], int] = (self.XXX, self.IMP, 2)
        table: List[Tuple[Callable[[Any], int], Callable[[], Tuple[int, bool]], int]] = [
            default_entry for _ in range(256)]

        # Mapeamento das instruções implementadas
        # Formato: table[OPCODE] = (self.NOME_INSTRUCAO, self.MODO_ENDEREÇAMENTO, CICLOS_BASE)
        # Ciclos base podem ser ajustados por ciclos adicionais (ex: cruzamento de página)

        # --- Instruções de Carga (Load) ---
        table[0xA9] = (self.LDA, self.IMM, 2)
        table[0xA5] = (self.LDA, self.ZP0, 3)
        table[0xB5] = (self.LDA, self.ZPX, 4)
        table[0xAD] = (self.LDA, self.ABS, 4)
        table[0xBD] = (self.LDA, self.ABX, 4)
        table[0xB9] = (self.LDA, self.ABY, 4)
        table[0xA1] = (self.LDA, self.IZX, 6)
        table[0xB1] = (self.LDA, self.IZY, 5)
        table[0xA2] = (self.LDX, self.IMM, 2)
        table[0xA6] = (self.LDX, self.ZP0, 3)
        table[0xB6] = (self.LDX, self.ZPY, 4)
        table[0xAE] = (self.LDX, self.ABS, 4)
        table[0xBE] = (self.LDX, self.ABY, 4)
        table[0xA0] = (self.LDY, self.IMM, 2)
        table[0xA4] = (self.LDY, self.ZP0, 3)
        table[0xB4] = (self.LDY, self.ZPX, 4)
        table[0xAC] = (self.LDY, self.ABS, 4)
        table[0xBC] = (self.LDY, self.ABX, 4)

        # --- Instruções de Armazenamento (Store) ---
        table[0x85] = (self.STA, self.ZP0, 3)
        table[0x95] = (self.STA, self.ZPX, 4)
        table[0x8D] = (self.STA, self.ABS, 4)
        table[0x9D] = (self.STA, self.ABX, 5)
        table[0x99] = (self.STA, self.ABY, 5)
        table[0x81] = (self.STA, self.IZX, 6)
        table[0x91] = (self.STA, self.IZY, 6)
        table[0x86] = (self.STX, self.ZP0, 3)
        table[0x96] = (self.STX, self.ZPY, 4)
        table[0x8E] = (self.STX, self.ABS, 4)
        table[0x84] = (self.STY, self.ZP0, 3)
        table[0x94] = (self.STY, self.ZPX, 4)
        table[0x8C] = (self.STY, self.ABS, 4)

        # --- Instruções Aritméticas ---
        table[0x69] = (self.ADC, self.IMM, 2)
        table[0x65] = (self.ADC, self.ZP0, 3)
        table[0x75] = (self.ADC, self.ZPX, 4)
        table[0x6D] = (self.ADC, self.ABS, 4)
        table[0x7D] = (self.ADC, self.ABX, 4)
        table[0x79] = (self.ADC, self.ABY, 4)
        table[0x61] = (self.ADC, self.IZX, 6)
        table[0x71] = (self.ADC, self.IZY, 5)
        # SBC - Subtract with Carry
        table[0xE9] = (self.SBC, self.IMM, 2)
        table[0xE5] = (self.SBC, self.ZP0, 3)
        table[0xF5] = (self.SBC, self.ZPX, 4)
        table[0xED] = (self.SBC, self.ABS, 4)
        table[0xFD] = (self.SBC, self.ABX, 4)
        table[0xF9] = (self.SBC, self.ABY, 4)
        table[0xE1] = (self.SBC, self.IZX, 6)
        table[0xF1] = (self.SBC, self.IZY, 5)

        # --- Instruções Lógicas ---
        table[0x29] = (self.AND, self.IMM, 2)
        table[0x25] = (self.AND, self.ZP0, 3)
        table[0x35] = (self.AND, self.ZPX, 4)
        table[0x2D] = (self.AND, self.ABS, 4)
        table[0x3D] = (self.AND, self.ABX, 4)
        table[0x39] = (self.AND, self.ABY, 4)
        table[0x21] = (self.AND, self.IZX, 6)
        table[0x31] = (self.AND, self.IZY, 5)
        # ORA - Logical OR
        table[0x09] = (self.ORA, self.IMM, 2)
        table[0x05] = (self.ORA, self.ZP0, 3)
        table[0x15] = (self.ORA, self.ZPX, 4)
        table[0x0D] = (self.ORA, self.ABS, 4)
        table[0x1D] = (self.ORA, self.ABX, 4)
        table[0x19] = (self.ORA, self.ABY, 4)
        table[0x01] = (self.ORA, self.IZX, 6)
        table[0x11] = (self.ORA, self.IZY, 5)

        # EOR - Exclusive OR
        table[0x49] = (self.EOR, self.IMM, 2)
        table[0x45] = (self.EOR, self.ZP0, 3)
        table[0x55] = (self.EOR, self.ZPX, 4)
        table[0x4D] = (self.EOR, self.ABS, 4)
        table[0x5D] = (self.EOR, self.ABX, 4)
        table[0x59] = (self.EOR, self.ABY, 4)
        table[0x41] = (self.EOR, self.IZX, 6)
        table[0x51] = (self.EOR, self.IZY, 5)

        # --- Instruções de Deslocamento e Rotação ---
        table[0x0A] = (self.ASL, self.ACC, 2)
        table[0x06] = (self.ASL, self.ZP0, 5)
        table[0x16] = (self.ASL, self.ZPX, 6)
        table[0x0E] = (self.ASL, self.ABS, 6)
        table[0x1E] = (self.ASL, self.ABX, 7)
        # LSR - Logical Shift Right
        table[0x4A] = (self.LSR, self.ACC, 2)
        table[0x46] = (self.LSR, self.ZP0, 5)
        table[0x56] = (self.LSR, self.ZPX, 6)
        table[0x4E] = (self.LSR, self.ABS, 6)
        table[0x5E] = (self.LSR, self.ABX, 7)

        # ROL - Rotate Left
        table[0x2A] = (self.ROL, self.ACC, 2)
        table[0x26] = (self.ROL, self.ZP0, 5)
        table[0x36] = (self.ROL, self.ZPX, 6)
        table[0x2E] = (self.ROL, self.ABS, 6)
        table[0x3E] = (self.ROL, self.ABX, 7)

        # ROR - Rotate Right
        table[0x6A] = (self.ROR, self.ACC, 2)
        table[0x66] = (self.ROR, self.ZP0, 5)
        table[0x76] = (self.ROR, self.ZPX, 6)
        table[0x6E] = (self.ROR, self.ABS, 6)
        table[0x7E] = (self.ROR, self.ABX, 7)

        # --- Instruções de Incremento e Decremento ---
        table[0xE6] = (self.INC, self.ZP0, 5)
        table[0xF6] = (self.INC, self.ZPX, 6)
        table[0xEE] = (self.INC, self.ABS, 6)
        table[0xFE] = (self.INC, self.ABX, 7)
        table[0xC6] = (self.DEC, self.ZP0, 5)
        table[0xD6] = (self.DEC, self.ZPX, 6)
        table[0xCE] = (self.DEC, self.ABS, 6)
        table[0xDE] = (self.DEC, self.ABX, 7)
        table[0xE8] = (self.INX, self.IMP, 2)
        table[0xC8] = (self.INY, self.IMP, 2)
        table[0xCA] = (self.DEX, self.IMP, 2)
        table[0x88] = (self.DEY, self.IMP, 2)

        # --- Instruções de Pilha (Stack) ---
        table[0x48] = (self.PHA, self.IMP, 3)
        table[0x68] = (self.PLA, self.IMP, 4)
        table[0x08] = (self.PHP, self.IMP, 3)
        table[0x28] = (self.PLP, self.IMP, 4)

        # --- Instruções de Salto (Jump) e Sub-rotina ---
        table[0x4C] = (self.JMP, self.ABS, 3)
        table[0x6C] = (self.JMP, self.IND, 5)
        table[0x20] = (self.JSR, self.ABS, 6)
        table[0x60] = (self.RTS, self.IMP, 6)
        table[0x40] = (self.RTI, self.IMP, 6)

        # --- Instruções de Desvio Condicional (Branch) ---
        table[0x90] = (self.BCC, self.REL, 2)  # BCC - Branch if Carry Clear
        table[0xB0] = (self.BCS, self.REL, 2)  # BCS - Branch if Carry Set
        table[0xF0] = (self.BEQ, self.REL, 2)  # BEQ - Branch if Equal
        table[0x30] = (self.BMI, self.REL, 2)  # BMI - Branch if Minus
        table[0xD0] = (self.BNE, self.REL, 2)  # BNE - Branch if Not Equal
        table[0x10] = (self.BPL, self.REL, 2)  # BPL - Branch if Plus
        table[0x50] = (self.BVC, self.REL, 2)  # BVC - Branch if Overflow Clear
        table[0x70] = (self.BVS, self.REL, 2)  # BVS - Branch if Overflow Set

        # --- Instruções de Comparação ---
        table[0xC9] = (self.CMP, self.IMM, 2)
        table[0xC5] = (self.CMP, self.ZP0, 3)
        table[0xD5] = (self.CMP, self.ZPX, 4)
        table[0xCD] = (self.CMP, self.ABS, 4)
        table[0xDD] = (self.CMP, self.ABX, 4)
        table[0xD9] = (self.CMP, self.ABY, 4)
        table[0xC1] = (self.CMP, self.IZX, 6)
        table[0xD1] = (self.CMP, self.IZY, 5)
        table[0xE0] = (self.CPX, self.IMM, 2)
        table[0xE4] = (self.CPX, self.ZP0, 3)
        table[0xEC] = (self.CPX, self.ABS, 4)
        table[0xC0] = (self.CPY, self.IMM, 2)
        table[0xC4] = (self.CPY, self.ZP0, 3)
        table[0xCC] = (self.CPY, self.ABS, 4)
        table[0x24] = (self.BIT, self.ZP0, 3)
        table[0x2C] = (self.BIT, self.ABS, 4)

        # --- Instruções de Transferência entre Registradores ---
        table[0xAA] = (self.TAX, self.IMP, 2)
        table[0x8A] = (self.TXA, self.IMP, 2)
        table[0xA8] = (self.TAY, self.IMP, 2)
        table[0x98] = (self.TYA, self.IMP, 2)
        table[0xBA] = (self.TSX, self.IMP, 2)
        table[0x9A] = (self.TXS, self.IMP, 2)

        # --- Instruções de Manipulação de Flags ---
        table[0x18] = (self.CLC, self.IMP, 2)
        table[0x38] = (self.SEC, self.IMP, 2)
        table[0x58] = (self.CLI, self.IMP, 2)
        table[0x78] = (self.SEI, self.IMP, 2)
        table[0xD8] = (self.CLD, self.IMP, 2)
        table[0xF8] = (self.SED, self.IMP, 2)
        table[0xB8] = (self.CLV, self.IMP, 2)

        # --- Outras Instruções ---
        table[0x00] = (self.BRK, self.IMP, 7)  # Break / Interrupt
        table[0xEA] = (self.NOP, self.IMP, 2)  # No Operation
        # TODO: Mapear outras NOPs não oficiais se necessário

        return table

    # --- Funções de Leitura e Escrita no Barramento (Wrappers) ---
    def read(self, address):
        """Lê um byte do barramento no endereço especificado."""
        return self.bus.read(address)

    def write(self, address, value):
        """Escreve um byte no barramento no endereço especificado."""
        self.bus.write(address, value)

    # --- Funções de Manipulação da Pilha (Stack) ---
    def push_byte(self, value):
        """Empilha um byte na pilha (endereço 0x0100 + SP) e decrementa SP."""
        self.write(0x0100 + self.regs.sp, value & 0xFF)
        # SP wraps around from 0x00 to 0xFF
        self.regs.sp = (self.regs.sp - 1) & 0xFF

    def push_word(self, value):
        """Empilha uma palavra (16 bits) na pilha, byte mais significativo primeiro."""
        self.push_byte((value >> 8) & 0xFF)  # High byte
        self.push_byte(value & 0xFF)        # Low byte

    def pop_byte(self):
        """Incrementa SP e desempilha um byte da pilha."""
        self.regs.sp = (
            self.regs.sp + 1) & 0xFF  # SP wraps around from 0xFF to 0x00
        return self.read(0x0100 + self.regs.sp)

    def pop_word(self):
        """Desempilha uma palavra (16 bits) da pilha, byte menos significativo primeiro."""
        # Ordem: incrementa SP, lê low byte; incrementa SP, lê high byte.
        low_byte = self.pop_byte()
        high_byte = self.pop_byte()
        return (high_byte << 8) | low_byte

    # --- Funções de Busca de Bytes da Instrução (Fetch) ---
    def fetch_byte(self):
        """Busca um byte da memória no endereço apontado por PC e incrementa PC."""
        value = self.read(self.regs.pc)
        self.regs.pc = (self.regs.pc + 1) & 0xFFFF  # PC wraps around
        return value

    def fetch_word(self):
        """Busca uma palavra (16 bits, little-endian) da memória a partir de PC e incrementa PC duas vezes."""
        # Lê little-endian
        low_byte = self.fetch_byte()
        high_byte = self.fetch_byte()
        return (high_byte << 8) | low_byte

    # --- Implementação dos Modos de Endereçamento ---
    # Cada função retorna uma tupla: (endereço_efetivo, page_crossed)
    # - endereço_efetivo: O endereço final calculado pelo modo.
    #                     Para IMP e ACC, retorna 0 (não usado).
    #                     Para IMM, retorna o endereço do operando imediato (PC após opcode).
    #                     Para REL, retorna o *offset* relativo.
    # - page_crossed:   Booleano indicando se o cálculo do endereço cruzou um limite de página (0x100 bytes).
    #                     Importante para calcular ciclos adicionais em algumas instruções.

    def IMP(self):  # Implied
        """Modo Implícito: Operando está implícito na instrução."""
        return 0, False

    def ACC(self):  # Accumulator
        """Modo Acumulador: Operando é o registrador Acumulador."""
        return 0, False

    def IMM(self):  # Immediate
        """Modo Imediato: Operando é o byte seguinte ao opcode."""
        addr = self.regs.pc
        self.regs.pc = (self.regs.pc + 1) & 0xFFFF
        return addr, False

    def ZP0(self):  # Zero Page
        """Modo Página Zero: Operando é um endereço de 8 bits (0x00xx)."""
        addr = self.fetch_byte() & 0x00FF
        return addr, False

    def ZPX(self):  # Zero Page, X
        """Modo Página Zero, Indexado com X: Endereço = byte + X (com wrap na página zero)."""
        addr = (self.fetch_byte() + self.regs.x) & 0x00FF
        return addr, False

    def ZPY(self):  # Zero Page, Y
        """Modo Página Zero, Indexado com Y: Endereço = byte + Y (com wrap na página zero)."""
        # Usado apenas por LDX e STX
        addr = (self.fetch_byte() + self.regs.y) & 0x00FF
        return addr, False

    def ABS(self):  # Absolute
        """Modo Absoluto: Operando é um endereço completo de 16 bits."""
        addr = self.fetch_word()
        return addr, False

    def ABX(self):  # Absolute, X
        """Modo Absoluto, Indexado com X: Endereço = word + X."""
        base_addr = self.fetch_word()
        addr = (base_addr + self.regs.x) & 0xFFFF
        page_crossed = (base_addr & 0xFF00) != (addr & 0xFF00)
        return addr, page_crossed

    def ABY(self):  # Absolute, Y
        """Modo Absoluto, Indexado com Y: Endereço = word + Y."""
        base_addr = self.fetch_word()
        addr = (base_addr + self.regs.y) & 0xFFFF
        page_crossed = (base_addr & 0xFF00) != (addr & 0xFF00)
        return addr, page_crossed

    def IND(self):  # Indirect
        """Modo Indireto: Lê um endereço de 16 bits e usa o valor nesse endereço como endereço final.

        Nota: Implementa o bug do 6502 onde, se o endereço indireto estiver no final de uma página,
        o byte alto é lido do início da mesma página, não da próxima.
        """
        ptr = self.fetch_word()

        # Simula o bug do 6502 na leitura indireta
        if (ptr & 0x00FF) == 0x00FF:
            # Se o ponteiro estiver no final de uma página, o byte alto é lido do início da mesma página
            low_byte = self.read(ptr)
            high_byte = self.read(ptr & 0xFF00)  # Wrap around na mesma página
        else:
            # Caso normal: lê dois bytes consecutivos
            low_byte = self.read(ptr)
            high_byte = self.read(ptr + 1)

        addr = (high_byte << 8) | low_byte
        return addr, False

    def IZX(self):  # Indexed Indirect (Pre-Indexed)
        """Modo Indexado Indireto (X): Endereço = conteúdo em [(byte + X) & 0xFF, (byte + X + 1) & 0xFF]."""
        # Lê o byte base da página zero
        base = self.fetch_byte()

        # Adiciona X com wrap na página zero
        ptr = (base + self.regs.x) & 0xFF

        # Lê o endereço de 16 bits da página zero
        # Simula o wrap-around na página zero
        low_byte = self.read(ptr)
        high_byte = self.read((ptr + 1) & 0xFF)

        addr = (high_byte << 8) | low_byte
        return addr, False

    def IZY(self):  # Indirect Indexed (Post-Indexed)
        """Modo Indireto Indexado (Y): Endereço = conteúdo em [byte, (byte + 1) & 0xFF] + Y."""
        # Lê o byte base da página zero
        base = self.fetch_byte()

        # Lê o endereço de 16 bits da página zero
        # Simula o wrap-around na página zero
        low_byte = self.read(base)
        high_byte = self.read((base + 1) & 0xFF)

        # Forma o endereço base de 16 bits
        base_addr = (high_byte << 8) | low_byte

        # Adiciona Y ao endereço base
        addr = (base_addr + self.regs.y) & 0xFFFF

        # Verifica se houve cruzamento de página
        page_crossed = (base_addr & 0xFF00) != (addr & 0xFF00)

        return addr, page_crossed

    def REL(self):  # Relative (Para Branches)
        """Modo Relativo: Operando é um offset de 8 bits com sinal relativo ao PC."""
        offset = self.fetch_byte()
        # Converte para offset com sinal (complemento de dois)
        if offset & 0x80:
            offset = offset - 0x100
        # Armazena o offset para uso na instrução de branch
        self.addr_rel = offset
        return offset, False

    # --- Função Auxiliar para Buscar Operando ---
    def fetch_operand(self, addr_mode_func):
        """Busca o valor do operando baseado no modo de endereçamento.

        Para modos que operam diretamente em registradores (ACC, IMP) ou 
        usam um offset (REL), o \'valor\' retornado pode não ser diretamente útil,
        mas a estrutura é mantida. A flag page_crossed é relevante.

        Args:
            addr_mode_func: A função do modo de endereçamento a ser usada.

        Returns:
            tuple: (valor_do_operando, page_crossed)
                   - valor_do_operando: O byte lido da memória ou do registrador.
                   - page_crossed: Booleano indicando se houve cruzamento de página.
        """
        if addr_mode_func == self.ACC:  # Modo Acumulador
            return self.regs.a, False
        elif addr_mode_func == self.IMM:  # Modo Imediato
            addr, page_crossed = addr_mode_func()
            return self.read(addr), page_crossed
        elif addr_mode_func == self.IMP or addr_mode_func == self.REL:
            # Modos Implícito e Relativo não têm operando de memória neste sentido
            # REL retorna offset, IMP não retorna nada útil aqui.
            # A função do modo já foi chamada para avançar o PC se necessário (IMM, ZP0, etc.)
            # ou para obter o offset (REL).
            # Chamamos novamente para obter page_crossed (geralmente False aqui)
            _, page_crossed = addr_mode_func()
            return 0, page_crossed  # Retorna 0 como placeholder
        else:  # Outros modos (ZP, ABS, IZX, IZY, etc.) que retornam endereço efetivo
            addr, page_crossed = addr_mode_func()
            return self.read(addr), page_crossed

    # --- Implementação das Instruções da CPU ---
    # Cada função de instrução recebe como argumento a função do modo de endereçamento.
    # Retorna o número de ciclos *adicionais* (além dos ciclos base definidos na lookup table).
    # Ciclos adicionais ocorrem tipicamente por cruzamento de página ou em branches tomados.

    # --- Instruções Aritméticas ---
    def ADC(self, addr_mode_func):
        """Instrução ADC: Add with Carry (Adiciona operando e Carry ao Acumulador)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)
        # Realiza a soma em 16 bits para detectar carry
        temp = self.regs.a + operand + self.regs.c

        # Atualiza Flags:
        self.regs.c = 1 if temp > 0xFF else 0  # Carry
        self.regs.update_flag_z(temp)          # Zero
        # Overflow (V): Ocorre se o sinal do resultado for diferente do sinal de ambos os operandos
        # (considerando A e operando como números com sinal de 8 bits)
        # Simplificação: (~(A ^ operand) & (A ^ result)) & 0x80
        self.regs.v = 1 if (~(self.regs.a ^ operand) &
                            (self.regs.a ^ temp)) & 0x80 else 0
        self.regs.update_flag_n(temp)          # Negative

        # Armazena o resultado de 8 bits no acumulador
        self.regs.a = temp & 0xFF
        # Retorna ciclo adicional se a página foi cruzada no cálculo do endereço
        return 1 if page_crossed else 0

    def SBC(self, addr_mode_func):
        """Instrução SBC: Subtract with Carry (A = A - operando - (1 - C))."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)
        # Inverte o operando para usar lógica de ADC em complemento de dois
        value = operand ^ 0xFF
        temp = self.regs.a + value + self.regs.c

        # Atualiza flags
        self.regs.c = 1 if temp > 0xFF else 0
        self.regs.update_flag_z(temp)
        self.regs.v = 1 if (~(self.regs.a ^ operand) &
                            (self.regs.a ^ temp)) & 0x80 else 0
        self.regs.update_flag_n(temp)

        self.regs.a = temp & 0xFF
        return 1 if page_crossed else 0

    # --- Instruções Lógicas ---
    def AND(self, addr_mode_func):
        """Instrução AND: Logical AND (Acumulador E Operando)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)
        self.regs.a &= operand
        self.regs.update_flag_z(self.regs.a)
        self.regs.update_flag_n(self.regs.a)
        return 1 if page_crossed else 0

    def ORA(self, addr_mode_func):
        """Instrução ORA: Logical OR (A = A | operando)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)
        self.regs.a |= operand
        self.regs.update_flag_z(self.regs.a)
        self.regs.update_flag_n(self.regs.a)
        return 1 if page_crossed else 0

    def EOR(self, addr_mode_func):
        """Instrução EOR: Exclusive OR (A = A ^ operando)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)
        self.regs.a ^= operand
        self.regs.update_flag_z(self.regs.a)
        self.regs.update_flag_n(self.regs.a)
        return 1 if page_crossed else 0

    # TODO: Implementar EOR, ORA

    # --- Instruções de Deslocamento e Rotação ---
    def ASL(self, addr_mode_func):
        """Instrução ASL: Arithmetic Shift Left (Desloca bits para a esquerda)."""
        if addr_mode_func == self.ACC:
            operand = self.regs.a
            # Bit 7 vai para o Carry
            self.regs.c = 1 if (operand & 0x80) else 0
            result = (operand << 1) & 0xFF
            self.regs.a = result
            self.regs.update_flag_z(result)
            self.regs.update_flag_n(result)
            return 0  # Sem ciclos adicionais
        else:
            addr, _ = addr_mode_func()  # Não há page crossed penalty para ASL memória
            operand = self.read(addr)
            self.regs.c = 1 if (operand & 0x80) else 0
            result = (operand << 1) & 0xFF
            self.write(addr, result)
            self.regs.update_flag_z(result)
            self.regs.update_flag_n(result)
            return 0

    # TODO: Implementar LSR, ROL, ROR

    # --- Instruções de Carga ---
    def LDA(self, addr_mode_func):
        """Instrução LDA: Load Accumulator (Carrega valor no Acumulador)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)
        self.regs.a = operand
        self.regs.update_flag_z(self.regs.a)
        self.regs.update_flag_n(self.regs.a)
        return 1 if page_crossed else 0

    def LDX(self, addr_mode_func):
        """Instrução LDX: Load X Register (Carrega valor no Registrador X)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)
        self.regs.x = operand
        self.regs.update_flag_z(self.regs.x)
        self.regs.update_flag_n(self.regs.x)
        return 1 if page_crossed else 0

    def LDY(self, addr_mode_func):
        """Instrução LDY: Load Y Register (Carrega valor no Registrador Y)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)
        self.regs.y = operand
        self.regs.update_flag_z(self.regs.y)
        self.regs.update_flag_n(self.regs.y)
        return 1 if page_crossed else 0

    # --- Instruções de Armazenamento ---
    def STA(self, addr_mode_func):
        """Instrução STA: Store Accumulator (Armazena Acumulador na memória)."""
        # Note: Modos indexados de STA (ABX, ABY, IZY) podem ter ciclos diferentes,
        # mas não adicionam ciclo por cruzamento de página. Os ciclos base já refletem isso.
        addr, _ = addr_mode_func()
        self.write(addr, self.regs.a)
        return 0

    def LSR(self, addr_mode_func):
        """Instrução LSR: Logical Shift Right."""
        if addr_mode_func == self.ACC:
            operand = self.regs.a
            self.regs.c = operand & 0x01
            result = (operand >> 1) & 0xFF
            self.regs.a = result
            self.regs.update_flag_z(result)
            self.regs.update_flag_n(result)
            return 0
        else:
            addr, _ = addr_mode_func()
            operand = self.read(addr)
            self.regs.c = operand & 0x01
            result = (operand >> 1) & 0xFF
            self.write(addr, result)
            self.regs.update_flag_z(result)
            self.regs.update_flag_n(result)
            return 0

    def ROL(self, addr_mode_func):
        """Instrução ROL: Rotate Left através do Carry."""
        if addr_mode_func == self.ACC:
            operand = self.regs.a
            new_c = 1 if (operand & 0x80) else 0
            result = ((operand << 1) & 0xFF) | (self.regs.c & 0x1)
            self.regs.c = new_c
            self.regs.a = result
            self.regs.update_flag_z(result)
            self.regs.update_flag_n(result)
            return 0
        else:
            addr, _ = addr_mode_func()
            operand = self.read(addr)
            new_c = 1 if (operand & 0x80) else 0
            result = ((operand << 1) & 0xFF) | (self.regs.c & 0x1)
            self.regs.c = new_c
            self.write(addr, result)
            self.regs.update_flag_z(result)
            self.regs.update_flag_n(result)
            return 0

    def ROR(self, addr_mode_func):
        """Instrução ROR: Rotate Right através do Carry."""
        if addr_mode_func == self.ACC:
            operand = self.regs.a
            new_c = 1 if (operand & 0x01) else 0
            result = ((self.regs.c << 7) & 0x80) | (operand >> 1)
            self.regs.c = new_c
            self.regs.a = result & 0xFF
            self.regs.update_flag_z(self.regs.a)
            self.regs.update_flag_n(self.regs.a)
            return 0
        else:
            addr, _ = addr_mode_func()
            operand = self.read(addr)
            new_c = 1 if (operand & 0x01) else 0
            result = ((self.regs.c << 7) & 0x80) | (operand >> 1)
            self.regs.c = new_c
            self.write(addr, result & 0xFF)
            self.regs.update_flag_z(result)
            self.regs.update_flag_n(result)
            return 0

    def STX(self, addr_mode_func):
        """Instrução STX: Store X Register (Armazena Registrador X na memória)."""
        addr, _ = addr_mode_func()
        self.write(addr, self.regs.x)
        return 0

    def STY(self, addr_mode_func):
        """Instrução STY: Store Y Register (Armazena Registrador Y na memória)."""
        addr, _ = addr_mode_func()
        self.write(addr, self.regs.y)
        return 0

    # --- Instruções de Incremento e Decremento ---
    def INC(self, addr_mode_func):
        """Instrução INC: Increment Memory (Incrementa valor na memória)."""
        addr, _ = addr_mode_func()
        value = (self.read(addr) + 1) & 0xFF
        self.write(addr, value)
        self.regs.update_flag_z(value)
        self.regs.update_flag_n(value)
        return 0

    def DEC(self, addr_mode_func):
        """Instrução DEC: Decrement Memory (Decrementa valor na memória)."""
        addr, _ = addr_mode_func()
        value = (self.read(addr) - 1) & 0xFF
        self.write(addr, value)
        self.regs.update_flag_z(value)
        self.regs.update_flag_n(value)
        return 0

    def INX(self, addr_mode_func):
        """Instrução INX: Increment X Register."""
        self.regs.x = (self.regs.x + 1) & 0xFF
        self.regs.update_flag_z(self.regs.x)
        self.regs.update_flag_n(self.regs.x)
        return 0

    def INY(self, addr_mode_func):
        """Instrução INY: Increment Y Register."""
        self.regs.y = (self.regs.y + 1) & 0xFF
        self.regs.update_flag_z(self.regs.y)
        self.regs.update_flag_n(self.regs.y)
        return 0

    def DEX(self, addr_mode_func):
        """Instrução DEX: Decrement X Register."""
        self.regs.x = (self.regs.x - 1) & 0xFF
        self.regs.update_flag_z(self.regs.x)
        self.regs.update_flag_n(self.regs.x)
        return 0

    def DEY(self, addr_mode_func):
        """Instrução DEY: Decrement Y Register."""
        self.regs.y = (self.regs.y - 1) & 0xFF
        self.regs.update_flag_z(self.regs.y)
        self.regs.update_flag_n(self.regs.y)
        return 0

    # --- Instruções de Pilha ---
    def PHA(self, addr_mode_func):
        """Instrução PHA: Push Accumulator (Empilha Acumulador)."""
        self.push_byte(self.regs.a)
        return 0

    def PLA(self, addr_mode_func):
        """Instrução PLA: Pull Accumulator (Desempilha para Acumulador)."""
        self.regs.a = self.pop_byte()
        self.regs.update_flag_z(self.regs.a)
        self.regs.update_flag_n(self.regs.a)
        return 0

    def PHP(self, addr_mode_func):
        """Instrução PHP: Push Processor Status (Empilha Registrador de Status)."""
        # Flag B é setada para 1 ao empilhar com PHP, flag U também é 1.
        self.push_byte(self.regs.get_status_byte(pushing=True))
        return 0

    def PLP(self, addr_mode_func):
        """Instrução PLP: Pull Processor Status (Desempilha para Registrador de Status)."""
        status = self.pop_byte()
        # Restaura flags do byte, ignorando B e U
        self.regs.set_status_byte(status)
        return 0

    # --- Instruções de Salto e Sub-rotina ---
    def JMP(self, addr_mode_func):
        """Instrução JMP: Jump (Salta para novo endereço)."""
        # O modo de endereçamento (ABS ou IND) calcula o endereço de destino
        addr, _ = addr_mode_func()
        self.regs.pc = addr
        return 0

    # CORREÇÃO: Usando a lógica revisada para JSR
    def JSR(self, addr_mode_func):
        """Instrução JSR: Jump to Subroutine (Salta para sub-rotina)."""
        # 1. Busca o endereço de destino usando a função de modo (ABS).
        #    Isso avança o PC após a instrução JSR (PC agora está na próxima instrução).
        target_addr, _ = addr_mode_func()  # addr_mode_func é self.ABS

        # 2. Calcula o endereço de retorno a ser empilhado. É o endereço do
        #    último byte da instrução JSR (PC - 1).
        return_addr = (self.regs.pc - 1) & 0xFFFF

        # 3. Empilha o endereço de retorno na pilha.
        self.push_word(return_addr)

        # 4. Define o PC para o endereço de destino.
        self.regs.pc = target_addr
        return 0  # JSR ABS sempre consome 6 ciclos, sem ciclos extras.

    # CORREÇÃO: Usando pop_word helper para RTS
    def RTS(self, addr_mode_func):
        """Instrução RTS: Return from Subroutine (Retorna da sub-rotina)."""
        # Pop the address pushed by JSR
        pushed_addr = self.pop_word()  # Pops low then high byte
        # Define o PC para o endereço após a instrução JSR
        self.regs.pc = (pushed_addr + 1) & 0xFFFF
        return 0

    # CORREÇÃO: Usando pop_byte e pop_word helpers para RTI
    def RTI(self, addr_mode_func):
        """Instrução RTI: Return from Interrupt (Retorna da interrupção).

        Restaura o status e o PC da pilha na ordem: status, PC low byte, PC high byte.
        Ajusta o SP para SP + 3 (três bytes desempilhados).
        """
        # Incrementa SP e lê o status
        self.regs.sp = (self.regs.sp + 1) & 0xFF
        status = self.read(0x0100 + self.regs.sp)
        self.regs.set_status_byte(status)

        # Incrementa SP e lê o PC low byte
        self.regs.sp = (self.regs.sp + 1) & 0xFF
        pc_low = self.read(0x0100 + self.regs.sp)

        # Incrementa SP e lê o PC high byte
        self.regs.sp = (self.regs.sp + 1) & 0xFF
        pc_high = self.read(0x0100 + self.regs.sp)

        # Reconstrói o PC completo
        self.regs.pc = (pc_high << 8) | pc_low

        return 0

    # --- Instruções de Branch (Desvio Condicional) ---
    def BCC(self, addr_mode_func):
        """Instrução BCC: Branch if Carry Clear (C=0)."""
        # Obtém o offset relativo
        addr_mode_func()  # Chama o modo de endereçamento para obter o offset

        # Ciclos adicionais se o branch for tomado
        extra_cycles = 0

        # Verifica a condição (Carry Clear)
        if self.regs.c == 0:
            # Calcula o endereço de destino
            # PC já aponta para a próxima instrução após o branch
            old_pc = self.regs.pc
            self.regs.pc = (self.regs.pc + self.addr_rel) & 0xFFFF

            # Adiciona 1 ciclo se o branch for tomado
            extra_cycles = 1

            # Adiciona mais 1 ciclo se o branch cruzar uma página
            if (old_pc & 0xFF00) != (self.regs.pc & 0xFF00):
                extra_cycles += 1

        return extra_cycles

    def BCS(self, addr_mode_func):
        """Instrução BCS: Branch if Carry Set (C=1)."""
        addr_mode_func()

        extra_cycles = 0

        if self.regs.c == 1:
            old_pc = self.regs.pc
            self.regs.pc = (self.regs.pc + self.addr_rel) & 0xFFFF

            extra_cycles = 1

            if (old_pc & 0xFF00) != (self.regs.pc & 0xFF00):
                extra_cycles += 1

        return extra_cycles

    def BEQ(self, addr_mode_func):
        """Instrução BEQ: Branch if Equal (Z=1)."""
        addr_mode_func()

        extra_cycles = 0

        if self.regs.z == 1:
            old_pc = self.regs.pc
            self.regs.pc = (self.regs.pc + self.addr_rel) & 0xFFFF

            extra_cycles = 1

            if (old_pc & 0xFF00) != (self.regs.pc & 0xFF00):
                extra_cycles += 1

        return extra_cycles

    def BMI(self, addr_mode_func):
        """Instrução BMI: Branch if Minus (N=1)."""
        addr_mode_func()

        extra_cycles = 0

        if self.regs.n == 1:
            old_pc = self.regs.pc
            self.regs.pc = (self.regs.pc + self.addr_rel) & 0xFFFF

            extra_cycles = 1

            if (old_pc & 0xFF00) != (self.regs.pc & 0xFF00):
                extra_cycles += 1

        return extra_cycles

    def BNE(self, addr_mode_func):
        """Instrução BNE: Branch if Not Equal (Z=0)."""
        addr_mode_func()

        extra_cycles = 0

        if self.regs.z == 0:
            old_pc = self.regs.pc
            self.regs.pc = (self.regs.pc + self.addr_rel) & 0xFFFF

            extra_cycles = 1

            if (old_pc & 0xFF00) != (self.regs.pc & 0xFF00):
                extra_cycles += 1

        return extra_cycles

    def BPL(self, addr_mode_func):
        """Instrução BPL: Branch if Plus (N=0)."""
        addr_mode_func()

        extra_cycles = 0

        if self.regs.n == 0:
            old_pc = self.regs.pc
            self.regs.pc = (self.regs.pc + self.addr_rel) & 0xFFFF

            extra_cycles = 1

            if (old_pc & 0xFF00) != (self.regs.pc & 0xFF00):
                extra_cycles += 1

        return extra_cycles

    def BVC(self, addr_mode_func):
        """Instrução BVC: Branch if Overflow Clear (V=0)."""
        addr_mode_func()

        extra_cycles = 0

        if self.regs.v == 0:
            old_pc = self.regs.pc
            self.regs.pc = (self.regs.pc + self.addr_rel) & 0xFFFF

            extra_cycles = 1

            if (old_pc & 0xFF00) != (self.regs.pc & 0xFF00):
                extra_cycles += 1

        return extra_cycles

    def BVS(self, addr_mode_func):
        """Instrução BVS: Branch if Overflow Set (V=1)."""
        addr_mode_func()

        extra_cycles = 0

        if self.regs.v == 1:
            old_pc = self.regs.pc
            self.regs.pc = (self.regs.pc + self.addr_rel) & 0xFFFF

            extra_cycles = 1

            if (old_pc & 0xFF00) != (self.regs.pc & 0xFF00):
                extra_cycles += 1

        return extra_cycles

    # --- Instruções de Comparação ---
    def CMP(self, addr_mode_func):
        """Instrução CMP: Compare Accumulator (Compara Acumulador com operando)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)

        # Realiza a comparação (subtração sem afetar o acumulador)
        result = (self.regs.a - operand) & 0xFF

        # Atualiza flags
        self.regs.c = 1 if self.regs.a >= operand else 0  # Carry set se A >= operando
        self.regs.update_flag_z(result)  # Zero set se A == operando
        # Negative set se bit 7 do resultado for 1
        self.regs.update_flag_n(result)

        return 1 if page_crossed else 0

    def CPX(self, addr_mode_func):
        """Instrução CPX: Compare X Register (Compara Registrador X com operando)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)

        # Realiza a comparação (subtração sem afetar o registrador X)
        result = (self.regs.x - operand) & 0xFF

        # Atualiza flags
        self.regs.c = 1 if self.regs.x >= operand else 0  # Carry set se X >= operando
        self.regs.update_flag_z(result)  # Zero set se X == operando
        # Negative set se bit 7 do resultado for 1
        self.regs.update_flag_n(result)

        return 0  # CPX não tem ciclos adicionais por page crossing

    def CPY(self, addr_mode_func):
        """Instrução CPY: Compare Y Register (Compara Registrador Y com operando)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)

        # Realiza a comparação (subtração sem afetar o registrador Y)
        result = (self.regs.y - operand) & 0xFF

        # Atualiza flags
        self.regs.c = 1 if self.regs.y >= operand else 0  # Carry set se Y >= operando
        self.regs.update_flag_z(result)  # Zero set se Y == operando
        # Negative set se bit 7 do resultado for 1
        self.regs.update_flag_n(result)

        return 0  # CPY não tem ciclos adicionais por page crossing

    def BIT(self, addr_mode_func):
        """Instrução BIT: Bit Test (Testa bits entre Acumulador e operando)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)

        # Realiza o teste de bits (AND lógico, mas sem afetar o acumulador)
        result = self.regs.a & operand

        # Atualiza flags
        self.regs.update_flag_z(result)  # Zero set se resultado do AND for 0
        # Bit 7 do operando vai para N
        self.regs.n = 1 if (operand & 0x80) else 0
        # Bit 6 do operando vai para V
        self.regs.v = 1 if (operand & 0x40) else 0

        return 0  # BIT não tem ciclos adicionais por page crossing

    # --- Instruções de Transferência entre Registradores ---
    def TAX(self, addr_mode_func):
        """Instrução TAX: Transfer Accumulator to X."""
        self.regs.x = self.regs.a
        self.regs.update_flag_z(self.regs.x)
        self.regs.update_flag_n(self.regs.x)
        return 0

    def TXA(self, addr_mode_func):
        """Instrução TXA: Transfer X to Accumulator."""
        self.regs.a = self.regs.x
        self.regs.update_flag_z(self.regs.a)
        self.regs.update_flag_n(self.regs.a)
        return 0

    def TAY(self, addr_mode_func):
        """Instrução TAY: Transfer Accumulator to Y."""
        self.regs.y = self.regs.a
        self.regs.update_flag_z(self.regs.y)
        self.regs.update_flag_n(self.regs.y)
        return 0

    def TYA(self, addr_mode_func):
        """Instrução TYA: Transfer Y to Accumulator."""
        self.regs.a = self.regs.y
        self.regs.update_flag_z(self.regs.a)
        self.regs.update_flag_n(self.regs.a)
        return 0

    def TSX(self, addr_mode_func):
        """Instrução TSX: Transfer Stack Pointer to X."""
        self.regs.x = self.regs.sp
        self.regs.update_flag_z(self.regs.x)
        self.regs.update_flag_n(self.regs.x)
        return 0

    def TXS(self, addr_mode_func):
        """Instrução TXS: Transfer X to Stack Pointer."""
        # TXS atualiza o SP, mas não afeta nenhuma flag.
        self.regs.sp = self.regs.x
        return 0

    # --- Instruções de Manipulação de Flags ---
    def CLC(self, addr_mode_func):
        """Instrução CLC: Clear Carry Flag."""
        self.regs.c = 0
        return 0

    def SEC(self, addr_mode_func):
        """Instrução SEC: Set Carry Flag."""
        self.regs.c = 1
        return 0

    def CLI(self, addr_mode_func):
        """Instrução CLI: Clear Interrupt Disable."""
        self.regs.i = 0
        return 0

    def SEI(self, addr_mode_func):
        """Instrução SEI: Set Interrupt Disable."""
        self.regs.i = 1
        return 0

    def CLD(self, addr_mode_func):
        """Instrução CLD: Clear Decimal Mode."""
        self.regs.d = 0
        return 0

    def SED(self, addr_mode_func):
        """Instrução SED: Set Decimal Mode."""
        # Nota: O modo decimal não é funcionalmente implementado em ADC/SBC aqui.
        self.regs.d = 1
        return 0

    def CLV(self, addr_mode_func):
        """Instrução CLV: Clear Overflow Flag."""
        self.regs.v = 0
        return 0

    # --- Outras Instruções ---
    def BRK(self, addr_mode_func):
        """Instrução BRK: Force Interrupt (Software Interrupt)."""
        # BRK se comporta de forma similar a uma IRQ, mas:
        # 1. Empilha PC+2 (o endereço *após* o byte de padding que segue BRK).
        # 2. Seta a flag B para 1 no status empilhado.
        # 3. Usa o vetor de IRQ (FFFE/FF).

        # PC já foi incrementado 1 vez pelo fetch do opcode BRK.
        # O 6502 lê um byte de padding após BRK, que é ignorado.
        # Incrementamos PC para simular a leitura do padding.
        self.regs.pc = (self.regs.pc + 1) & 0xFFFF

        # Seta a flag I para desabilitar outras IRQs durante o handler.
        self.regs.i = 1

        # Empilha PC (PC atual, que aponta para a instrução *após* o padding).
        self.push_word(self.regs.pc)

        # Empilha Status Register (com B=1, U=1).
        # A flag B interna não muda, mas é 1 no valor empilhado.
        self.push_byte(self.regs.get_status_byte(pushing=True))

        # Carrega PC do vetor de IRQ/BRK.
        self.regs.pc = self.bus.read_word(0xFFFE)

        # BRK não retorna ciclos adicionais; os 7 ciclos base já cobrem tudo.
        return 0

    def NOP(self, addr_mode_func):
        """Instrução NOP: No Operation."""
        # NOPs oficiais (como $EA) não fazem nada e não têm ciclos extras.
        # NOPs não oficiais podem ter modos de endereçamento que causam ciclos extras.
        return 0

    def XXX(self, addr_mode_func):
        """Instrução ilegal ou não implementada."""
        # Use 16-bit wraparound for PC-1 to avoid negative printing like -001
        pc_addr = (self.regs.pc - 1) & 0xFFFF
        # Gather a small memory/context dump to help debugging why an illegal opcode occurred
        try:
            surrounding = []
            for offs in range(-4, 5):
                addr = (pc_addr + offs) & 0xFFFF
                try:
                    b = self.bus.read(addr)
                except Exception:
                    b = None
                surrounding.append((addr, b))
        except Exception:
            surrounding = []

        try:
            # Sample a few stack bytes (if accessible)
            sp = self.regs.sp & 0xFF
            stack_samples = []
            for i in range(0, 6):
                try:
                    val = self.bus.read(0x0100 + ((sp + i) & 0xFF))
                except Exception:
                    val = None
                stack_samples.append(val)
        except Exception:
            stack_samples = []

        try:
            logging.error(
                "Opcode ILEGAL/NÃO IMPLEMENTADO encontrado: %02X no endereço %04X",
                self.opcode, pc_addr)
            logging.error("Regs: A=%02X X=%02X Y=%02X SP=%02X FLAGS=[N=%d V=%d B=%d D=%d I=%d Z=%d C=%d]",
                          self.regs.a & 0xFF, self.regs.x & 0xFF, self.regs.y & 0xFF, self.regs.sp & 0xFF,
                          int(bool(self.regs.n)), int(bool(self.regs.v)), int(
                              bool(self.regs.b)), int(bool(self.regs.d)),
                          int(bool(self.regs.i)), int(bool(self.regs.z)), int(bool(self.regs.c)))
            # Surrounding memory
            mem_items = []
            for (addr, b) in surrounding:
                if isinstance(b, int):
                    mem_items.append(f"{addr:04X}:{b:02X}")
                else:
                    mem_items.append(f"{addr:04X}:..")
            mem_str = ' '.join(mem_items)
            logging.error("Memory around PC: %s", mem_str)
            stack_items = [(f"{v:02X}" if isinstance(v, int) else '..')
                           for v in stack_samples]
            logging.error("Stack[@SP..]: %s", ' '.join(stack_items))
        except Exception:
            pass
        return 0

    # --- Função Principal de Execução ---
    def clock(self):
        """Executa um ciclo da CPU.

        Retorna:
            int: Número de ciclos consumidos pela instrução.
        """
        # Se a CPU estiver parada, não faz nada
        if self.halted:
            return 0

        # Busca o opcode
        self.opcode = self.fetch_byte()

        # Decodifica o opcode usando a tabela de lookup
        instr_func, addr_mode_func, cycles = self.lookup[self.opcode]

        # Anota o PC do opcode atual no barramento (útil para logging de writes)
        try:
            # PC atual após fetch aponta para o próximo byte, então o opcode está em PC-1
            if hasattr(self.bus, '_last_instr_pc'):
                self.bus._last_instr_pc = (self.regs.pc - 1) & 0xFFFF
            else:
                # cria o atributo para que o Bus possa consultá-lo se desejar
                self.bus._last_instr_pc = (self.regs.pc - 1) & 0xFFFF
        except Exception:
            pass

        # Executa a instrução e obtém ciclos adicionais
        extra_cycles = instr_func(addr_mode_func)

        # Atualiza o contador de ciclos
        total_cycles = cycles + extra_cycles
        self.cycles = total_cycles
        self.total_cycles += total_cycles
        # Se houver um PPU instalado no barramento, avance-o (3 PPU clocks por CPU cycle)
        try:
            ppu = getattr(self.bus, 'ppu', None)
            if ppu and hasattr(ppu, 'step'):
                try:
                    ppu_clocks = total_cycles * 3
                    try:
                        if getattr(self, 'verbose', False):
                            if not hasattr(self, '_ppu_step_log_count'):
                                self._ppu_step_log_count = 0
                            self._ppu_step_log_count += 1
                            if self._ppu_step_log_count <= 50:
                                last_pc = getattr(
                                    self.bus, '_last_instr_pc', None)
                                try:
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    if last_pc is None:
                                        logger.debug(
                                            f"CPU: stepping PPU: cpu_cycles={total_cycles} -> ppu_clocks={ppu_clocks}")
                                    else:
                                        logger.debug(
                                            f"CPU: stepping PPU: cpu_cycles={total_cycles} -> ppu_clocks={ppu_clocks} (instr @ ${last_pc:04X})")
                                except Exception:
                                    pass
                            elif self._ppu_step_log_count == 51:
                                try:
                                    import logging
                                    logging.getLogger(__name__).debug(
                                        "CPU: further PPU.step logs suppressed")
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    ppu.step(ppu_clocks)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if not hasattr(self, '_instr_debug_count'):
                self._instr_debug_count = 0
            self._instr_debug_count += 1
            if self._instr_debug_count % 500 == 0:
                if getattr(self, 'verbose', False):
                    ppu = getattr(self.bus, 'ppu', None)
                    if ppu is not None:
                        try:
                            scan = getattr(ppu, 'scanline', None)
                            ppu_cycle = getattr(ppu, 'ppu_cycle', None)
                            frame = getattr(ppu, 'frame', None)
                            try:
                                import logging
                                logging.getLogger(__name__).debug(
                                    f"CPU-debug: instr#{self._instr_debug_count} -> PPU scanline={scan}, ppu_cycle={ppu_cycle}, frame={frame}")
                            except Exception:
                                pass
                        except Exception:
                            pass
        except Exception:
            pass

        return total_cycles

    def reset(self):
        """Reseta a CPU para o estado inicial.

        Isso simula o sinal de RESET do hardware:
        1. Carrega PC do vetor de reset (FFFC/D)
        2. Reseta registradores e flags para valores padrão
        3. Desativa o modo decimal
        4. Ativa a flag de interrupção
        """
        # Reseta registradores
        self.regs = Registers()

        # Carrega PC do vetor de reset
        self.regs.pc = self.bus.read_word(0xFFFC)

        # Reseta contadores de ciclos
        self.cycles = 0
        self.total_cycles = 0

        # Desativa o modo halt
        self.halted = False

        # Reseta variáveis internas
        self.addr_rel = 0
        self.addr_abs = 0
        self.opcode = 0

        # O reset leva 8 ciclos
        return 8

    def irq(self):
        """Processa uma Interrupção (IRQ).

        Se a flag I (Interrupt Disable) estiver setada, a interrupção é ignorada.
        Caso contrário, empilha PC e status, e carrega PC do vetor de IRQ.
        """
        # Se a flag I estiver setada, ignora a interrupção
        if self.regs.i == 1:
            return 0

        # Empilha PC
        self.push_word(self.regs.pc)

        # Empilha status (com B=0, U=1)
        # A flag B é 0 no valor empilhado para IRQ/NMI (diferente de BRK)
        self.regs.b = 0
        self.push_byte(self.regs.get_status_byte(pushing=True))

        # Seta a flag I para evitar interrupções aninhadas
        self.regs.i = 1

        # Carrega PC do vetor de IRQ
        self.regs.pc = self.bus.read_word(0xFFFE)

        # IRQ leva 7 ciclos
        return 7

    def nmi(self):
        """Processa uma Interrupção Não-Mascarável (NMI).

        NMI não pode ser desabilitada pela flag I.
        Empilha PC e status, e carrega PC do vetor de NMI.
        """
        # Empilha PC
        self.push_word(self.regs.pc)

        # Empilha status (com B=0, U=1)
        # A flag B é 0 no valor empilhado para IRQ/NMI (diferente de BRK)
        self.regs.b = 0
        self.push_byte(self.regs.get_status_byte(pushing=True))

        # Seta a flag I para evitar interrupções durante o handler de NMI
        self.regs.i = 1

        # Carrega PC do vetor de NMI
        self.regs.pc = self.bus.read_word(0xFFFA)

        # NMI leva 8 ciclos
        return 8
