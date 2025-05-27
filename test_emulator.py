#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar o emulador 6502 com o programa de teste de branch e comparação.
"""

import sys
import os
from Cpu import CPU, Bus

def carregar_programa(bus, arquivo_asm, endereco_inicial=0x8000):
    """
    Carrega um programa assembly no barramento de memória.
    
    Args:
        bus: O barramento de memória
        arquivo_asm: O arquivo assembly a ser carregado
        endereco_inicial: O endereço inicial onde o programa será carregado
    """
    # Verifica se o arquivo existe
    if not os.path.exists(arquivo_asm):
        print(f"Erro: Arquivo {arquivo_asm} não encontrado.")
        return False
    
    # Lê o conteúdo do arquivo
    with open(arquivo_asm, 'r') as f:
        linhas = f.readlines()
    
    # Processa o arquivo para extrair o código de máquina
    endereco = endereco_inicial
    for linha in linhas:
        linha = linha.strip()
        
        # Ignora linhas vazias e comentários
        if not linha or linha.startswith(';') or linha.startswith('#'):
            continue
        
        # Processa diretivas e instruções
        if linha.startswith('.org'):
            # Extrai o endereço da diretiva .org
            try:
                endereco_str = linha.split()[1]
                if endereco_str.startswith('$'):
                    endereco = int(endereco_str[1:], 16)
                else:
                    endereco = int(endereco_str)
            except (IndexError, ValueError):
                print(f"Erro ao processar diretiva .org: {linha}")
                continue
        elif linha.startswith('.equ'):
            # Ignora diretivas .equ para este teste simples
            continue
        elif ':' in linha:
            # Ignora labels
            continue
        else:
            # Processa instruções
            partes = linha.split(';')[0].strip().split()
            if not partes:
                continue
            
            instrucao = partes[0].upper()
            
            # Mapeamento simplificado de instruções para opcodes
            # Apenas para fins de teste
            if instrucao == 'LDA' and '#' in partes[1]:
                # LDA imediato
                valor = partes[1].replace('#', '').replace('$', '')
                if valor.startswith('$'):
                    valor = int(valor[1:], 16)
                elif valor.isdigit():
                    valor = int(valor)
                else: 
                    # Assume que é um valor hexadecimal
                    try:
                        valor = int(valor, 16)
                    except ValueError:
                        print(f"Erro: Valor inválido: {valor}")
                        continue
                bus.ram[endereco] = 0xA9  # Opcode LDA imediato
                bus.ram[endereco + 1] = valor & 0xFF
                endereco += 2
            elif instrucao == 'STA' and not '#' in partes[1]:
                # STA absoluto
                endereco_alvo = partes[1]
                if '+' in endereco_alvo:
                    # Endereço com offset (ex: TEST_RESULT+1)
                    base, offset = endereco_alvo.split('+')
                    if base == 'TEST_RESULT':
                        endereco_alvo = 0x0200 + int(offset)
                    else:
                        endereco_alvo = int(base.replace('$', ''), 16) + int(offset)
                elif endereco_alvo == 'TEST_RESULT':
                    endereco_alvo = 0x0200
                elif endereco_alvo.startswith('$'):
                    endereco_alvo = int(endereco_alvo[1:], 16)
                else:
                    endereco_alvo = int(endereco_alvo)
                
                bus.ram[endereco] = 0x8D  # Opcode STA absoluto
                bus.ram[endereco + 1] = endereco_alvo & 0xFF
                bus.ram[endereco + 2] = (endereco_alvo >> 8) & 0xFF
                endereco += 3
            elif instrucao == 'LDX' and '#' in partes[1]:
                # LDX imediato
                valor = partes[1].replace('#', '').replace('$', '')
                if valor.startswith('$'):
                    valor = int(valor[1:], 16)
                else:
                    valor = int(valor)
                bus.ram[endereco] = 0xA2  # Opcode LDX imediato
                bus.ram[endereco + 1] = valor & 0xFF
                endereco += 2
            elif instrucao == 'LDY' and '#' in partes[1]:
                # LDY imediato
                valor = partes[1].replace('#', '').replace('$', '')
                if valor.startswith('$'):
                    valor = int(valor[1:], 16)
                else:
                    valor = int(valor)
                bus.ram[endereco] = 0xA0  # Opcode LDY imediato
                bus.ram[endereco + 1] = valor & 0xFF
                endereco += 2
            elif instrucao == 'CMP' and '#' in partes[1]:
                # CMP imediato
                valor = partes[1].replace('#', '').replace('$', '')
                if valor.startswith('$'):
                    valor = int(valor[1:], 16)
                else:
                    valor = int(valor)
                bus.ram[endereco] = 0xC9  # Opcode CMP imediato
                bus.ram[endereco + 1] = valor & 0xFF
                endereco += 2
            elif instrucao == 'CPX' and '#' in partes[1]:
                # CPX imediato
                valor = partes[1].replace('#', '').replace('$', '')
                if valor.startswith('$'):
                    valor = int(valor[1:], 16)
                else:
                    valor = int(valor)
                bus.ram[endereco] = 0xE0  # Opcode CPX imediato
                bus.ram[endereco + 1] = valor & 0xFF
                endereco += 2
            elif instrucao == 'CPY' and '#' in partes[1]:
                # CPY imediato
                valor = partes[1].replace('#', '').replace('$', '')
                if valor.startswith('$'):
                    valor = int(valor[1:], 16)
                else:
                    valor = int(valor)
                bus.ram[endereco] = 0xC0  # Opcode CPY imediato
                bus.ram[endereco + 1] = valor & 0xFF
                endereco += 2
            elif instrucao == 'BIT' and '#' in partes[1]:
                # BIT imediato (não oficial, mas usado no teste)
                valor = partes[1].replace('#', '').replace('$', '')
                if valor.startswith('$'):
                    valor = int(valor[1:], 16)
                else:
                    valor = int(valor)
                bus.ram[endereco] = 0x89  # Opcode BIT imediato (não oficial)
                bus.ram[endereco + 1] = valor & 0xFF
                endereco += 2
            elif instrucao == 'JMP':
                # JMP absoluto
                label = partes[1]
                # Para simplificar, vamos apenas colocar um JMP para o próximo endereço
                # Em um assembler real, resolveríamos os labels
                bus.ram[endereco] = 0x4C  # Opcode JMP absoluto
                bus.ram[endereco + 1] = (endereco + 3) & 0xFF
                bus.ram[endereco + 2] = ((endereco + 3) >> 8) & 0xFF
                endereco += 3
            elif instrucao == 'BNE':
                # BNE relativo
                bus.ram[endereco] = 0xD0  # Opcode BNE
                bus.ram[endereco + 1] = 0x02  # Offset de 2 bytes (pula para a próxima instrução)
                endereco += 2
            elif instrucao == 'BEQ':
                # BEQ relativo
                bus.ram[endereco] = 0xF0  # Opcode BEQ
                bus.ram[endereco + 1] = 0x02  # Offset de 2 bytes
                endereco += 2
            elif instrucao == 'BCC':
                # BCC relativo
                bus.ram[endereco] = 0x90  # Opcode BCC
                bus.ram[endereco + 1] = 0x02  # Offset de 2 bytes
                endereco += 2
            elif instrucao == 'BCS':
                # BCS relativo
                bus.ram[endereco] = 0xB0  # Opcode BCS
                bus.ram[endereco + 1] = 0x02  # Offset de 2 bytes
                endereco += 2
            elif instrucao == 'BMI':
                # BMI relativo
                bus.ram[endereco] = 0x30  # Opcode BMI
                bus.ram[endereco + 1] = 0x02  # Offset de 2 bytes
                endereco += 2
            elif instrucao == 'BPL':
                # BPL relativo
                bus.ram[endereco] = 0x10  # Opcode BPL
                bus.ram[endereco + 1] = 0x02  # Offset de 2 bytes
                endereco += 2
            elif instrucao == 'BVC':
                # BVC relativo
                bus.ram[endereco] = 0x50  # Opcode BVC
                bus.ram[endereco + 1] = 0x02  # Offset de 2 bytes
                endereco += 2
            elif instrucao == 'BVS':
                # BVS relativo
                bus.ram[endereco] = 0x70  # Opcode BVS
                bus.ram[endereco + 1] = 0x02  # Offset de 2 bytes
                endereco += 2
            elif instrucao == 'CLC':
                # CLC implícito
                bus.ram[endereco] = 0x18  # Opcode CLC
                endereco += 1
            elif instrucao == 'SEC':
                # SEC implícito
                bus.ram[endereco] = 0x38  # Opcode SEC
                endereco += 1
            elif instrucao == 'CLV':
                # CLV implícito
                bus.ram[endereco] = 0xB8  # Opcode CLV
                endereco += 1
            elif instrucao == 'ADC' and '#' in partes[1]:
                # ADC imediato
                valor = partes[1].replace('#', '').replace('$', '')
                if valor.startswith('$'):
                    valor = int(valor[1:], 16)
                else:
                    valor = int(valor)
                bus.ram[endereco] = 0x69  # Opcode ADC imediato
                bus.ram[endereco + 1] = valor & 0xFF
                endereco += 2
            elif instrucao == 'BRK':
                # BRK implícito
                bus.ram[endereco] = 0x00  # Opcode BRK
                endereco += 1
    
    # Programa carregado com sucesso
    return True

def executar_teste():
    """
    Executa o teste do emulador com o programa de teste de branch e comparação.
    """
    # Cria o barramento e a CPU
    bus = Bus()
    cpu = CPU(bus)
    
    # Carrega o programa de teste
    print("Carregando programa de teste...")
    if not carregar_programa(bus, "test_branch_instructions.asm"):
        print("Falha ao carregar o programa de teste.")
        return
    
    # Configura o vetor de reset para apontar para o início do programa
    bus.ram[0xFFFC] = 0x00
    bus.ram[0xFFFD] = 0x80  # $8000
    
    # Reseta a CPU
    print("Resetando CPU...")
    cpu.reset()
    
    # Executa o programa
    print("Executando programa de teste...")
    ciclos_max = 1000
    ciclos_executados = 0
    
    while ciclos_executados < ciclos_max:
        # Executa um ciclo da CPU
        ciclos = cpu.clock()
        ciclos_executados += ciclos
        
        # Verifica se chegou ao final do programa (BRK)
        if bus.ram[cpu.regs.pc] == 0x00:  # Opcode BRK
            print(f"Programa finalizado após {ciclos_executados} ciclos.")
            break
    
    # Verifica os resultados dos testes
    print("\nResultados dos testes:")
    for i in range(12):
        resultado = bus.ram[0x0200 + i]
        if resultado == 0xAA:
            print(f"Teste {i+1}: PASSOU (0x{resultado:02X})")
        else:
            print(f"Teste {i+1}: FALHOU (0x{resultado:02X})")
    
    # Exibe o estado final da CPU
    print("\nEstado final da CPU:")
    print(f"A: 0x{cpu.regs.a:02X}")
    print(f"X: 0x{cpu.regs.x:02X}")
    print(f"Y: 0x{cpu.regs.y:02X}")
    print(f"PC: 0x{cpu.regs.pc:04X}")
    print(f"SP: 0x{cpu.regs.sp:02X}")
    print(f"Flags: N={cpu.regs.n} V={cpu.regs.v} B={cpu.regs.b} D={cpu.regs.d} I={cpu.regs.i} Z={cpu.regs.z} C={cpu.regs.c}")

if __name__ == "__main__":
    executar_teste()
