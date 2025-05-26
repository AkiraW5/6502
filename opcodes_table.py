# -*- coding: utf-8 -*-
"""
Tabela de opcodes para o processador MOS 6502.

Este módulo define a tabela completa de opcodes do 6502, mapeando cada combinação
de instrução e modo de endereçamento para o opcode correspondente.
"""

# Modos de endereçamento
class AddressingMode:
    IMPLICIT = 0       # Implícito/Inerente (sem operando)
    ACCUMULATOR = 1    # Acumulador (ex: ASL A)
    IMMEDIATE = 2      # Imediato (ex: LDA #$10)
    ABSOLUTE = 3       # Absoluto (ex: JMP $1234)
    ABSOLUTE_X = 4     # Absoluto,X (ex: LDA $1234,X)
    ABSOLUTE_Y = 5     # Absoluto,Y (ex: LDA $1234,Y)
    ZEROPAGE = 6       # Zeropage (ex: LDA $12)
    ZEROPAGE_X = 7     # Zeropage,X (ex: LDA $12,X)
    ZEROPAGE_Y = 8     # Zeropage,Y (ex: LDX $12,Y)
    INDIRECT = 9       # Indireto (ex: JMP ($1234))
    INDIRECT_X = 10    # Indireto,X (ex: LDA ($12,X))
    INDIRECT_Y = 11    # Indireto,Y (ex: LDA ($12),Y)
    RELATIVE = 12      # Relativo (ex: BNE $10)

# Tabela de opcodes do 6502
# Formato: {instrução: {modo_endereçamento: (opcode, tamanho_bytes)}}
OPCODE_TABLE = {
    # Transferência de Dados
    "LDA": {
        AddressingMode.IMMEDIATE: (0xA9, 2),
        AddressingMode.ABSOLUTE: (0xAD, 3),
        AddressingMode.ABSOLUTE_X: (0xBD, 3),
        AddressingMode.ABSOLUTE_Y: (0xB9, 3),
        AddressingMode.ZEROPAGE: (0xA5, 2),
        AddressingMode.ZEROPAGE_X: (0xB5, 2),
        AddressingMode.INDIRECT_X: (0xA1, 2),
        AddressingMode.INDIRECT_Y: (0xB1, 2),
    },
    "LDX": {
        AddressingMode.IMMEDIATE: (0xA2, 2),
        AddressingMode.ABSOLUTE: (0xAE, 3),
        AddressingMode.ABSOLUTE_Y: (0xBE, 3),
        AddressingMode.ZEROPAGE: (0xA6, 2),
        AddressingMode.ZEROPAGE_Y: (0xB6, 2),
    },
    "LDY": {
        AddressingMode.IMMEDIATE: (0xA0, 2),
        AddressingMode.ABSOLUTE: (0xAC, 3),
        AddressingMode.ABSOLUTE_X: (0xBC, 3),
        AddressingMode.ZEROPAGE: (0xA4, 2),
        AddressingMode.ZEROPAGE_X: (0xB4, 2),
    },
    "STA": {
        AddressingMode.ABSOLUTE: (0x8D, 3),
        AddressingMode.ABSOLUTE_X: (0x9D, 3),
        AddressingMode.ABSOLUTE_Y: (0x99, 3),
        AddressingMode.ZEROPAGE: (0x85, 2),
        AddressingMode.ZEROPAGE_X: (0x95, 2),
        AddressingMode.INDIRECT_X: (0x81, 2),
        AddressingMode.INDIRECT_Y: (0x91, 2),
    },
    "STX": {
        AddressingMode.ABSOLUTE: (0x8E, 3),
        AddressingMode.ZEROPAGE: (0x86, 2),
        AddressingMode.ZEROPAGE_Y: (0x96, 2),
    },
    "STY": {
        AddressingMode.ABSOLUTE: (0x8C, 3),
        AddressingMode.ZEROPAGE: (0x84, 2),
        AddressingMode.ZEROPAGE_X: (0x94, 2),
    },
    "TAX": {
        AddressingMode.IMPLICIT: (0xAA, 1),
    },
    "TAY": {
        AddressingMode.IMPLICIT: (0xA8, 1),
    },
    "TXA": {
        AddressingMode.IMPLICIT: (0x8A, 1),
    },
    "TYA": {
        AddressingMode.IMPLICIT: (0x98, 1),
    },
    "TSX": {
        AddressingMode.IMPLICIT: (0xBA, 1),
    },
    "TXS": {
        AddressingMode.IMPLICIT: (0x9A, 1),
    },
    
    # Aritméticas
    "ADC": {
        AddressingMode.IMMEDIATE: (0x69, 2),
        AddressingMode.ABSOLUTE: (0x6D, 3),
        AddressingMode.ABSOLUTE_X: (0x7D, 3),
        AddressingMode.ABSOLUTE_Y: (0x79, 3),
        AddressingMode.ZEROPAGE: (0x65, 2),
        AddressingMode.ZEROPAGE_X: (0x75, 2),
        AddressingMode.INDIRECT_X: (0x61, 2),
        AddressingMode.INDIRECT_Y: (0x71, 2),
    },
    "SBC": {
        AddressingMode.IMMEDIATE: (0xE9, 2),
        AddressingMode.ABSOLUTE: (0xED, 3),
        AddressingMode.ABSOLUTE_X: (0xFD, 3),
        AddressingMode.ABSOLUTE_Y: (0xF9, 3),
        AddressingMode.ZEROPAGE: (0xE5, 2),
        AddressingMode.ZEROPAGE_X: (0xF5, 2),
        AddressingMode.INDIRECT_X: (0xE1, 2),
        AddressingMode.INDIRECT_Y: (0xF1, 2),
    },
    "INC": {
        AddressingMode.ABSOLUTE: (0xEE, 3),
        AddressingMode.ABSOLUTE_X: (0xFE, 3),
        AddressingMode.ZEROPAGE: (0xE6, 2),
        AddressingMode.ZEROPAGE_X: (0xF6, 2),
    },
    "INX": {
        AddressingMode.IMPLICIT: (0xE8, 1),
    },
    "INY": {
        AddressingMode.IMPLICIT: (0xC8, 1),
    },
    "DEC": {
        AddressingMode.ABSOLUTE: (0xCE, 3),
        AddressingMode.ABSOLUTE_X: (0xDE, 3),
        AddressingMode.ZEROPAGE: (0xC6, 2),
        AddressingMode.ZEROPAGE_X: (0xD6, 2),
    },
    "DEX": {
        AddressingMode.IMPLICIT: (0xCA, 1),
    },
    "DEY": {
        AddressingMode.IMPLICIT: (0x88, 1),
    },
    
    # Lógicas
    "AND": {
        AddressingMode.IMMEDIATE: (0x29, 2),
        AddressingMode.ABSOLUTE: (0x2D, 3),
        AddressingMode.ABSOLUTE_X: (0x3D, 3),
        AddressingMode.ABSOLUTE_Y: (0x39, 3),
        AddressingMode.ZEROPAGE: (0x25, 2),
        AddressingMode.ZEROPAGE_X: (0x35, 2),
        AddressingMode.INDIRECT_X: (0x21, 2),
        AddressingMode.INDIRECT_Y: (0x31, 2),
    },
    "ORA": {
        AddressingMode.IMMEDIATE: (0x09, 2),
        AddressingMode.ABSOLUTE: (0x0D, 3),
        AddressingMode.ABSOLUTE_X: (0x1D, 3),
        AddressingMode.ABSOLUTE_Y: (0x19, 3),
        AddressingMode.ZEROPAGE: (0x05, 2),
        AddressingMode.ZEROPAGE_X: (0x15, 2),
        AddressingMode.INDIRECT_X: (0x01, 2),
        AddressingMode.INDIRECT_Y: (0x11, 2),
    },
    "EOR": {
        AddressingMode.IMMEDIATE: (0x49, 2),
        AddressingMode.ABSOLUTE: (0x4D, 3),
        AddressingMode.ABSOLUTE_X: (0x5D, 3),
        AddressingMode.ABSOLUTE_Y: (0x59, 3),
        AddressingMode.ZEROPAGE: (0x45, 2),
        AddressingMode.ZEROPAGE_X: (0x55, 2),
        AddressingMode.INDIRECT_X: (0x41, 2),
        AddressingMode.INDIRECT_Y: (0x51, 2),
    },
    "ASL": {
        AddressingMode.ACCUMULATOR: (0x0A, 1),
        AddressingMode.ABSOLUTE: (0x0E, 3),
        AddressingMode.ABSOLUTE_X: (0x1E, 3),
        AddressingMode.ZEROPAGE: (0x06, 2),
        AddressingMode.ZEROPAGE_X: (0x16, 2),
    },
    "LSR": {
        AddressingMode.ACCUMULATOR: (0x4A, 1),
        AddressingMode.ABSOLUTE: (0x4E, 3),
        AddressingMode.ABSOLUTE_X: (0x5E, 3),
        AddressingMode.ZEROPAGE: (0x46, 2),
        AddressingMode.ZEROPAGE_X: (0x56, 2),
    },
    "ROL": {
        AddressingMode.ACCUMULATOR: (0x2A, 1),
        AddressingMode.ABSOLUTE: (0x2E, 3),
        AddressingMode.ABSOLUTE_X: (0x3E, 3),
        AddressingMode.ZEROPAGE: (0x26, 2),
        AddressingMode.ZEROPAGE_X: (0x36, 2),
    },
    "ROR": {
        AddressingMode.ACCUMULATOR: (0x6A, 1),
        AddressingMode.ABSOLUTE: (0x6E, 3),
        AddressingMode.ABSOLUTE_X: (0x7E, 3),
        AddressingMode.ZEROPAGE: (0x66, 2),
        AddressingMode.ZEROPAGE_X: (0x76, 2),
    },
    
    # Comparações e Testes
    "CMP": {
        AddressingMode.IMMEDIATE: (0xC9, 2),
        AddressingMode.ABSOLUTE: (0xCD, 3),
        AddressingMode.ABSOLUTE_X: (0xDD, 3),
        AddressingMode.ABSOLUTE_Y: (0xD9, 3),
        AddressingMode.ZEROPAGE: (0xC5, 2),
        AddressingMode.ZEROPAGE_X: (0xD5, 2),
        AddressingMode.INDIRECT_X: (0xC1, 2),
        AddressingMode.INDIRECT_Y: (0xD1, 2),
    },
    "CPX": {
        AddressingMode.IMMEDIATE: (0xE0, 2),
        AddressingMode.ABSOLUTE: (0xEC, 3),
        AddressingMode.ZEROPAGE: (0xE4, 2),
    },
    "CPY": {
        AddressingMode.IMMEDIATE: (0xC0, 2),
        AddressingMode.ABSOLUTE: (0xCC, 3),
        AddressingMode.ZEROPAGE: (0xC4, 2),
    },
    "BIT": {
        AddressingMode.ABSOLUTE: (0x2C, 3),
        AddressingMode.ZEROPAGE: (0x24, 2),
    },
    
    # Desvios Condicionais
    "BCC": {
        AddressingMode.RELATIVE: (0x90, 2),
    },
    "BCS": {
        AddressingMode.RELATIVE: (0xB0, 2),
    },
    "BEQ": {
        AddressingMode.RELATIVE: (0xF0, 2),
    },
    "BNE": {
        AddressingMode.RELATIVE: (0xD0, 2),
    },
    "BMI": {
        AddressingMode.RELATIVE: (0x30, 2),
    },
    "BPL": {
        AddressingMode.RELATIVE: (0x10, 2),
    },
    "BVC": {
        AddressingMode.RELATIVE: (0x50, 2),
    },
    "BVS": {
        AddressingMode.RELATIVE: (0x70, 2),
    },
    
    # Desvios e Chamadas
    "JMP": {
        AddressingMode.ABSOLUTE: (0x4C, 3),
        AddressingMode.INDIRECT: (0x6C, 3),
    },
    "JSR": {
        AddressingMode.ABSOLUTE: (0x20, 3),
    },
    "RTS": {
        AddressingMode.IMPLICIT: (0x60, 1),
    },
    
    # Manipulação de Flags
    "CLC": {
        AddressingMode.IMPLICIT: (0x18, 1),
    },
    "SEC": {
        AddressingMode.IMPLICIT: (0x38, 1),
    },
    "CLD": {
        AddressingMode.IMPLICIT: (0xD8, 1),
    },
    "SED": {
        AddressingMode.IMPLICIT: (0xF8, 1),
    },
    "CLI": {
        AddressingMode.IMPLICIT: (0x58, 1),
    },
    "SEI": {
        AddressingMode.IMPLICIT: (0x78, 1),
    },
    "CLV": {
        AddressingMode.IMPLICIT: (0xB8, 1),
    },
    
    # Pilha
    "PHA": {
        AddressingMode.IMPLICIT: (0x48, 1),
    },
    "PLA": {
        AddressingMode.IMPLICIT: (0x68, 1),
    },
    "PHP": {
        AddressingMode.IMPLICIT: (0x08, 1),
    },
    "PLP": {
        AddressingMode.IMPLICIT: (0x28, 1),
    },
    
    # Outras
    "BRK": {
        AddressingMode.IMPLICIT: (0x00, 1),
    },
    "NOP": {
        AddressingMode.IMPLICIT: (0xEA, 1),
    },
    "RTI": {
        AddressingMode.IMPLICIT: (0x40, 1),
    },
}

# Função para obter o opcode e tamanho de uma instrução
def get_opcode_info(instruction, addressing_mode):
    """
    Obtém o opcode e tamanho em bytes de uma instrução com o modo de endereçamento especificado.
    
    Args:
        instruction: Nome da instrução (ex: "LDA")
        addressing_mode: Modo de endereçamento (ex: AddressingMode.IMMEDIATE)
        
    Returns:
        Tupla (opcode, tamanho_bytes) ou None se a combinação não for válida
    """
    if instruction in OPCODE_TABLE and addressing_mode in OPCODE_TABLE[instruction]:
        return OPCODE_TABLE[instruction][addressing_mode]
    return None

# Função para verificar se uma instrução suporta um modo de endereçamento
def is_valid_addressing_mode(instruction, addressing_mode):
    """
    Verifica se uma instrução suporta o modo de endereçamento especificado.
    
    Args:
        instruction: Nome da instrução (ex: "LDA")
        addressing_mode: Modo de endereçamento (ex: AddressingMode.IMMEDIATE)
        
    Returns:
        True se a combinação for válida, False caso contrário
    """
    return instruction in OPCODE_TABLE and addressing_mode in OPCODE_TABLE[instruction]

# Função para obter todos os modos de endereçamento suportados por uma instrução
def get_supported_addressing_modes(instruction):
    """
    Obtém todos os modos de endereçamento suportados por uma instrução.
    
    Args:
        instruction: Nome da instrução (ex: "LDA")
        
    Returns:
        Lista de modos de endereçamento suportados ou lista vazia se a instrução não existir
    """
    if instruction in OPCODE_TABLE:
        return list(OPCODE_TABLE[instruction].keys())
    return []
