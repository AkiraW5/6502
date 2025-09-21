# -*- coding: utf-8 -*-
"""
Implementação da integração da tabela de opcodes com o assembler 6502.

Este módulo adiciona funções para detectar modos de endereçamento e gerar código de máquina
para todas as instruções do 6502 suportadas.
"""

from .opcodes_table import OPCODE_TABLE, AddressingMode, get_opcode_info, is_valid_addressing_mode, get_supported_addressing_modes


class AddressingModeDetector:
    """
    Classe responsável por detectar o modo de endereçamento de uma instrução
    com base no operando fornecido.
    """

    @staticmethod
    def detect_addressing_mode(operand: str) -> int:
        """
        Detecta o modo de endereçamento com base no formato do operando.

        Args:
            operand: String representando o operando da instrução

        Returns:
            Constante AddressingMode representando o modo de endereçamento
        """
        operand = operand.strip()

        # Modo implícito (sem operando)
        if not operand:
            return AddressingMode.IMPLICIT

        # Modo acumulador (A)
        if operand.upper() == 'A':
            return AddressingMode.ACCUMULATOR

        # Modo imediato (#$xx ou #xx)
        if operand.startswith('#'):
            return AddressingMode.IMMEDIATE

        # Detecta formas indiretas primeiro para não confundir com modos indexados simples
        # Formas esperadas:
        #   (addr,X)    -> INDIRECT_X
        #   (addr),Y    -> INDIRECT_Y
        #   (addr)      -> INDIRECT
        import re
        # (addr,X)  e (symbol,X)
        if re.match(r'^\s*\(\s*[^\)]+\s*,\s*X\s*\)\s*$', operand, re.IGNORECASE):
            return AddressingMode.INDIRECT_X
        # (addr),Y  e (symbol),Y
        if re.match(r'^\s*\(\s*[^\)]+\s*\)\s*,\s*Y\s*$', operand, re.IGNORECASE):
            return AddressingMode.INDIRECT_Y
        # (addr) or (symbol)
        if re.match(r'^\s*\(\s*[^\)]+\s*\)\s*$', operand):
            return AddressingMode.INDIRECT

        # Modos indexados
        if ',X' in operand.upper():
            # Determinar se é zeropage ou absoluto com base no valor
            value = operand.split(',')[0].strip()
            if value.startswith('$'):
                if len(value) <= 3:  # $xx (zeropage)
                    return AddressingMode.ZEROPAGE_X
                else:  # $xxxx (absoluto)
                    return AddressingMode.ABSOLUTE_X
            else:  # Assumir zeropage para valores decimais pequenos
                try:
                    num = int(value)
                    if num < 256:
                        return AddressingMode.ZEROPAGE_X
                    else:
                        return AddressingMode.ABSOLUTE_X
                except ValueError:
                    # Se não for um número, assumir absoluto
                    return AddressingMode.ABSOLUTE_X

        if ',Y' in operand.upper():
            # Determinar se é zeropage ou absoluto com base no valor
            value = operand.split(',')[0].strip()
            if value.startswith('$'):
                if len(value) <= 3:  # $xx (zeropage)
                    return AddressingMode.ZEROPAGE_Y
                else:  # $xxxx (absoluto)
                    return AddressingMode.ABSOLUTE_Y
            else:  # Assumir zeropage para valores decimais pequenos
                try:
                    num = int(value)
                    if num < 256:
                        return AddressingMode.ZEROPAGE_Y
                    else:
                        return AddressingMode.ABSOLUTE_Y
                except ValueError:
                    # Se não for um número, assumir absoluto
                    return AddressingMode.ABSOLUTE_Y

        # Modos não indexados (zeropage ou absoluto)
        if operand.startswith('$'):
            if len(operand) <= 3:  # $xx (zeropage)
                return AddressingMode.ZEROPAGE
            else:  # $xxxx (absoluto)
                return AddressingMode.ABSOLUTE

        # Para instruções de desvio condicional, assumir relativo
        # Isso será determinado pelo contexto da instrução

        # Para outros casos, assumir absoluto (símbolos, etc.)
        return AddressingMode.ABSOLUTE

    @staticmethod
    def is_branch_instruction(instruction: str) -> bool:
        """
        Verifica se a instrução é um desvio condicional.

        Args:
            instruction: Nome da instrução

        Returns:
            True se for um desvio condicional, False caso contrário
        """
        branch_instructions = {'BCC', 'BCS', 'BEQ',
                               'BNE', 'BMI', 'BPL', 'BVC', 'BVS'}
        return instruction.upper() in branch_instructions

    @staticmethod
    def parse_operand_value(operand: str, symbol_table=None) -> int:
        """
        Converte o operando em um valor numérico.

        Args:
            operand: String representando o operando
            symbol_table: Tabela de símbolos para resolver referências

        Returns:
            Valor numérico do operando
        """
        # Remover caracteres especiais para modos específicos
        operand = operand.strip()

        # Modo imediato
        if operand.startswith('#'):
            operand = operand[1:]

        # Modos indiretos
        if operand.startswith('(') and operand.endswith(')'):
            operand = operand[1:-1]

        # Modos indexados
        if ',X' in operand.upper():
            operand = operand.split(',')[0].strip()
        elif ',Y' in operand.upper():
            operand = operand.split(',')[0].strip()

        # Converter para valor numérico
        if operand.startswith('$'):  # Hexadecimal
            return int(operand[1:], 16)
        elif operand.startswith('%'):  # Binário
            return int(operand[1:], 2)
        else:
            try:
                return int(operand)  # Decimal
            except ValueError:
                # Tentar resolver como símbolo
                if symbol_table and operand in symbol_table:
                    return symbol_table[operand]
                return 0  # Valor padrão se não puder resolver

    @staticmethod
    def generate_machine_code(instruction: str, operand: str, current_address: int, symbol_table=None) -> bytes:
        """
        Gera o código de máquina para uma instrução.

        Args:
            instruction: Nome da instrução
            operand: Operando da instrução
            current_address: Endereço atual do contador de programa
            symbol_table: Tabela de símbolos para resolver referências

        Returns:
            Bytes representando o código de máquina da instrução
        """
        # Detectar o modo de endereçamento
        addressing_mode = AddressingModeDetector.detect_addressing_mode(
            operand)

        # Ajustar para instruções de desvio
        if AddressingModeDetector.is_branch_instruction(instruction):
            addressing_mode = AddressingMode.RELATIVE

        # Verificar se a instrução suporta o modo de endereçamento
        if not is_valid_addressing_mode(instruction.upper(), addressing_mode):
            supported_modes = get_supported_addressing_modes(
                instruction.upper())
            raise ValueError(
                f"Instrução {instruction} não suporta o modo de endereçamento {addressing_mode}. Modos suportados: {supported_modes}")

        # Obter o opcode e tamanho
        opcode_info = get_opcode_info(instruction.upper(), addressing_mode)
        if not opcode_info:
            raise ValueError(
                f"Combinação inválida de instrução e modo de endereçamento: {instruction} com modo {addressing_mode}")

        opcode, size = opcode_info

        # Gerar o código de máquina
        machine_code = bytearray([opcode])

        # Adicionar operando se necessário
        if size > 1:
            value = AddressingModeDetector.parse_operand_value(
                operand, symbol_table)

            if addressing_mode == AddressingMode.RELATIVE:
                # Calcular o deslocamento relativo
                target_address = value
                # +2 porque o PC já avançou após a instrução
                offset = target_address - (current_address + 2)

                # Verificar se o deslocamento está dentro do intervalo válido (-128 a 127)
                if offset < -128 or offset > 127:
                    raise ValueError(
                        f"Deslocamento relativo fora do intervalo válido: {offset}")

                # Converter para byte com sinal
                if offset < 0:
                    offset = 256 + offset  # Representação de complemento de 2

                machine_code.append(offset & 0xFF)
            elif size == 2:
                # Operando de 1 byte
                machine_code.append(value & 0xFF)
            elif size == 3:
                # Operando de 2 bytes (little-endian)
                machine_code.append(value & 0xFF)
                machine_code.append((value >> 8) & 0xFF)

        return bytes(machine_code)
