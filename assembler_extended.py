# -*- coding: utf-8 -*-
"""
Integração do processador de macros com o assembler 6502.

Este módulo estende o assembler 6502 original para suportar:
- Macros: Blocos de código reutilizáveis
- Diretivas condicionais: Compilação condicional (.if, .ifdef, .ifndef, .else, .endif)
- Inclusão de arquivos: Incluir código de outros arquivos (.include)
"""

import os
import sys
import argparse
import logging
from typing import List, Optional

from assembler_6502_fixed_final import Assembler
from macro_processor import MacroProcessor

class ExtendedAssembler:
    """Assembler 6502 estendido com suporte a macros e diretivas condicionais."""
    
    def __init__(self, debug=False):
        """
        Inicializa o assembler estendido.
        
        Args:
            debug: Se True, habilita mensagens de depuração
        """
        self.assembler = Assembler()
        self.macro_processor = MacroProcessor()
        self.debug = debug
        
        # Configuração de logging
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def assemble_file(self, input_file: str, output_file: Optional[str] = None) -> bytes:
        """
        Monta um arquivo assembly, processando macros e diretivas condicionais.
        
        Args:
            input_file: Caminho do arquivo de entrada
            output_file: Caminho do arquivo de saída (opcional)
        
        Returns:
            Código binário gerado
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Processa macros e diretivas condicionais
        self.logger.info(f"Processing macros and conditionals in {input_file}")
        processed_lines = self.macro_processor.process_file(input_file)
        
        # Junta as linhas processadas em um único texto
        processed_source = "\n".join(processed_lines)
        
        # Monta o código processado
        self.logger.info("Assembling processed code")
        binary = self.assembler.assemble(processed_source)
        
        # Salva o código binário se um arquivo de saída for especificado
        if output_file and binary:
            with open(output_file, 'wb') as f:
                f.write(binary)
            self.logger.info(f"Binary code written to {output_file}")
        
        return binary
    
    def assemble_string(self, source_code: str) -> bytes:
        """
        Monta um código assembly a partir de uma string, processando macros e diretivas condicionais.
        
        Args:
            source_code: Código fonte assembly
        
        Returns:
            Código binário gerado
        """
        # Divide o código em linhas
        lines = source_code.splitlines()
        
        # Processa macros e diretivas condicionais
        self.logger.info("Processing macros and conditionals")
        processed_lines = self.macro_processor.process_lines(lines)
        
        # Junta as linhas processadas em um único texto
        processed_source = "\n".join(processed_lines)
        
        # Monta o código processado
        self.logger.info("Assembling processed code")
        return self.assembler.assemble(processed_source)

def main():
    """Função principal para execução via linha de comando."""
    parser = argparse.ArgumentParser(description='6502 Assembler with Macro Support')
    parser.add_argument('input_file', help='Input assembly file')
    parser.add_argument('output_file', nargs='?', help='Output binary file')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--preprocess', action='store_true', help='Only preprocess, do not assemble')
    parser.add_argument('--preprocess-output', help='Output file for preprocessed code')
    
    args = parser.parse_args()
    
    try:
        assembler = ExtendedAssembler(debug=args.debug)
        
        if args.preprocess:
            # Apenas pré-processa o código
            processor = MacroProcessor()
            processed_lines = processor.process_file(args.input_file)
            processed_source = "\n".join(processed_lines)
            
            if args.preprocess_output:
                with open(args.preprocess_output, 'w') as f:
                    f.write(processed_source)
                print(f"Preprocessed code written to {args.preprocess_output}")
            else:
                print(processed_source)
        else:
            # Monta o código
            binary = assembler.assemble_file(args.input_file, args.output_file)
            
            if binary:
                print(f"Assembly successful: {len(binary)} bytes generated")
                
                if not args.output_file:
                    # Se nenhum arquivo de saída foi especificado, exibe os primeiros bytes
                    print("First 16 bytes:", end=" ")
                    for i in range(min(16, len(binary))):
                        print(f"${binary[i]:02X}", end=" ")
                    print()
            else:
                print("Assembly failed")
                sys.exit(1)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
