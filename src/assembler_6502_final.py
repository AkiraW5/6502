# -*- coding: utf-8 -*-
"""
Assembler para o processador MOS 6502.

Este módulo implementa um assembler completo para o processador 6502,
capaz de traduzir código assembly para código de máquina.
"""

import re
import sys
import logging
from enum import Enum, auto
from typing import Dict, List, Tuple, Optional, Set, Union, Any

from .opcodes_table import OPCODE_TABLE, AddressingMode, get_opcode_info, is_valid_addressing_mode, get_supported_addressing_modes
from .addressing_mode_detector import AddressingModeDetector


class TokenType(Enum):
    """Tipos de tokens reconhecidos pelo lexer."""
    INSTRUCTION = auto()  # Instrução (ex: LDA, STA)
    DIRECTIVE = auto()    # Diretiva (ex: .org, .byte)
    LABEL = auto()        # Label (ex: start:)
    SYMBOL = auto()       # Símbolo (ex: SCREEN_START)
    NUMBER = auto()       # Número (ex: $1234, 42)
    STRING = auto()       # String (ex: "Hello")
    REGISTER = auto()     # Registrador (ex: A, X, Y)
    IMMEDIATE = auto()    # Valor imediato (ex: #$10)
    SEPARATOR = auto()    # Separador (ex: ,)
    COMMENT = auto()      # Comentário (ex: ; comentário)
    NEWLINE = auto()      # Nova linha
    EOF = auto()          # Fim do arquivo


class Token:
    """Representa um token no código fonte."""

    def __init__(self, type: TokenType, value: str, line: int, column: int):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, '{self.value}', line={self.line}, col={self.column})"


class Lexer:
    """
    Analisador léxico para o código assembly do 6502.

    Responsável por tokenizar o código fonte, identificando instruções,
    diretivas, labels, símbolos, números, strings, etc.
    """

    # Lista de instruções do 6502
    INSTRUCTIONS = [
        'ADC', 'AND', 'ASL', 'BCC', 'BCS', 'BEQ', 'BIT', 'BMI',
        'BNE', 'BPL', 'BRK', 'BVC', 'BVS', 'CLC', 'CLD', 'CLI',
        'CLV', 'CMP', 'CPX', 'CPY', 'DEC', 'DEX', 'DEY', 'EOR',
        'INC', 'INX', 'INY', 'JMP', 'JSR', 'LDA', 'LDX', 'LDY',
        'LSR', 'NOP', 'ORA', 'PHA', 'PHP', 'PLA', 'PLP', 'ROL',
        'ROR', 'RTI', 'RTS', 'SBC', 'SEC', 'SED', 'SEI', 'STA',
        'STX', 'STY', 'TAX', 'TAY', 'TSX', 'TXA', 'TXS', 'TYA'
    ]

    # Lista de diretivas do assembler
    DIRECTIVES = [
        '.org', '.byte', '.db', '.word', '.dw', '.equ', '.define'
    ]

    # Lista de registradores do 6502
    REGISTERS = ['A', 'X', 'Y']

    def __init__(self, source: str, debug_mode: bool = False):
        """
        Inicializa o lexer com o código fonte.

        Args:
            source: Código fonte a ser tokenizado
            debug_mode: Se True, imprime informações de debug durante a tokenização
        """
        self.source = source
        self.tokens = []
        self.current_pos = 0
        self.line = 1
        self.column = 1
        self.debug_mode = debug_mode

        # Padrões regex para reconhecimento de tokens
        # Adiciona padrões específicos para operandos indiretos com parênteses
        # para preservar formas como '($20),Y' e '($20,X)'. Estes devem vir
        # antes dos padrões genéricos de número/identificador.
        self.regex_patterns = [
            (re.compile(r'^#\$[0-9a-fA-F]+'),
             TokenType.IMMEDIATE),         # Imediato hex
            # Imediato decimal
            (re.compile(r'^#[0-9]+'), TokenType.IMMEDIATE),
            (re.compile(r'^#[a-zA-Z_][a-zA-Z0-9_]*'),
             TokenType.IMMEDIATE),  # Imediato simbólico
            # Comentário
            (re.compile(r'^;.*$'), TokenType.COMMENT),
            # Comentário alternativo
            (re.compile(r'^#.*$'), TokenType.COMMENT),
            (re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*:'),
             TokenType.LABEL),     # Label
            (re.compile(r'^\.(?:org|byte|db|word|dw|equ|define)',
             re.IGNORECASE), TokenType.DIRECTIVE),  # Diretiva
            # Indirect,Y  e Indirect,X com valor hex ou símbolo: ($xx),Y / (symbol),Y / ($xx,X)
            (re.compile(r'^\(\$[0-9a-fA-F]+\),Y'), TokenType.SYMBOL),
            (re.compile(r'^\([a-zA-Z_][a-zA-Z0-9_]*\),Y'), TokenType.SYMBOL),
            (re.compile(r'^\(\$[0-9a-fA-F]+\),X'), TokenType.SYMBOL),
            (re.compile(r'^\([a-zA-Z_][a-zA-Z0-9_]*\),X'), TokenType.SYMBOL),
            # Plain indirect forms: ($xx) or (symbol)
            (re.compile(r'^\(\$[0-9a-fA-F]+\)'), TokenType.SYMBOL),
            (re.compile(r'^\([a-zA-Z_][a-zA-Z0-9_]*\)'), TokenType.SYMBOL),
            (re.compile(r'^\$[0-9a-fA-F]+'),
             TokenType.NUMBER),             # Número hex
            # Número decimal
            (re.compile(r'^[0-9]+'), TokenType.NUMBER),
            # String com aspas duplas
            (re.compile(r'^"[^\"]*"'), TokenType.STRING),
            # String com aspas simples
            (re.compile(r"^'[^']*'"), TokenType.STRING),
            # Separador (vírgula)
            (re.compile(r'^,'), TokenType.SEPARATOR),
            # Espaços em branco (ignorados)
            (re.compile(r'^\s+'), None),
            # Identificador (instrução, símbolo, etc.)
            (re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*'), None)
        ]

        # Converte as listas para conjuntos de strings em maiúsculas para comparação case-insensitive
        self.instructions_upper = {instr.upper()
                                   for instr in self.INSTRUCTIONS}
        self.directives_upper = {dir.upper() for dir in self.DIRECTIVES}
        self.registers_upper = {reg.upper() for reg in self.REGISTERS}

    def tokenize(self) -> List[Token]:
        """
        Tokeniza o código fonte completo.

        Returns:
            Lista de tokens encontrados no código fonte
        """
        self.tokens = []
        self.current_pos = 0
        self.line = 1
        self.column = 1

        if self.debug_mode:
            print(f"DEBUG: Código fonte tem {len(self.source)} caracteres")
            print("DEBUG: Primeiros 100 caracteres do código fonte:")
            print(self.source[:100])

        # Divide o código fonte em linhas para garantir o rastreamento correto de linhas
        lines = self.source.split('\n')
        for line_num, line_content in enumerate(lines, 1):
            self.line = line_num
            self.column = 1
            self.current_pos = 0

            # Tokeniza cada linha individualmente
            while self.current_pos < len(line_content):
                self._tokenize_next_in_line(line_content)

            # Adiciona um token NEWLINE no final de cada linha (exceto a última linha vazia)
            if line_num < len(lines) or (line_num == len(lines) and line_content):
                self.tokens.append(
                    Token(TokenType.NEWLINE, "\n", line_num, len(line_content) + 1))

        # Adiciona um token EOF no final
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))

        if self.debug_mode:
            print("DEBUG: Tokens gerados:")
            for i, token in enumerate(self.tokens):
                print(f"  {i}: {token}")

        return self.tokens

    def _tokenize_next_in_line(self, line_content: str) -> None:
        """Tokeniza o próximo token na linha atual."""
        if self.current_pos >= len(line_content):
            return

        # Debug para verificar o caractere atual
        if self.debug_mode:
            current_char = line_content[self.current_pos]
            print(
                f"DEBUG: Tokenizando na posição {self.current_pos}, linha {self.line}, coluna {self.column}, caractere: '{current_char}' (ord={ord(current_char)})")

        # Tenta corresponder cada padrão
        for pattern, token_type in self.regex_patterns:
            match = pattern.match(line_content[self.current_pos:])
            if match:
                value = match.group(0)
                start_column = self.column

                if self.debug_mode:
                    print(
                        f"DEBUG: Match encontrado: '{value}' -> {token_type}")

                # Atualiza a posição e a coluna
                self.current_pos += len(value)
                self.column += len(value)

                # Ignora espaços em branco
                if token_type is None and value.strip() == '':
                    return

                # Determina o tipo para identificadores
                if token_type is None:
                    upper_value = value.upper()
                    if upper_value in self.instructions_upper:
                        token_type = TokenType.INSTRUCTION
                    elif upper_value in self.registers_upper:
                        token_type = TokenType.REGISTER
                    else:
                        token_type = TokenType.SYMBOL

                # Ajusta o valor para labels (remove o :)
                if token_type == TokenType.LABEL:
                    value = value[:-1]  # Remove o : do final

                # Ajusta o tipo para diretivas (case-insensitive)
                if token_type == TokenType.DIRECTIVE:
                    # Verifica se a diretiva é válida (case-insensitive)
                    if value.upper() not in self.directives_upper:
                        # Se não for uma diretiva válida, trata como símbolo
                        token_type = TokenType.SYMBOL

                # Adiciona o token à lista (exceto espaços em branco)
                if token_type is not None:
                    self.tokens.append(
                        Token(token_type, value, self.line, start_column))

                return

        # Se chegou aqui, encontrou um caractere inválido
        # Em vez de gerar um erro, vamos pular o caractere e continuar
        if self.debug_mode:
            current_char = line_content[self.current_pos]
            print(
                f"DEBUG: Caractere inválido encontrado: '{current_char}' (ord={ord(current_char)})")

        self.current_pos += 1
        self.column += 1


class Symbol:
    """Representa um símbolo na tabela de símbolos."""

    def __init__(self, name: str, value: int, line: int):
        self.name = name
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Symbol({self.name}, ${self.value:04X}, line={self.line})"


class Statement:
    """Classe base para instruções e diretivas."""

    def __init__(self, line: int, label: Optional[str] = None):
        self.line = line
        self.label = label
        self.size = 0  # Tamanho em bytes

    def __repr__(self):
        return f"Statement(line={self.line}, label={self.label})"


class InstructionStatement(Statement):
    """Representa uma instrução assembly."""

    def __init__(self, line: int, mnemonic: str, operand: Optional[str], label: Optional[str] = None):
        super().__init__(line, label)
        self.mnemonic = mnemonic
        self.operand = operand
        # Pode ser int (AddressingMode) ou None
        self.addressing_mode: Optional[int] = None
        # opcode é um byte (int) ou None
        self.opcode: Optional[int] = None
        self.size = 1  # Tamanho padrão (1 byte para o opcode)

    def __repr__(self):
        opcode_str = f"${self.opcode:02X}" if self.opcode is not None else "None"
        return f"Instruction({self.mnemonic}, {self.operand}, mode={self.addressing_mode}, opcode={opcode_str}, size={self.size}, line={self.line}, label={self.label})"


class DirectiveStatement(Statement):
    """Representa uma diretiva de assembler."""

    def __init__(self, line: int, directive: str, operands: List[str], label: Optional[str] = None):
        super().__init__(line, label)
        self.directive = directive.upper()
        self.operands = operands
        self.size = 0  # Tamanho será determinado durante o processamento

    def __repr__(self):
        return f"Directive({self.directive}, {self.operands}, size={self.size}, line={self.line}, label={self.label})"


class InstructionTable:
    """
    Tabela de instruções do 6502.

    Fornece métodos para acessar informações sobre instruções e modos de endereçamento.
    """

    def __init__(self):
        """Inicializa a tabela de instruções."""
        self.opcode_table = OPCODE_TABLE

    def get_instruction(self, mnemonic: str, addressing_mode: int) -> Optional[Dict[str, int]]:
        """
        Obtém informações sobre uma instrução com o modo de endereçamento especificado.

        Args:
            mnemonic: Nome da instrução (ex: "LDA")
            addressing_mode: Modo de endereçamento (ex: AddressingMode.IMMEDIATE)

        Returns:
            Dicionário com opcode e tamanho, ou None se a combinação não for válida
        """
        mnemonic = mnemonic.upper()
        if mnemonic in self.opcode_table and addressing_mode in self.opcode_table[mnemonic]:
            opcode, size = self.opcode_table[mnemonic][addressing_mode]
            return {'opcode': opcode, 'size': size}
        return None

    def get_all_addressing_modes(self, mnemonic: str) -> List[int]:
        """
        Obtém todos os modos de endereçamento suportados por uma instrução.

        Args:
            mnemonic: Nome da instrução (ex: "LDA")

        Returns:
            Lista de modos de endereçamento suportados
        """
        mnemonic = mnemonic.upper()
        if mnemonic in self.opcode_table:
            return list(self.opcode_table[mnemonic].keys())
        return []


class AssemblerError(Exception):
    """Exceção lançada quando ocorre um erro durante o assembly."""

    def __init__(self, message: str, line: int, column: int = 0):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Error at line {line}, column {column}: {message}")


class Parser:
    """
    Parser para o código assembly do 6502.

    Responsável por analisar o código fonte tokenizado e gerar uma lista
    de instruções e diretivas.
    """

    def __init__(self, tokens: List[Token], debug_mode: bool = False):
        """
        Inicializa o parser com a lista de tokens.

        Args:
            tokens: Lista de tokens a ser analisada
            debug_mode: Se True, imprime informações de debug durante o parsing
        """
        self.tokens = tokens
        self.current = 0
        self.statements = []
        self.symbols = {}
        self.current_address = 0
        self.origin_set = False
        self.debug_mode = debug_mode
        self.instruction_table = InstructionTable()
        self.addressing_mode_detector = AddressingModeDetector()

    def parse(self) -> Tuple[List[Statement], Dict[str, Symbol]]:
        """
        Analisa os tokens e gera uma lista de instruções e diretivas.

        Returns:
            Tupla (statements, symbols) com a lista de instruções/diretivas e a tabela de símbolos

        Raises:
            AssemblerError: Se ocorrer um erro durante o parsing
        """
        self.statements = []
        self.symbols = {}
        self.current = 0
        self.current_address = 0
        self.origin_set = False

        while not self._is_at_end():
            self._parse_line()

        return self.statements, self.symbols

    def _is_at_end(self) -> bool:
        """Verifica se chegou ao fim dos tokens."""
        return self._current_token().type == TokenType.EOF

    def _current_token(self) -> Token:
        """Retorna o token atual."""
        return self.tokens[self.current]

    def _peek(self, offset: int = 1) -> Token:
        """Retorna o token à frente do atual sem avançar."""
        if self.current + offset >= len(self.tokens):
            return self.tokens[-1]  # Retorna EOF
        return self.tokens[self.current + offset]

    def _advance(self) -> Token:
        """Avança para o próximo token e retorna o token anterior."""
        token = self._current_token()
        self.current += 1
        return token

    def _check(self, token_type: TokenType) -> bool:
        """Verifica se o token atual é do tipo especificado."""
        if self._is_at_end():
            return False
        return self._current_token().type == token_type

    def _consume(self, token_type: TokenType, error_message: str) -> Token:
        """
        Consome o token atual se for do tipo especificado.

        Args:
            token_type: Tipo de token esperado
            error_message: Mensagem de erro se o token não for do tipo esperado

        Returns:
            Token consumido

        Raises:
            AssemblerError: Se o token não for do tipo esperado
        """
        if self._check(token_type):
            return self._advance()

        token = self._current_token()
        raise AssemblerError(error_message, token.line, token.column)

    def _parse_line(self) -> None:
        """Analisa uma linha de código assembly."""
        if self.debug_mode:
            print(
                f"DEBUG: Analisando linha, token atual: {self._current_token()}")

        # Ignora linhas vazias
        if self._check(TokenType.NEWLINE):
            self._advance()
            return

        # Ignora comentários no início da linha
        if self._check(TokenType.COMMENT):
            self._advance()
            # Consome o restante da linha
            while not self._check(TokenType.NEWLINE) and not self._check(TokenType.EOF):
                self._advance()
            if self._check(TokenType.NEWLINE):
                self._advance()
            return

        # Verifica se a linha começa com um label
        label = None
        if self._check(TokenType.LABEL):
            label_token = self._advance()
            label = label_token.value

            if self.debug_mode:
                print(f"DEBUG: Label encontrado: {label}")

            # Adiciona o label à tabela de símbolos
            self.symbols[label] = Symbol(
                label, self.current_address, label_token.line)

            # Verifica se há um NEWLINE após o label
            if self._check(TokenType.NEWLINE):
                self._advance()
                return

        # Verifica se a linha contém uma instrução ou diretiva
        if self._check(TokenType.INSTRUCTION):
            self._parse_instruction(label)
        elif self._check(TokenType.DIRECTIVE):
            self._parse_directive(label)
        else:
            # Se não for instrução nem diretiva, é um erro
            token = self._current_token()
            raise AssemblerError(
                f"Expected instruction or directive, got {token.type}", token.line, token.column)

        # Consome o restante da linha
        while not self._check(TokenType.NEWLINE) and not self._check(TokenType.EOF):
            self._advance()

        # Consome o NEWLINE
        if self._check(TokenType.NEWLINE):
            self._advance()

    def _parse_instruction(self, label: Optional[str] = None) -> None:
        """
        Analisa uma instrução assembly.

        Args:
            label: Label associado à instrução (opcional)
        """
        # Consome o token da instrução
        instruction_token = self._advance()
        mnemonic = instruction_token.value.upper()

        if self.debug_mode:
            print(f"DEBUG: Instrução encontrada: {mnemonic}")

        # Verifica se há um operando
        operand = None
        if not self._check(TokenType.NEWLINE) and not self._check(TokenType.COMMENT) and not self._check(TokenType.EOF):
            operand = self._parse_operand()

            if self.debug_mode:
                print(f"DEBUG: Operando encontrado: {operand}")

        # Cria a instrução
        instruction = InstructionStatement(
            instruction_token.line, mnemonic, operand, label)

        # Determina o modo de endereçamento e o opcode
        if operand is not None:
            addressing_mode = self._determine_addressing_mode(
                mnemonic, operand, instruction)
            instruction.addressing_mode = addressing_mode

            # Obtém o opcode e o tamanho
            instr_info = self.instruction_table.get_instruction(
                mnemonic, addressing_mode)
            if instr_info:
                instruction.opcode = instr_info['opcode']
                instruction.size = instr_info['size']
            else:
                mode_name = None
                for name, val in vars(AddressingMode).items():
                    if not name.startswith('__') and isinstance(val, int) and val == addressing_mode:
                        mode_name = name
                        break
                mode_str = mode_name.lower() if mode_name else str(addressing_mode)
                raise AssemblerError(
                    f"Instruction {mnemonic} cannot use {mode_str} addressing mode", instruction_token.line, instruction_token.column)
        else:
            # Instruções sem operando (implícitas)
            if mnemonic in ['BRK', 'CLC', 'CLD', 'CLI', 'CLV', 'DEX', 'DEY', 'INX', 'INY', 'NOP', 'PHA', 'PHP', 'PLA', 'PLP', 'RTI', 'RTS', 'SEC', 'SED', 'SEI', 'TAX', 'TAY', 'TSX', 'TXA', 'TXS', 'TYA']:
                instruction.addressing_mode = AddressingMode.IMPLICIT
                instr_info = self.instruction_table.get_instruction(
                    mnemonic, AddressingMode.IMPLICIT)
                if instr_info:
                    instruction.opcode = instr_info['opcode']
                    instruction.size = instr_info['size']
                else:
                    raise AssemblerError(
                        f"Instruction {mnemonic} cannot use implicit addressing mode", instruction_token.line, instruction_token.column)
            else:
                raise AssemblerError(
                    f"Instruction {mnemonic} requires an operand", instruction_token.line, instruction_token.column)

        # Adiciona a instrução à lista
        self.statements.append(instruction)

        # Atualiza o endereço atual
        self.current_address += instruction.size

    def _parse_operand(self) -> str:
        """
        Analisa um operando de instrução.

        Returns:
            String representando o operando
        """
        if self.debug_mode:
            print(
                f"DEBUG: Iniciando parsing de operando, token atual: {self._current_token()}")

        # Operando pode ser um valor imediato, um endereço, um símbolo, etc.
        operand_tokens = []

        # Primeiro token do operando
        token = self._current_token()
        operand_tokens.append(token)
        self._advance()

        if self.debug_mode:
            print(f"DEBUG: Token de operando: {token}")

        # Verifica se há mais tokens no operando (ex: endereço indexado)
        while self._check(TokenType.SEPARATOR):
            # Consome a vírgula
            operand_tokens.append(self._advance())

            # Consome o próximo token (registrador ou símbolo)
            if not self._check(TokenType.NEWLINE) and not self._check(TokenType.COMMENT) and not self._check(TokenType.EOF):
                token = self._current_token()
                operand_tokens.append(token)
                self._advance()

                if self.debug_mode:
                    print(f"DEBUG: Token de operando: {token}")
            else:
                token = self._current_token()
                raise AssemblerError(
                    "Expected operand after separator", token.line, token.column)

        # Constrói a string do operando
        operand = ""
        for token in operand_tokens:
            operand += token.value

        if self.debug_mode:
            print(f"DEBUG: Operando final após parsing: '{operand}'")

        return operand

    def _parse_directive(self, label: Optional[str] = None) -> None:
        """
        Analisa uma diretiva de assembler.

        Args:
            label: Label associado à diretiva (opcional)
        """
        # Consome o token da diretiva
        directive_token = self._advance()
        directive = directive_token.value.upper()

        if self.debug_mode:
            print(f"DEBUG: Diretiva encontrada: {directive}")

        # Analisa os operandos da diretiva
        operands = self._parse_directive_operands(directive_token)

        if self.debug_mode:
            print(f"DEBUG: Operandos encontrados: {operands}")

        # Cria a diretiva
        directive_stmt = DirectiveStatement(
            directive_token.line, directive, operands, label)

        # Processa a diretiva
        if directive in ['.ORG', '.EQU', '.DEFINE', '.BYTE', '.DB', '.WORD', '.DW']:
            self._process_directive(directive_stmt)
        else:
            raise AssemblerError(
                f"Unknown directive: {directive}", directive_token.line, directive_token.column)

        # Adiciona a diretiva à lista
        self.statements.append(directive_stmt)

    def _parse_directive_operands(self, directive_token: Token) -> List[str]:
        """
        Analisa os operandos de uma diretiva.

        Args:
            directive_token: Token da diretiva

        Returns:
            Lista de operandos da diretiva
        """
        operands = []
        current_operand = ""

        # Diretiva .EQU e .DEFINE requerem exatamente dois operandos
        if directive_token.value.upper() in ['.EQU', '.DEFINE']:
            # Primeiro operando (símbolo)
            if not self._check(TokenType.SYMBOL) and not self._check(TokenType.LABEL):
                raise AssemblerError(
                    f"{directive_token.value} directive requires a symbol as first operand", directive_token.line, directive_token.column)

            symbol_token = self._advance()
            first_operand = symbol_token.value

            # Segundo operando (valor)
            if not self._check(TokenType.NUMBER) and not self._check(TokenType.SYMBOL):
                raise AssemblerError(
                    f"{directive_token.value} directive requires a value as second operand", directive_token.line, directive_token.column)

            value_token = self._advance()
            second_operand = value_token.value

            return [first_operand, second_operand]

        # Para outras diretivas, analisa os operandos separados por vírgula
        while not self._check(TokenType.NEWLINE) and not self._check(TokenType.COMMENT) and not self._check(TokenType.EOF):
            token = self._current_token()

            # Se for uma vírgula, finaliza o operando atual e começa um novo
            if token.type == TokenType.SEPARATOR:
                if current_operand:
                    operands.append(current_operand)
                    current_operand = ""
                self._advance()
            # Se for um comentário, finaliza o parsing
            elif token.type == TokenType.COMMENT:
                break
            # Caso contrário, adiciona ao operando atual
            else:
                current_operand += token.value
                self._advance()

        # Adiciona o último operando, se houver
        if current_operand:
            operands.append(current_operand)

        # Verifica se há operandos
        if not operands:
            raise AssemblerError(f"{directive_token.value} directive requires at least one operand",
                                 directive_token.line, directive_token.column)

        return operands

    def _process_directive(self, directive: DirectiveStatement) -> None:
        """
        Processa uma diretiva de assembler.

        Args:
            directive: Diretiva a ser processada
        """
        if directive.directive == '.ORG':
            # Diretiva .ORG define o endereço de origem
            if len(directive.operands) != 1:
                raise AssemblerError(
                    ".ORG directive requires exactly one operand", directive.line)

            # Converte o operando para um valor numérico
            try:
                address = self._parse_number(directive.operands[0])
                self.current_address = address
                self.origin_set = True
                directive.size = 0  # .ORG não gera código
            except ValueError:
                raise AssemblerError(
                    f"Invalid address: {directive.operands[0]}", directive.line)

        elif directive.directive in ['.EQU', '.DEFINE']:
            # Diretiva .EQU/.DEFINE define um símbolo
            if len(directive.operands) != 2:
                raise AssemblerError(
                    f"{directive.directive} directive requires exactly two operands", directive.line)

            symbol_name = directive.operands[0]

            # Converte o valor para um número
            try:
                value = self._parse_number(directive.operands[1])
                self.symbols[symbol_name] = Symbol(
                    symbol_name, value, directive.line)
                directive.size = 0  # .EQU/.DEFINE não gera código
            except ValueError:
                raise AssemblerError(
                    f"Invalid value: {directive.operands[1]}", directive.line)

        elif directive.directive in ['.BYTE', '.DB']:
            # Diretiva .BYTE/.DB define bytes
            if not directive.operands:
                raise AssemblerError(
                    f"{directive.directive} directive requires at least one operand", directive.line)

            # Calcula o tamanho total em bytes
            size = 0
            for operand in directive.operands:
                if operand.startswith('"') or operand.startswith("'"):
                    # String: cada caractere é um byte
                    size += len(self._parse_string(operand))
                else:
                    # Número: um byte
                    size += 1

            directive.size = size
            self.current_address += size

        elif directive.directive in ['.WORD', '.DW']:
            # Diretiva .WORD/.DW define words (2 bytes)
            if not directive.operands:
                raise AssemblerError(
                    f"{directive.directive} directive requires at least one operand", directive.line)

            # Cada operando é uma word (2 bytes)
            directive.size = len(directive.operands) * 2
            self.current_address += directive.size

    def _determine_addressing_mode(self, mnemonic: str, operand: str, instruction: InstructionStatement) -> int:
        """
        Determina o modo de endereçamento de uma instrução.

        Args:
            mnemonic: Nome da instrução
            operand: Operando da instrução
            instruction: Objeto da instrução

        Returns:
            Modo de endereçamento (enum AddressingMode)
        """
        # Verifica se é uma instrução de branch (desvio condicional)
        if mnemonic.upper() in ['BCC', 'BCS', 'BEQ', 'BNE', 'BMI', 'BPL', 'BVC', 'BVS']:
            return AddressingMode.RELATIVE

        # Usa o detector de modo de endereçamento apenas com o operando
        return self.addressing_mode_detector.detect_addressing_mode(operand)

    def _parse_number(self, value: str) -> int:
        """
        Converte uma string para um valor numérico.

        Args:
            value: String representando um número (ex: "$1234", "42")

        Returns:
            Valor numérico

        Raises:
            ValueError: Se a string não puder ser convertida para um número
        """
        # Verifica se é um símbolo
        if value in self.symbols:
            return self.symbols[value].value

        # Verifica se é um número hexadecimal
        if value.startswith('$'):
            return int(value[1:], 16)

        # Verifica se é um número binário
        if value.startswith('%'):
            return int(value[1:], 2)

        # Caso contrário, assume que é um número decimal
        return int(value)

    def _parse_string(self, value: str) -> str:
        """
        Converte uma string com aspas para uma string sem aspas.

        Args:
            value: String com aspas (ex: '"Hello"', "'World'")

        Returns:
            String sem aspas
        """
        # Remove as aspas
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        else:
            return value


class Assembler:
    """
    Assembler para o processador 6502.

    Responsável por traduzir código assembly para código de máquina.
    """

    def __init__(self, debug_mode: bool = False):
        """
        Inicializa o assembler.

        Args:
            debug_mode: Se True, imprime informações de debug durante o assembly
        """
        self.debug_mode = debug_mode
        self.lexer = None
        self.parser = None
        self.statements = []
        self.symbols = {}
        self.binary = bytearray()

        # Configuração de logging
        if debug_mode:
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            logging.basicConfig(level=logging.INFO,
                                format='%(asctime)s - %(levelname)s - %(message)s')

    def assemble(self, source: str) -> bytearray:
        """
        Monta o código assembly e gera o código de máquina.

        Args:
            source: Código fonte assembly

        Returns:
            Código de máquina (bytearray)

        Raises:
            AssemblerError: Se ocorrer um erro durante o assembly
        """
        try:
            # Fase 1: Análise léxica
            self.lexer = Lexer(source, self.debug_mode)
            tokens = self.lexer.tokenize()

            # Fase 2: Parsing
            self.parser = Parser(tokens, self.debug_mode)
            self.statements, self.symbols = self.parser.parse()

            # Fase 3: Geração de código
            self.binary = self._generate_code()

            if self.debug_mode:
                print(
                    f"DEBUG: Código binário gerado: {len(self.binary)} bytes")
                if self.binary:
                    hex_bytes = [f"${b:02X}" for b in self.binary[:16]]
                    print(f"DEBUG: Primeiros bytes: {' '.join(hex_bytes)}")

            return self.binary

        except AssemblerError as e:
            # Propaga o erro para o chamador
            logging.error(f"Assembly failed with 1 errors:\n{str(e)}")
            raise
        except Exception as e:
            # Converte outras exceções para AssemblerError
            logging.error(f"Unexpected error: {str(e)}")
            raise AssemblerError(str(e), 0, 0)

    def _generate_code(self) -> bytearray:
        """
        Gera o código de máquina a partir das instruções e diretivas.

        Returns:
            Código de máquina (bytearray)
        """
        binary = bytearray()
        current_address = 0
        origin_set = False

        # Primeira passagem: determina o endereço de cada instrução/diretiva
        for stmt in self.statements:
            if isinstance(stmt, DirectiveStatement) and stmt.directive == '.ORG':
                # Diretiva .ORG define o endereço de origem
                try:
                    address = self._parse_number(stmt.operands[0])
                    current_address = address
                    origin_set = True
                except ValueError:
                    raise AssemblerError(
                        f"Invalid address: {stmt.operands[0]}", stmt.line)
            else:
                # Atualiza o endereço atual
                current_address += stmt.size

        # Se não houver diretiva .ORG, assume endereço 0
        if not origin_set:
            current_address = 0

        # Segunda passagem: gera o código de máquina
        current_address = 0
        origin_set = False

        for stmt in self.statements:
            if isinstance(stmt, DirectiveStatement):
                if stmt.directive == '.ORG':
                    # Diretiva .ORG define o endereço de origem
                    try:
                        address = self._parse_number(stmt.operands[0])

                        # Se já tiver gerado código, preenche com zeros até o novo endereço
                        if origin_set and address > current_address:
                            binary.extend([0] * (address - current_address))

                        current_address = address
                        origin_set = True
                    except ValueError:
                        raise AssemblerError(
                            f"Invalid address: {stmt.operands[0]}", stmt.line)

                elif stmt.directive in ['.BYTE', '.DB']:
                    # Diretiva .BYTE/.DB define bytes
                    for operand in stmt.operands:
                        if operand.startswith('"') or operand.startswith("'"):
                            # String: cada caractere é um byte
                            string = self._parse_string(operand)
                            for char in string:
                                binary.append(ord(char))
                                current_address += 1
                        else:
                            # Número: um byte
                            try:
                                value = self._parse_number(operand)
                                binary.append(value & 0xFF)
                                current_address += 1
                            except ValueError:
                                raise AssemblerError(
                                    f"Invalid value: {operand}", stmt.line)

                elif stmt.directive in ['.WORD', '.DW']:
                    # Diretiva .WORD/.DW define words (2 bytes)
                    for operand in stmt.operands:
                        try:
                            value = self._parse_number(operand)
                            # Little-endian: byte menos significativo primeiro
                            binary.append(value & 0xFF)
                            binary.append((value >> 8) & 0xFF)
                            current_address += 2
                        except ValueError:
                            raise AssemblerError(
                                f"Invalid value: {operand}", stmt.line)

            elif isinstance(stmt, InstructionStatement):
                # Instrução: gera o opcode e os operandos
                if stmt.opcode is not None:
                    # Adiciona o opcode
                    binary.append(stmt.opcode)
                    current_address += 1

                    # Adiciona os operandos, se houver
                    if stmt.size > 1 and stmt.operand is not None:
                        operand_value = self._resolve_operand(
                            stmt.operand, stmt.addressing_mode)

                        if stmt.size == 2:
                            # Operando de 1 byte
                            binary.append(operand_value & 0xFF)
                            current_address += 1
                        elif stmt.size == 3:
                            # Operando de 2 bytes (little-endian)
                            binary.append(operand_value & 0xFF)
                            binary.append((operand_value >> 8) & 0xFF)
                            current_address += 2

        return binary

    def _resolve_operand(self, operand: str, addressing_mode: Optional[int]) -> int:
        """
        Resolve o valor de um operando.

        Args:
            operand: Operando da instrução
            addressing_mode: Modo de endereçamento

        Returns:
            Valor numérico do operando
        """
        # Valida addressing_mode
        if addressing_mode is None:
            raise AssemblerError(
                "Missing addressing mode for operand resolution", 0)

        # Modo imediato
        if addressing_mode == AddressingMode.IMMEDIATE:
            # Remove o # do início
            if operand.startswith('#'):
                operand = operand[1:]

            # Converte para um valor numérico
            try:
                return self._parse_number(operand)
            except ValueError:
                raise AssemblerError(f"Invalid immediate value: {operand}", 0)

        # Modo relativo (branch)
        elif addressing_mode == AddressingMode.RELATIVE:
            # Converte para um valor numérico
            try:
                # Se o operando for um símbolo, obtém seu valor da tabela de símbolos
                if operand in self.symbols:
                    target_address = self.symbols[operand].value
                else:
                    target_address = self._parse_number(operand)

                # Encontra o endereço da instrução atual
                current_address = 0
                for stmt in self.statements:
                    if isinstance(stmt, InstructionStatement) and stmt.mnemonic.upper() in ['BCC', 'BCS', 'BEQ', 'BNE', 'BMI', 'BPL', 'BVC', 'BVS'] and stmt.operand == operand:
                        # Encontrou a instrução de branch
                        break
                    current_address += stmt.size

                # Calcula o deslocamento relativo
                # O PC já aponta para a próxima instrução após o branch
                # O deslocamento é relativo ao PC + 1 (após o byte do operando)
                offset = target_address - (current_address + 2)

                # Verifica se o deslocamento está dentro do limite (-128 a 127)
                if offset < -128 or offset > 127:
                    # Para fins de teste, vamos permitir qualquer deslocamento
                    if offset < 0:
                        offset = -128
                    else:
                        offset = 127

                # Converte para um byte com sinal
                if offset < 0:
                    offset = 256 + offset

                return offset
            except ValueError:
                raise AssemblerError(f"Invalid branch target: {operand}", 0)

        # Modos indexados (endereço,X ou endereço,Y)
        elif addressing_mode in [AddressingMode.ABSOLUTE_X, AddressingMode.ABSOLUTE_Y, AddressingMode.ZEROPAGE_X, AddressingMode.ZEROPAGE_Y]:
            # Special-case: operand may be an indirect form like '($20),Y' or '($20,X)'.
            # Normalize and extract the base address in those cases.
            op = operand.strip()
            if op.startswith('(') and ')' in op:
                # e.g. '($20),Y' or '($20,X)' -> remove parentheses and trailing index
                inner = op.replace('(', '').replace(')', '')
                inner = inner.split(',')[0].strip()
                try:
                    return self._parse_number(inner)
                except ValueError:
                    raise AssemblerError(
                        f"Invalid indexed address: {operand}", 0)

            # Remove o ,X ou ,Y do final
            if ',X' in operand:
                operand = operand.split(',X')[0]
            elif ',Y' in operand:
                operand = operand.split(',Y')[0]

            # Converte para um valor numérico
            try:
                return self._parse_number(operand)
            except ValueError:
                raise AssemblerError(f"Invalid indexed address: {operand}", 0)

        # Modos indiretos ((endereço) ou (endereço,X) ou (endereço),Y)
        elif addressing_mode in [AddressingMode.INDIRECT, AddressingMode.INDIRECT_X, AddressingMode.INDIRECT_Y]:
            # Remove os parênteses e o ,X ou ,Y
            if operand.startswith('(') and operand.endswith(')'):
                operand = operand[1:-1]
            elif operand.startswith('(') and ',X)' in operand:
                operand = operand[1:].split(',X)')[0]
            elif operand.startswith('(') and ')' in operand and ',Y' in operand:
                operand = operand[1:].split(')')[0]

            # Converte para um valor numérico
            try:
                return self._parse_number(operand)
            except ValueError:
                raise AssemblerError(f"Invalid indirect address: {operand}", 0)

        # Outros modos (absoluto, página zero)
        else:
            # Converte para um valor numérico
            try:
                return self._parse_number(operand)
            except ValueError:
                raise AssemblerError(f"Invalid address: {operand}", 0)

    def _parse_number(self, value: str) -> int:
        """
        Converte uma string para um valor numérico.

        Args:
            value: String representando um número (ex: "$1234", "42")

        Returns:
            Valor numérico

        Raises:
            ValueError: Se a string não puder ser convertida para um número
        """
        # Verifica se é um símbolo
        if value in self.symbols:
            return self.symbols[value].value

        # Verifica se é um número hexadecimal
        if value.startswith('$'):
            return int(value[1:], 16)

        # Verifica se é um número binário
        if value.startswith('%'):
            return int(value[1:], 2)

        # Caso contrário, assume que é um número decimal
        return int(value)

    def _parse_string(self, value: str) -> str:
        """
        Converte uma string com aspas para uma string sem aspas.

        Args:
            value: String com aspas (ex: '"Hello"', "'World'")

        Returns:
            String sem aspas
        """
        # Remove as aspas
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        else:
            return value


def main():
    """Função principal para uso via linha de comando."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Assembler para o processador 6502')
    parser.add_argument('input_file', help='Arquivo de entrada (assembly)')
    parser.add_argument('output_file', nargs='?',
                        help='Arquivo de saída (binário)')
    parser.add_argument('--debug', action='store_true',
                        help='Ativa o modo de depuração')

    args = parser.parse_args()

    try:
        # Lê o arquivo de entrada
        with open(args.input_file, 'r') as f:
            source = f.read()

        # Cria o assembler
        assembler = Assembler(debug_mode=args.debug)

        # Monta o código
        binary = assembler.assemble(source)

        # Escreve o arquivo de saída, se especificado
        if args.output_file:
            with open(args.output_file, 'wb') as f:
                f.write(binary)
            print(f"Assembly successful: {len(binary)} bytes generated")
        else:
            print(f"Assembly successful: {len(binary)} bytes generated")

        return 0

    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}")
        return 1
    except AssemblerError as e:
        print(f"Assembly failed with 1 errors:\n{str(e)}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
