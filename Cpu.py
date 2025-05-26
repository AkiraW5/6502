# -*- coding: utf-8 -*-
"""
Emulador do microprocessador MOS 6502 em Python.

Este módulo contém as classes para simular os Registradores (`Registers`),
o Barramento de Memória (`Bus`) e a Unidade Central de Processamento (`CPU`).
O objetivo é fornecer uma simulação funcional básica da arquitetura 6502.
"""

import logging

# Configuração do logging para exibir informações durante a execução
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        self.sp = 0xFD # Ponteiro de Pilha (Stack Pointer)
        
        # Contador de Programa (Program Counter) de 16 bits
        self.pc = 0x0000

        # Registrador de Status (P) - Flags representadas como atributos individuais
        self.c = 0 # Carry Flag (Bit 0)
        self.z = 0 # Zero Flag (Bit 1)
        self.i = 1 # Interrupt Disable Flag (Bit 2)
        self.d = 0 # Decimal Mode Flag (Bit 3) - Não suportado funcionalmente neste emulador
        self.b = 0 # Break Command Flag (Bit 4) - Usado ao empilhar durante BRK/IRQ/NMI
        self.u = 1 # Unused Flag (Bit 5) - Sempre 1
        self.v = 0 # Overflow Flag (Bit 6)
        self.n = 0 # Negative Flag (Bit 7)

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
             b_flag_val = 1 # B é 1 quando empurrado por PHP, BRK, IRQ, NMI

        return (
            (self.n << 7) |
            (self.v << 6) |
            (1 << 5) | # Flag U (Unused) é sempre 1
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
        address &= 0xFFFF # Garante que o endereço esteja dentro do espaço de 16 bits
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
        high_byte = self.read((address + 1) & 0xFFFF) # Garante wrap-around se ler em 0xFFFF
        return (high_byte << 8) | low_byte

    def write(self, address, value):
        """Escreve um byte na memória no endereço especificado.

        Args:
            address (int): O endereço de 16 bits para escrita.
            value (int): O valor do byte (0-255) a ser escrito.
        """
        address &= 0xFFFF
        value &= 0xFF # Garante que o valor seja um byte
        # TODO: Implementar mapeamento de memória para escrita.
        self.ram[address] = value

class CPU:
    """Representa a unidade central de processamento (CPU) MOS 6502."""
    def __init__(self, bus):
        """Inicializa a CPU, conectando-a ao barramento fornecido.

        Args:
            bus (Bus): A instância do barramento de memória a ser usada pela CPU.
        """
        self.bus = bus # Usa o barramento passado, não cria um novo
        self.regs = Registers()
        self.halted = False
        self.cycles = 0 # Contador de ciclos para a instrução *atual*
        self.total_cycles = 0 # Contador de ciclos *total* desde o reset

        # Tabela de Lookup: Mapeia cada opcode (0-255) para uma tupla:
        # (função_da_instrução, função_do_modo_de_endereçamento, ciclos_base)
        self.lookup = self._build_lookup_table()

    def _build_lookup_table(self):
        """Constrói e retorna a tabela de lookup para decodificação rápida de opcodes."""
        # Inicializa a tabela com uma instrução ilegal padrão (XXX)
        # Isso garante que opcodes não mapeados sejam tratados.
        table = [(self.XXX, self.IMP, 2)] * 256

        # Mapeamento das instruções implementadas
        # Formato: table[OPCODE] = (self.NOME_INSTRUCAO, self.MODO_ENDEREÇAMENTO, CICLOS_BASE)
        # Ciclos base podem ser ajustados por ciclos adicionais (ex: cruzamento de página)

        # --- Instruções de Carga (Load) ---
        table[0xA9] = (self.LDA, self.IMM, 2); table[0xA5] = (self.LDA, self.ZP0, 3)
        table[0xB5] = (self.LDA, self.ZPX, 4); table[0xAD] = (self.LDA, self.ABS, 4)
        table[0xBD] = (self.LDA, self.ABX, 4); table[0xB9] = (self.LDA, self.ABY, 4)
        table[0xA1] = (self.LDA, self.IZX, 6); table[0xB1] = (self.LDA, self.IZY, 5)
        table[0xA2] = (self.LDX, self.IMM, 2); table[0xA6] = (self.LDX, self.ZP0, 3)
        table[0xB6] = (self.LDX, self.ZPY, 4); table[0xAE] = (self.LDX, self.ABS, 4)
        table[0xBE] = (self.LDX, self.ABY, 4)
        table[0xA0] = (self.LDY, self.IMM, 2); table[0xA4] = (self.LDY, self.ZP0, 3)
        table[0xB4] = (self.LDY, self.ZPX, 4); table[0xAC] = (self.LDY, self.ABS, 4)
        table[0xBC] = (self.LDY, self.ABX, 4)

        # --- Instruções de Armazenamento (Store) ---
        table[0x85] = (self.STA, self.ZP0, 3); table[0x95] = (self.STA, self.ZPX, 4)
        table[0x8D] = (self.STA, self.ABS, 4); table[0x9D] = (self.STA, self.ABX, 5)
        table[0x99] = (self.STA, self.ABY, 5); table[0x81] = (self.STA, self.IZX, 6)
        table[0x91] = (self.STA, self.IZY, 6)
        table[0x86] = (self.STX, self.ZP0, 3); table[0x96] = (self.STX, self.ZPY, 4)
        table[0x8E] = (self.STX, self.ABS, 4)
        table[0x84] = (self.STY, self.ZP0, 3); table[0x94] = (self.STY, self.ZPX, 4)
        table[0x8C] = (self.STY, self.ABS, 4)

        # --- Instruções Aritméticas ---
        table[0x69] = (self.ADC, self.IMM, 2); table[0x65] = (self.ADC, self.ZP0, 3)
        table[0x75] = (self.ADC, self.ZPX, 4); table[0x6D] = (self.ADC, self.ABS, 4)
        table[0x7D] = (self.ADC, self.ABX, 4); table[0x79] = (self.ADC, self.ABY, 4)
        table[0x61] = (self.ADC, self.IZX, 6); table[0x71] = (self.ADC, self.IZY, 5)
        # TODO: Implementar SBC (Subtract with Carry)

        # --- Instruções Lógicas ---
        table[0x29] = (self.AND, self.IMM, 2); table[0x25] = (self.AND, self.ZP0, 3)
        table[0x35] = (self.AND, self.ZPX, 4); table[0x2D] = (self.AND, self.ABS, 4)
        table[0x3D] = (self.AND, self.ABX, 4); table[0x39] = (self.AND, self.ABY, 4)
        table[0x21] = (self.AND, self.IZX, 6); table[0x31] = (self.AND, self.IZY, 5)
        # TODO: Implementar EOR (Exclusive OR)
        # TODO: Implementar ORA (Logical OR)

        # --- Instruções de Deslocamento e Rotação ---
        table[0x0A] = (self.ASL, self.ACC, 2); table[0x06] = (self.ASL, self.ZP0, 5)
        table[0x16] = (self.ASL, self.ZPX, 6); table[0x0E] = (self.ASL, self.ABS, 6)
        table[0x1E] = (self.ASL, self.ABX, 7)
        # TODO: Implementar LSR (Logical Shift Right)
        # TODO: Implementar ROL (Rotate Left)
        # TODO: Implementar ROR (Rotate Right)

        # --- Instruções de Incremento e Decremento ---
        table[0xE6] = (self.INC, self.ZP0, 5); table[0xF6] = (self.INC, self.ZPX, 6)
        table[0xEE] = (self.INC, self.ABS, 6); table[0xFE] = (self.INC, self.ABX, 7)
        table[0xC6] = (self.DEC, self.ZP0, 5); table[0xD6] = (self.DEC, self.ZPX, 6)
        table[0xCE] = (self.DEC, self.ABS, 6); table[0xDE] = (self.DEC, self.ABX, 7)
        table[0xE8] = (self.INX, self.IMP, 2); table[0xC8] = (self.INY, self.IMP, 2)
        table[0xCA] = (self.DEX, self.IMP, 2); table[0x88] = (self.DEY, self.IMP, 2)

        # --- Instruções de Pilha (Stack) ---
        table[0x48] = (self.PHA, self.IMP, 3); table[0x68] = (self.PLA, self.IMP, 4)
        table[0x08] = (self.PHP, self.IMP, 3); table[0x28] = (self.PLP, self.IMP, 4)

        # --- Instruções de Salto (Jump) e Sub-rotina ---
        table[0x4C] = (self.JMP, self.ABS, 3); table[0x6C] = (self.JMP, self.IND, 5)
        table[0x20] = (self.JSR, self.ABS, 6)
        table[0x60] = (self.RTS, self.IMP, 6)
        table[0x40] = (self.RTI, self.IMP, 6)

        # --- Instruções de Desvio Condicional (Branch) ---
        # TODO: Implementar BCC, BCS, BEQ, BMI, BNE, BPL, BVC, BVS

        # --- Instruções de Comparação ---
        # TODO: Implementar CMP, CPX, CPY
        # TODO: Implementar BIT

        # --- Instruções de Transferência entre Registradores ---
        table[0xAA] = (self.TAX, self.IMP, 2); table[0x8A] = (self.TXA, self.IMP, 2)
        table[0xA8] = (self.TAY, self.IMP, 2); table[0x98] = (self.TYA, self.IMP, 2)
        table[0xBA] = (self.TSX, self.IMP, 2); table[0x9A] = (self.TXS, self.IMP, 2)

        # --- Instruções de Manipulação de Flags ---
        table[0x18] = (self.CLC, self.IMP, 2); table[0x38] = (self.SEC, self.IMP, 2)
        table[0x58] = (self.CLI, self.IMP, 2); table[0x78] = (self.SEI, self.IMP, 2)
        table[0xD8] = (self.CLD, self.IMP, 2); table[0xF8] = (self.SED, self.IMP, 2)
        table[0xB8] = (self.CLV, self.IMP, 2)

        # --- Outras Instruções ---
        table[0x00] = (self.BRK, self.IMP, 7) # Break / Interrupt
        table[0xEA] = (self.NOP, self.IMP, 2) # No Operation
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
        self.regs.sp = (self.regs.sp - 1) & 0xFF # SP wraps around from 0x00 to 0xFF

    def push_word(self, value):
        """Empilha uma palavra (16 bits) na pilha, byte mais significativo primeiro."""
        self.push_byte((value >> 8) & 0xFF) # High byte
        self.push_byte(value & 0xFF)        # Low byte

    def pop_byte(self):
        """Incrementa SP e desempilha um byte da pilha."""
        self.regs.sp = (self.regs.sp + 1) & 0xFF # SP wraps around from 0xFF to 0x00
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
        self.regs.pc = (self.regs.pc + 1) & 0xFFFF # PC wraps around
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

    def IMP(self): # Implied
        """Modo Implícito: Operando está implícito na instrução."""
        return 0, False

    def ACC(self): # Accumulator
        """Modo Acumulador: Operando é o registrador Acumulador."""
        return 0, False

    def IMM(self): # Immediate
        """Modo Imediato: Operando é o byte seguinte ao opcode."""
        addr = self.regs.pc
        self.regs.pc = (self.regs.pc + 1) & 0xFFFF
        return addr, False

    def ZP0(self): # Zero Page
        """Modo Página Zero: Operando é um endereço de 8 bits (0x00xx)."""
        addr = self.fetch_byte() & 0x00FF
        return addr, False

    def ZPX(self): # Zero Page, X
        """Modo Página Zero, Indexado com X: Endereço = byte + X (com wrap na página zero)."""
        addr = (self.fetch_byte() + self.regs.x) & 0x00FF
        return addr, False

    def ZPY(self): # Zero Page, Y
        """Modo Página Zero, Indexado com Y: Endereço = byte + Y (com wrap na página zero)."""
        # Usado apenas por LDX e STX
        addr = (self.fetch_byte() + self.regs.y) & 0x00FF
        return addr, False

    def ABS(self): # Absolute
        """Modo Absoluto: Operando é um endereço completo de 16 bits."""
        addr = self.fetch_word()
        return addr, False

    def ABX(self): # Absolute, X
        """Modo Absoluto, Indexado com X: Endereço = word + X."""
        base_addr = self.fetch_word()
        addr = (base_addr + self.regs.x) & 0xFFFF
        page_crossed = (base_addr & 0xFF00) != (addr & 0xFF00)
        return addr, page_crossed

    def ABY(self): # Absolute, Y
        """Modo Absoluto, Indexado com Y: Endereço = word + Y."""
        base_addr = self.fetch_word()
        addr = (base_addr + self.regs.y) & 0xFFFF
        page_crossed = (base_addr & 0xFF00) != (addr & 0xFF00)
        return addr, page_crossed

    def IND(self): # Indirect (Apenas para JMP)
        """Modo Indireto: Lê o endereço de destino de outro endereço na memória.
           Simula o bug de hardware do 6502 ao cruzar páginas no ponteiro.
        """
        ptr_addr = self.fetch_word()
        # Simula o bug: se o byte baixo do ponteiro é 0xFF, o byte alto é lido
        # da mesma página, não da página seguinte.
        if (ptr_addr & 0x00FF) == 0x00FF:
            low_byte = self.read(ptr_addr)
            high_byte = self.read(ptr_addr & 0xFF00) # Bug: lê do início da mesma página (ex: $xxFF -> lê $xxFF e $xx00)
        else:
            low_byte = self.read(ptr_addr)
            high_byte = self.read(ptr_addr + 1)
        addr = (high_byte << 8) | low_byte
        return addr, False

    def IZX(self): # Indirect, X (Indexed Indirect)
        """Modo Indireto Indexado com X: Endereço = word[byte + X]."""
        base_ptr = self.fetch_byte()
        ptr_addr = (base_ptr + self.regs.x) & 0x00FF # Endereço do ponteiro na página zero
        # Lê o endereço final (little-endian) da página zero
        low_byte = self.read(ptr_addr)
        high_byte = self.read((ptr_addr + 1) & 0x00FF) # Wrap around na página zero
        addr = (high_byte << 8) | low_byte
        return addr, False

    def IZY(self): # Indirect, Y (Indirect Indexed)
        """Modo Indireto Indexado com Y: Endereço = word[byte] + Y."""
        ptr_addr = self.fetch_byte() & 0x00FF # Endereço do ponteiro na página zero
        # Lê o endereço base (little-endian) da página zero
        low_byte = self.read(ptr_addr)
        high_byte = self.read((ptr_addr + 1) & 0x00FF) # Wrap around na página zero
        base_addr = (high_byte << 8) | low_byte
        # Adiciona Y ao endereço base
        addr = (base_addr + self.regs.y) & 0xFFFF
        page_crossed = (base_addr & 0xFF00) != (addr & 0xFF00)
        return addr, page_crossed

    def REL(self): # Relative (Para Branches)
        """Modo Relativo: Operando é um offset de 8 bits com sinal relativo ao PC."""
        offset = self.fetch_byte()
        # Converte para offset com sinal (complemento de dois)
        if offset & 0x80:
            offset = offset - 0x100
        # Retorna o offset. O cálculo do endereço final é feito na instrução de branch.
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
        if addr_mode_func == self.ACC: # Modo Acumulador
            return self.regs.a, False
        elif addr_mode_func == self.IMM: # Modo Imediato
            addr, page_crossed = addr_mode_func()
            return self.read(addr), page_crossed
        elif addr_mode_func == self.IMP or addr_mode_func == self.REL:
             # Modos Implícito e Relativo não têm operando de memória neste sentido
             # REL retorna offset, IMP não retorna nada útil aqui.
             # A função do modo já foi chamada para avançar o PC se necessário (IMM, ZP0, etc.)
             # ou para obter o offset (REL).
             # Chamamos novamente para obter page_crossed (geralmente False aqui)
             _, page_crossed = addr_mode_func()
             return 0, page_crossed # Retorna 0 como placeholder
        else: # Outros modos (ZP, ABS, IZX, IZY, etc.) que retornam endereço efetivo
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
        self.regs.c = 1 if temp > 0xFF else 0 # Carry
        self.regs.update_flag_z(temp)          # Zero
        # Overflow (V): Ocorre se o sinal do resultado for diferente do sinal de ambos os operandos
        # (considerando A e operando como números com sinal de 8 bits)
        # Simplificação: (~(A ^ operand) & (A ^ result)) & 0x80
        self.regs.v = 1 if (~(self.regs.a ^ operand) & (self.regs.a ^ temp)) & 0x80 else 0
        self.regs.update_flag_n(temp)          # Negative
        
        # Armazena o resultado de 8 bits no acumulador
        self.regs.a = temp & 0xFF
        # Retorna ciclo adicional se a página foi cruzada no cálculo do endereço
        return 1 if page_crossed else 0

    # TODO: Implementar SBC

    # --- Instruções Lógicas ---
    def AND(self, addr_mode_func):
        """Instrução AND: Logical AND (Acumulador E Operando)."""
        operand, page_crossed = self.fetch_operand(addr_mode_func)
        self.regs.a &= operand
        self.regs.update_flag_z(self.regs.a)
        self.regs.update_flag_n(self.regs.a)
        return 1 if page_crossed else 0

    # TODO: Implementar EOR, ORA

    # --- Instruções de Deslocamento e Rotação ---
    def ASL(self, addr_mode_func):
        """Instrução ASL: Arithmetic Shift Left (Desloca bits para a esquerda)."""
        if addr_mode_func == self.ACC:
            operand = self.regs.a
            self.regs.c = 1 if (operand & 0x80) else 0 # Bit 7 vai para o Carry
            result = (operand << 1) & 0xFF
            self.regs.a = result
            self.regs.update_flag_z(result)
            self.regs.update_flag_n(result)
            return 0 # Sem ciclos adicionais
        else:
            addr, _ = addr_mode_func() # Não há page crossed penalty para ASL memória
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
        # 1. Fetch the target address using the mode function (ABS).
        #    This advances PC past the JSR instruction (PC is now at the next instruction).
        target_addr, _ = addr_mode_func() # addr_mode_func is self.ABS

        # 2. Calculate the return address to push. It's the address of the
        #    last byte of the JSR instruction (PC - 1).
        return_addr = (self.regs.pc - 1) & 0xFFFF

        # 3. Push the return address onto the stack.
        self.push_word(return_addr)

        # 4. Set PC to the target address.
        self.regs.pc = target_addr
        return 0 # JSR ABS always takes 6 cycles, no extra cycles.

    # CORREÇÃO: Usando pop_word helper para RTS
    def RTS(self, addr_mode_func):
        """Instrução RTS: Return from Subroutine (Retorna da sub-rotina)."""
        # Pop the address pushed by JSR
        pushed_addr = self.pop_word() # Pops low then high byte
        # Set PC to the address after the JSR instruction
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
        # Verificamos se o modo pode cruzar página e adicionamos ciclo se necessário.
        _, page_crossed = addr_mode_func() # Chama a função do modo para avançar PC e checar página
        # Apenas modos como ABX podem ter ciclo extra em NOPs não oficiais
        if addr_mode_func in [self.ABX]: # Adicionar outros modos se mapear NOPs não oficiais
             return 1 if page_crossed else 0
        return 0

    def XXX(self, addr_mode_func):
        """Instrução XXX: Placeholder para Opcodes Ilegais/Não Implementados."""
        # Obtém o endereço onde o opcode foi lido (PC já avançou)
        opcode_addr = (self.regs.pc - 1) & 0xFFFF
        opcode = self.read(opcode_addr)
        logging.error(f"Opcode ILEGAL/NÃO IMPLEMENTADO encontrado: {opcode:02X} no endereço {opcode_addr:04X}")
        # Considerar parar a execução ou apenas logar.
        self.halted = True 
        return 0

    # --- Ciclo Principal da CPU e Tratamento de Interrupções ---
    def clock(self):
        """Executa um ciclo de instrução completo da CPU.
        
        Busca o opcode, decodifica, executa a instrução e calcula os ciclos.
        Também verifica por interrupções (NMI, IRQ) antes de cada instrução.
        """
        if self.halted:
            return

        # --- Verificação de Interrupções (NMI tem prioridade sobre IRQ) ---
        # TODO: Implementar lógica de NMI (edge-triggered) e IRQ (level-triggered)
        #       Por enquanto, chamadas manuais a self.nmi() e self.irq() funcionam.

        # --- Ciclo de Instrução ---
        # Guarda o PC no início do ciclo para logging/debugging
        pc_start = self.regs.pc

        # 1. Fetch: Lê o opcode da memória
        opcode = self.fetch_byte()
        
        # Reseta o contador de ciclos para esta instrução
        self.cycles = 0

        # 2. Decode: Obtém a função da instrução, modo de endereçamento e ciclos base
        instruction_func, addr_mode_func, base_cycles = self.lookup[opcode]
        
        self.cycles += base_cycles

        # 3. Execute: Chama a função da instrução, passando a função do modo de endereçamento.
        # A função da instrução internamente chamará a função do modo de endereçamento
        # para obter o endereço/operando e calcular ciclos adicionais (page cross, branch taken).
        additional_cycles = instruction_func(addr_mode_func)
        self.cycles += additional_cycles

        # Atualiza o contador total de ciclos
        self.total_cycles += self.cycles

        # Log (opcional, pode ser útil para debugging)
        # self._log_state(pc_start, opcode)

    def reset(self):
        """Simula o sinal de RESET da CPU.
        
        Lê o vetor de reset (0xFFFC/FD), define o PC, reseta registradores e flags,
        e consome os ciclos apropriados.
        """
        logging.info("--- CPU RESET --- ")
        # Lê o endereço inicial do vetor de reset
        self.regs.pc = self.bus.read_word(0xFFFC)

        # Reseta registradores para estado conhecido
        self.regs.a = 0
        self.regs.x = 0
        self.regs.y = 0
        self.regs.sp = 0xFD # Reset do Stack Pointer (padrão)
        
        # Reseta flags (I=1, U=1, B=0, D=0, outras=0)
        self.regs.set_status_byte(0x00 | (1 << 5) | (1 << 2)) # U=1, I=1

        self.halted = False
        # Reset consome 8 ciclos (documentado em várias fontes)
        self.cycles = 8
        self.total_cycles = 0 # Zera contador total no reset

    def irq(self):
        """Simula uma Requisição de Interrupção (IRQ).
        
        Só ocorre se a flag I (Interrupt Disable) estiver 0.
        Empilha PC e Status, seta I=1, e carrega PC do vetor IRQ (0xFFFE/FF).
        """
        if self.regs.i == 0: # Verifica se interrupções estão habilitadas
            logging.info("--- IRQ --- ")
            # Empilha PC (endereço da *próxima* instrução a ser executada)
            self.push_word(self.regs.pc)
            
            # Empilha Status Register (com B=0, U=1)
            # A flag B interna não muda, mas é 1 no valor empilhado.
            self.push_byte(self.regs.get_status_byte(pushing=True))
            
            # Seta a flag I para desabilitar novas IRQs
            self.regs.i = 1
            
            # Carrega PC do vetor de IRQ/BRK
            self.regs.pc = self.bus.read_word(0xFFFE)
            
            # IRQ consome 7 ciclos
            self.cycles = 7
            self.total_cycles += self.cycles
        else:
            logging.debug("IRQ ignorada (I=1)")

    def nmi(self):
        """Simula uma Interrupção Não-Mascarável (NMI).
        
        Ocorre independentemente da flag I.
        Empilha PC e Status, seta I=1, e carrega PC do vetor NMI (0xFFFA/FB).
        """
        logging.info("--- NMI --- ")
        # Empilha PC (endereço da *próxima* instrução a ser executada)
        self.push_word(self.regs.pc)
        
        # Empilha Status Register (com B=0, U=1)
        # A flag B interna não muda, mas é 1 no valor empilhado.
        self.push_byte(self.regs.get_status_byte(pushing=True))
        
        # Seta a flag I (mesmo que NMI não seja mascarável, o handler pode ser interrompido por outra NMI)
        self.regs.i = 1
        
        # Carrega PC do vetor de NMI
        self.regs.pc = self.bus.read_word(0xFFFA)
        
        # NMI consome 8 ciclos
        self.cycles = 8
        self.total_cycles += self.cycles

    # --- Funções Auxiliares de Debugging e Controle ---
    def load_program(self, program_bytes, start_address):
        """Carrega um programa (lista/bytearray de bytes) na memória do barramento.

        Args:
            program_bytes: Sequência de bytes do programa.
            start_address (int): Endereço inicial onde carregar o programa.
        """
        offset = 0
        for byte in program_bytes:
            self.write(start_address + offset, byte)
            offset += 1
        end_address = start_address + offset - 1
        logging.info(f"Programa ({offset} bytes) carregado de {start_address:04X} a {end_address:04X}")

    def set_reset_vector(self, address):
        """Define o endereço no vetor de reset (0xFFFC/FD) na memória.

        Args:
            address (int): O endereço de 16 bits para onde a CPU deve pular no reset.
        """
        self.write(0xFFFC, address & 0xFF) # Low byte
        self.write(0xFFFD, (address >> 8) & 0xFF) # High byte
        logging.info(f"Vetor de Reset (FFFC/FD) definido para {address:04X}")

    def _log_state(self, pc_start, opcode):
        """Função interna para logar o estado da CPU após uma instrução (para debugging)."""
        # Formato similar ao log do Mesen ou Nintendulator
        op_info = self.lookup[opcode]
        instr_name = op_info[0].__name__ if op_info[0] else "???"
        addr_mode_name = op_info[1].__name__ if op_info[1] else "???"
        
        # TODO: Formatar e imprimir o log completo se necessário
        # log_str = (
        #     f"{pc_start:04X}  {opcode:02X}       {instr_name} {addr_mode_name}    "
        #     f"A:{self.regs.a:02X} X:{self.regs.x:02X} Y:{self.regs.y:02X} P:{self.regs.get_status_byte():02X} SP:{self.regs.sp:02X} CYC:{self.total_cycles}"
        # )
        # print(log_str)
        pass

# --- Exemplo de Uso (se executado diretamente) --- 
if __name__ == "__main__":
    bus = Bus()
    cpu = CPU(bus)

    # Programa teste: LDA #$C0, TAX, INX, PHA, LDA #$20, JSR $8010, PLA 
    # (JSR apenas empilha PC-1 e salta, RTS desempilha e volta para PC+1)
    program = [
        0xA9, 0xC0,       # LDA #$C0   (A=C0, N=1, Z=0)
        0xAA,             # TAX        (X=C0, N=1, Z=0)
        0xE8,             # INX        (X=C1, N=1, Z=0)
        0x48,             # PHA        (Push A=C0 to stack @ $01FD)
        0xA9, 0x20,       # LDA #$20   (A=20, N=0, Z=0)
        0x20, 0x10, 0x80, # JSR $8010  (Push $800A-1=$8009 to stack @ $01FC,$01FB, PC=$8010)
        # --- Sub-rotina em $8010 ---
        # (Simulada aqui, pois não há código em $8010 no exemplo)
        # Suponha que $8010 contenha: 0x60 # RTS
        # --- Fim da Sub-rotina ---
        0x68,             # PLA        (Pull from stack @ $01FD -> A=C0, N=1, Z=0)
        0x00              # BRK        (Stop execution)
    ]
    start_addr = 0x8000
    cpu.load_program(program, start_addr)
    
    # Simula a sub-rotina em $8010 contendo apenas RTS
    cpu.write(0x8010, 0x60) # RTS
    
    cpu.set_reset_vector(start_addr)
    cpu.reset()

    # Executa o programa
    logging.info("Iniciando execução...")
    instruction_count = 0
    max_instructions = 20 
    while not cpu.halted and instruction_count < max_instructions:
        pc_before = cpu.regs.pc
        opcode = bus.read(pc_before)
        cpu.clock()
        logging.info(f"PC:{pc_before:04X} Op:{opcode:02X} -> A:{cpu.regs.a:02X} X:{cpu.regs.x:02X} Y:{cpu.regs.y:02X} P:{cpu.regs.get_status_byte():02X} SP:{cpu.regs.sp:02X} CYC:{cpu.total_cycles}")
        instruction_count += 1
        if opcode == 0x00: # Para no BRK
             logging.info("Instrução BRK encontrada, parando.")
             # A própria instrução BRK já lida com a lógica de interrupção
             # Poderíamos setar halted aqui se BRK não fosse implementado como interrupção
             # cpu.halted = True 
             break # Sai do loop de teste

    logging.info("Execução concluída.")
    logging.info(f"Valor final do Acumulador (A): {cpu.regs.a:02X}")
    logging.info(f"Valor final do Registrador X: {cpu.regs.x:02X}")
    logging.info(f"Valor final do Stack Pointer (SP): {cpu.regs.sp:02X}")
    # Verifica o valor que foi empilhado por PHA e depois desempilhado por PLA
    # O SP deve ter voltado ao valor inicial (FD) menos os 2 bytes do JSR que não foram desempilhados
    logging.info(f"Valor esperado no topo da pilha (não desempilhado pelo RTS): {bus.read(0x0100 + ((cpu.regs.sp + 1) & 0xFF)):02X} {bus.read(0x0100 + ((cpu.regs.sp + 2) & 0xFF)):02X}")

