# -*- coding: utf-8 -*-
"""
Implementação de suporte a macros e diretivas condicionais para o assembler 6502.

Este módulo estende o assembler 6502 com recursos avançados:
- Macros: Permitem definir blocos de código reutilizáveis
- Diretivas condicionais: Permitem compilação condicional (.if, .ifdef, .ifndef, .else, .endif)
- Inclusão de arquivos: Permite incluir código de outros arquivos (.include)
"""

import re
import os
from typing import Dict, List, Tuple, Optional, Set, Union, Any

class MacroDefinition:
    """Representa uma definição de macro."""
    def __init__(self, name: str, params: List[str], body: List[str]):
        """
        Inicializa uma definição de macro.
        
        Args:
            name: Nome da macro
            params: Lista de parâmetros da macro
            body: Corpo da macro (linhas de código)
        """
        self.name = name
        self.params = params
        self.body = body
    
    def expand(self, args: List[str]) -> List[str]:
        """
        Expande a macro com os argumentos fornecidos.
        
        Args:
            args: Lista de argumentos para substituir os parâmetros
        
        Returns:
            Lista de linhas de código com os parâmetros substituídos
        """
        if len(args) != len(self.params):
            raise ValueError(f"Macro {self.name} expects {len(self.params)} arguments, got {len(args)}")
        
        # Cria um dicionário de substituição
        substitutions = dict(zip(self.params, args))
        
        # Substitui os parâmetros no corpo da macro
        expanded_body = []
        for line in self.body:
            # Substitui cada parâmetro pelo argumento correspondente
            for param, arg in substitutions.items():
                # Usa regex para substituir apenas parâmetros completos, não partes de palavras
                line = re.sub(r'\b' + re.escape(param) + r'\b', arg, line)
            expanded_body.append(line)
        
        return expanded_body

class ConditionalBlock:
    """Representa um bloco condicional (.if, .ifdef, .ifndef)."""
    def __init__(self, condition_type: str, condition: str, active: bool):
        """
        Inicializa um bloco condicional.
        
        Args:
            condition_type: Tipo de condição (.if, .ifdef, .ifndef)
            condition: Expressão ou símbolo da condição
            active: Indica se o bloco está ativo (deve ser processado)
        """
        self.condition_type = condition_type
        self.condition = condition
        self.active = active
        self.has_else = False  # Indica se o bloco tem uma cláusula .else

class MacroProcessor:
    """Processador de macros e diretivas condicionais para o assembler 6502."""
    def __init__(self):
        """Inicializa o processador de macros."""
        self.macros: Dict[str, MacroDefinition] = {}
        self.symbols: Dict[str, Any] = {}
        self.conditional_stack: List[ConditionalBlock] = []
        self.current_macro: Optional[MacroDefinition] = None
        self.macro_body: List[str] = []
        self.in_macro_definition = False
    
    def process_file(self, filename: str) -> List[str]:
        """
        Processa um arquivo de código fonte, expandindo macros e processando diretivas condicionais.
        
        Args:
            filename: Caminho do arquivo a ser processado
        
        Returns:
            Lista de linhas de código processadas
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")
        
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        return self.process_lines(lines, os.path.dirname(filename))
    
    def process_lines(self, lines: List[str], base_dir: str = '') -> List[str]:
        """
        Processa uma lista de linhas de código, expandindo macros e processando diretivas condicionais.
        
        Args:
            lines: Lista de linhas de código a serem processadas
            base_dir: Diretório base para resolução de caminhos relativos em .include
        
        Returns:
            Lista de linhas de código processadas
        """
        processed_lines = []
        line_number = 0
        
        while line_number < len(lines):
            line = lines[line_number].strip()
            line_number += 1
            
            # Ignora linhas vazias e comentários
            if not line or line.startswith(';') or line.startswith('#'):
                if not self.in_macro_definition:
                    processed_lines.append(line)
                else:
                    self.macro_body.append(line)
                continue
            
            # Processa diretivas de macro e condicionais
            if line.startswith('.'):
                directive_parts = line.split(None, 1)
                directive = directive_parts[0].lower()
                
                # Diretiva .macro
                if directive == '.macro':
                    if self.in_macro_definition:
                        raise SyntaxError(f"Nested macro definition not allowed: {line}")
                    
                    if len(directive_parts) < 2:
                        raise SyntaxError(f"Invalid macro definition: {line}")
                    
                    # Extrai o nome da macro e os parâmetros
                    macro_def = directive_parts[1].split()
                    if not macro_def:
                        raise SyntaxError(f"Invalid macro definition: {line}")
                    
                    macro_name = macro_def[0]
                    macro_params = macro_def[1:] if len(macro_def) > 1 else []
                    
                    self.in_macro_definition = True
                    self.current_macro = MacroDefinition(macro_name, macro_params, [])
                    self.macro_body = []
                    continue
                
                # Diretiva .endmacro
                elif directive == '.endmacro':
                    if not self.in_macro_definition:
                        raise SyntaxError(f"Unexpected .endmacro: {line}")
                    
                    self.current_macro.body = self.macro_body
                    self.macros[self.current_macro.name] = self.current_macro
                    self.in_macro_definition = False
                    self.current_macro = None
                    self.macro_body = []
                    continue
                
                # Diretiva .include
                elif directive == '.include':
                    if self.in_macro_definition:
                        self.macro_body.append(line)
                        continue
                    
                    if not self._is_active_conditional_block():
                        continue
                    
                    if len(directive_parts) < 2:
                        raise SyntaxError(f"Invalid include directive: {line}")
                    
                    # Extrai o nome do arquivo a ser incluído
                    include_file = directive_parts[1].strip('"\'')
                    include_path = os.path.join(base_dir, include_file)
                    
                    # Processa o arquivo incluído
                    included_lines = self.process_file(include_path)
                    processed_lines.extend(included_lines)
                    continue
                
                # Diretivas condicionais
                elif directive in ['.if', '.ifdef', '.ifndef']:
                    if self.in_macro_definition:
                        self.macro_body.append(line)
                        continue
                    
                    if len(directive_parts) < 2:
                        raise SyntaxError(f"Invalid conditional directive: {line}")
                    
                    condition = directive_parts[1].strip()
                    active = False
                    
                    # Verifica se o bloco pai está ativo
                    parent_active = self._is_active_conditional_block()
                    
                    if directive == '.if':
                        # Avalia a expressão condicional
                        if parent_active:
                            try:
                                # Substitui símbolos por seus valores
                                for symbol, value in self.symbols.items():
                                    condition = re.sub(r'\b' + re.escape(symbol) + r'\b', str(value), condition)
                                active = bool(eval(condition))
                            except Exception as e:
                                raise SyntaxError(f"Error evaluating condition: {condition} - {str(e)}")
                    
                    elif directive == '.ifdef':
                        # Verifica se o símbolo está definido
                        if parent_active:
                            active = condition in self.symbols
                    
                    elif directive == '.ifndef':
                        # Verifica se o símbolo não está definido
                        if parent_active:
                            active = condition not in self.symbols
                    
                    self.conditional_stack.append(ConditionalBlock(directive, condition, active and parent_active))
                    continue
                
                # Diretiva .else
                elif directive == '.else':
                    if self.in_macro_definition:
                        self.macro_body.append(line)
                        continue
                    
                    if not self.conditional_stack:
                        raise SyntaxError(f"Unexpected .else: {line}")
                    
                    # Inverte a condição do bloco atual, mas apenas se o bloco pai estiver ativo
                    current_block = self.conditional_stack[-1]
                    if not current_block.has_else:
                        parent_active = True
                        if len(self.conditional_stack) > 1:
                            parent_active = self.conditional_stack[-2].active
                        
                        current_block.active = not current_block.active and parent_active
                        current_block.has_else = True
                    else:
                        raise SyntaxError(f"Multiple .else directives in the same conditional block: {line}")
                    
                    continue
                
                # Diretiva .endif
                elif directive == '.endif':
                    if self.in_macro_definition:
                        self.macro_body.append(line)
                        continue
                    
                    if not self.conditional_stack:
                        raise SyntaxError(f"Unexpected .endif: {line}")
                    
                    self.conditional_stack.pop()
                    continue
                
                # Diretiva .equ / .define
                elif directive in ['.equ', '.define']:
                    if self.in_macro_definition:
                        self.macro_body.append(line)
                        continue
                    
                    if not self._is_active_conditional_block():
                        continue
                    
                    if len(directive_parts) < 2:
                        raise SyntaxError(f"Invalid define directive: {line}")
                    
                    # Extrai o nome do símbolo e o valor
                    define_parts = directive_parts[1].split(None, 1)
                    if len(define_parts) < 2:
                        raise SyntaxError(f"Invalid define directive: {line}")
                    
                    symbol = define_parts[0]
                    value = define_parts[1].strip()
                    
                    # Tenta converter para número se possível
                    try:
                        if value.startswith('$'):
                            value = int(value[1:], 16)
                        elif value.startswith('%'):
                            value = int(value[1:], 2)
                        else:
                            value = int(value)
                    except ValueError:
                        # Mantém como string se não for um número
                        pass
                    
                    self.symbols[symbol] = value
                    processed_lines.append(line)
                    continue
                
                # Outras diretivas
                else:
                    if self.in_macro_definition:
                        self.macro_body.append(line)
                        continue
                    
                    if not self._is_active_conditional_block():
                        continue
                    
                    processed_lines.append(line)
                    continue
            
            # Verifica se é uma chamada de macro
            elif not self.in_macro_definition and self._is_active_conditional_block():
                macro_call = line.split(None, 1)
                macro_name = macro_call[0]
                
                if macro_name in self.macros:
                    # Extrai os argumentos da chamada de macro
                    args = []
                    if len(macro_call) > 1:
                        # Divide os argumentos, respeitando vírgulas dentro de strings
                        in_string = False
                        string_char = None
                        current_arg = ""
                        for char in macro_call[1]:
                            if char in ['"', "'"]:
                                if not in_string:
                                    in_string = True
                                    string_char = char
                                elif char == string_char:
                                    in_string = False
                                    string_char = None
                                current_arg += char
                            elif char == ',' and not in_string:
                                args.append(current_arg.strip())
                                current_arg = ""
                            else:
                                current_arg += char
                        
                        if current_arg:
                            args.append(current_arg.strip())
                    
                    # Expande a macro
                    expanded_lines = self.macros[macro_name].expand(args)
                    
                    # Processa recursivamente as linhas expandidas
                    expanded_processed = self.process_lines(expanded_lines, base_dir)
                    processed_lines.extend(expanded_processed)
                    continue
            
            # Linhas normais
            if self.in_macro_definition:
                self.macro_body.append(line)
            elif self._is_active_conditional_block():
                processed_lines.append(line)
        
        # Verifica se todas as diretivas condicionais foram fechadas
        if self.conditional_stack:
            raise SyntaxError("Unclosed conditional block")
        
        # Verifica se todas as definições de macro foram fechadas
        if self.in_macro_definition:
            raise SyntaxError("Unclosed macro definition")
        
        return processed_lines
    
    def _is_active_conditional_block(self) -> bool:
        """
        Verifica se o bloco condicional atual está ativo.
        
        Returns:
            True se o bloco estiver ativo ou se não houver blocos condicionais,
            False caso contrário
        """
        if not self.conditional_stack:
            return True
        
        # Verifica se todos os blocos na pilha estão ativos
        return all(block.active for block in self.conditional_stack)
