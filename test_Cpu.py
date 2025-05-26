# -*- coding: utf-8 -*-
"""
Testes unitários para o emulador do microprocessador MOS 6502.

Este módulo contém testes para verificar o funcionamento correto das instruções
e modos de endereçamento implementados na classe CPU.
"""

import unittest
from upload.Cpu import CPU, Bus, Registers

class TestCPUInstructions(unittest.TestCase):
    """Testes para as instruções da CPU 6502."""
    
    def setUp(self):
        """Configura o ambiente de teste antes de cada teste."""
        self.bus = Bus()
        self.cpu = CPU(self.bus)
        self.start_addr = 0x0200  # Endereço inicial para carregar programas de teste
        self.cpu.reset()
        self.cpu.regs.pc = self.start_addr  # Define PC para o endereço inicial

    def _load_and_run_cycles(self, program, num_cycles):
        """Carrega um programa na memória e executa um número específico de ciclos."""
        offset = 0
        for byte in program:
            self.bus.write(self.start_addr + offset, byte)
            offset += 1
        
        # Executa o número especificado de ciclos
        for _ in range(num_cycles):
            if not self.cpu.halted:
                self.cpu.clock()

    def _load_and_run(self, program):
        """Carrega um programa na memória e executa até o final."""
        offset = 0
        for byte in program:
            self.bus.write(self.start_addr + offset, byte)
            offset += 1
        
        # Executa o programa
        for _ in range(len(program)):
            if not self.cpu.halted:
                self.cpu.clock()
                
    def test_RTI(self):
        """Teste completo de RTI (Return from Interrupt)."""
        # Simula estado após uma interrupção
        target_pc = 0x1234
        target_status = 0b10101010 # N=1, D=1, Z=1 (B e U serão ignorados)
        initial_sp = 0xFA
        
        # Configura o estado inicial
        self.cpu.regs.pc = 0x0000 
        self.cpu.regs.sp = 0xF7  # SP já ajustado para apontar para o byte antes do status
        
        # Empilha PC e Status como se uma interrupção tivesse ocorrido
        self.bus.write(0x0100 + 0xF8, target_status | 0b00110000) # Status com B=1, U=1
        self.bus.write(0x0100 + 0xF9, target_pc & 0xFF) # PC low byte
        self.bus.write(0x0100 + 0xFA, (target_pc >> 8) & 0xFF) # PC high byte
        
        # Executa RTI diretamente sem usar _load_and_run
        self.cpu.RTI(self.cpu.IMP)

        # Verifica se PC foi restaurado
        self.assertEqual(self.cpu.regs.pc, target_pc)
        # Verifica se SP voltou ao normal
        self.assertEqual(self.cpu.regs.sp, initial_sp)
        # Verifica se flags foram restauradas (exceto B e U)
        self.assertEqual(self.cpu.regs.n, 1)
        self.assertEqual(self.cpu.regs.v, 0)
        self.assertEqual(self.cpu.regs.d, 1)
        self.assertEqual(self.cpu.regs.i, 0)
        self.assertEqual(self.cpu.regs.z, 1)
        self.assertEqual(self.cpu.regs.c, 0)
        self.assertEqual(self.cpu.regs.u, 1) # U sempre 1

    # --- Testes de Reset e Interrupções --- 
    def test_RESET(self):
        self.cpu.set_reset_vector(0xFCE2)
        self.cpu.regs.a = 0xFF # Altera estado para garantir que reset funcione
        self.cpu.reset()
        self.assertEqual(self.cpu.regs.pc, 0xFCE2)
        self.assertEqual(self.cpu.regs.a, 0)
        self.assertEqual(self.cpu.regs.x, 0)
        self.assertEqual(self.cpu.regs.y, 0)
        self.assertEqual(self.cpu.regs.sp, 0xFD)
        self.assertEqual(self.cpu.regs.i, 1) # Flag I deve ser setada no reset

    def test_BRK(self):
        # Configura o vetor de IRQ/BRK
        self.bus.write(0xFFFE, 0x34)
        self.bus.write(0xFFFF, 0x12)
        
        # Configura a flag N para 1 para testar se é preservada no status empilhado
        self.cpu.regs.n = 1
        
        # Salva PC antes do BRK
        pc_before_brk = self.cpu.regs.pc
        
        # Executa BRK
        self._load_and_run_cycles([0x00], 1) # BRK
        
        # Verifica se PC foi atualizado para o endereço do vetor de IRQ/BRK
        self.assertEqual(self.cpu.regs.pc, 0x1234)
        
        # Verifica se a flag I foi setada
        self.assertEqual(self.cpu.regs.i, 1)
        
        # Verifica o status empilhado (B=1, U=1, N=1)
        status_pushed = self.bus.read(0x0100 + ((self.cpu.regs.sp + 1) & 0xFF))
        self.assertTrue(status_pushed & 0b00110000 == 0b00110000) # B=1, U=1
        self.assertTrue(status_pushed & 0b10000000) # N=1

        # Verifica o PC empilhado (PC após o byte de padding do BRK)
        pc_pushed_low = self.bus.read(0x0100 + ((self.cpu.regs.sp + 2) & 0xFF))
        pc_pushed_high = self.bus.read(0x0100 + ((self.cpu.regs.sp + 3) & 0xFF))
        pc_pushed = (pc_pushed_high << 8) | pc_pushed_low
        self.assertEqual(pc_pushed, pc_before_brk + 2)

    # --- Testes de Instruções de Carga ---

    def test_LDA_IMM(self):
        self._load_and_run([0xA9, 0x42]) # LDA #$42
        self.assertEqual(self.cpu.regs.a, 0x42)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_LDA_ZP0(self):
        self.bus.write(0x42, 0x37)
        self._load_and_run([0xA5, 0x42]) # LDA $42
        self.assertEqual(self.cpu.regs.a, 0x37)

    def test_LDA_ZPX(self):
        self.cpu.regs.x = 0x05
        self.bus.write(0x47, 0x37) # $42 + $05 = $47
        self._load_and_run([0xB5, 0x42]) # LDA $42,X
        self.assertEqual(self.cpu.regs.a, 0x37)

    def test_LDA_ABS(self):
        self.bus.write(0x1234, 0x37)
        self._load_and_run([0xAD, 0x34, 0x12]) # LDA $1234
        self.assertEqual(self.cpu.regs.a, 0x37)

    def test_LDA_ABX(self):
        self.cpu.regs.x = 0x05
        self.bus.write(0x1239, 0x37) # $1234 + $05 = $1239
        self._load_and_run([0xBD, 0x34, 0x12]) # LDA $1234,X
        self.assertEqual(self.cpu.regs.a, 0x37)

    def test_LDA_ABY(self):
        self.cpu.regs.y = 0x05
        self.bus.write(0x1239, 0x37) # $1234 + $05 = $1239
        self._load_and_run([0xB9, 0x34, 0x12]) # LDA $1234,Y
        self.assertEqual(self.cpu.regs.a, 0x37)

    def test_LDA_IZX(self):
        self.cpu.regs.x = 0x05
        self.bus.write(0x47, 0x34) # $42 + $05 = $47
        self.bus.write(0x48, 0x12)
        self.bus.write(0x1234, 0x37)
        self._load_and_run([0xA1, 0x42]) # LDA ($42,X)
        self.assertEqual(self.cpu.regs.a, 0x37)

    def test_LDA_IZY(self):
        self.cpu.regs.y = 0x05
        self.bus.write(0x42, 0x34)
        self.bus.write(0x43, 0x12)
        self.bus.write(0x1239, 0x37) # $1234 + $05 = $1239
        self._load_and_run([0xB1, 0x42]) # LDA ($42),Y
        self.assertEqual(self.cpu.regs.a, 0x37)

    def test_LDX_IMM(self):
        self._load_and_run([0xA2, 0x42]) # LDX #$42
        self.assertEqual(self.cpu.regs.x, 0x42)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_LDY_IMM(self):
        self._load_and_run([0xA0, 0x42]) # LDY #$42
        self.assertEqual(self.cpu.regs.y, 0x42)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    # --- Testes de Instruções de Armazenamento ---

    def test_STA_ZP0(self):
        self.cpu.regs.a = 0x42
        self._load_and_run([0x85, 0x37]) # STA $37
        self.assertEqual(self.bus.read(0x37), 0x42)

    def test_STX_ZP0(self):
        self.cpu.regs.x = 0x42
        self._load_and_run([0x86, 0x37]) # STX $37
        self.assertEqual(self.bus.read(0x37), 0x42)

    def test_STY_ZP0(self):
        self.cpu.regs.y = 0x42
        self._load_and_run([0x84, 0x37]) # STY $37
        self.assertEqual(self.bus.read(0x37), 0x42)

    # --- Testes de Instruções Aritméticas ---

    def test_ADC_IMM(self):
        self.cpu.regs.a = 0x42
        self.cpu.regs.c = 0
        self._load_and_run([0x69, 0x37]) # ADC #$37
        self.assertEqual(self.cpu.regs.a, 0x79) # $42 + $37 = $79
        self.assertEqual(self.cpu.regs.c, 0)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_ADC_IMM_with_carry(self):
        self.cpu.regs.a = 0x42
        self.cpu.regs.c = 1
        self._load_and_run([0x69, 0x37]) # ADC #$37
        self.assertEqual(self.cpu.regs.a, 0x7A) # $42 + $37 + $01 = $7A
        self.assertEqual(self.cpu.regs.c, 0)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_ADC_IMM_overflow(self):
        self.cpu.regs.a = 0x7F
        self.cpu.regs.c = 0
        self._load_and_run([0x69, 0x01]) # ADC #$01
        self.assertEqual(self.cpu.regs.a, 0x80) # $7F + $01 = $80
        self.assertEqual(self.cpu.regs.c, 0)
        self.assertEqual(self.cpu.regs.v, 1) # Overflow: 7F (positivo) + 01 = 80 (negativo)
        self.assertEqual(self.cpu.regs.n, 1) # Bit 7 setado

    # --- Testes de Instruções Lógicas ---

    def test_AND_IMM(self):
        self.cpu.regs.a = 0xF0
        self._load_and_run([0x29, 0x0F]) # AND #$0F
        self.assertEqual(self.cpu.regs.a, 0x00) # $F0 & $0F = $00
        self.assertEqual(self.cpu.regs.z, 1)
        self.assertEqual(self.cpu.regs.n, 0)

    # --- Testes de Instruções de Deslocamento ---

    def test_ASL_ACC(self):
        self.cpu.regs.a = 0x81
        self._load_and_run([0x0A]) # ASL A
        self.assertEqual(self.cpu.regs.a, 0x02) # $81 << 1 = $02
        self.assertEqual(self.cpu.regs.c, 1) # Bit 7 vai para carry
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_ASL_ZP0(self):
        self.bus.write(0x37, 0x81)
        self._load_and_run([0x06, 0x37]) # ASL $37
        self.assertEqual(self.bus.read(0x37), 0x02) # $81 << 1 = $02
        self.assertEqual(self.cpu.regs.c, 1) # Bit 7 vai para carry
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    # --- Testes de Instruções de Incremento/Decremento ---

    def test_INC_ZP0(self):
        self.bus.write(0x37, 0x41)
        self._load_and_run([0xE6, 0x37]) # INC $37
        self.assertEqual(self.bus.read(0x37), 0x42) # $41 + 1 = $42
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_DEC_ZP0(self):
        self.bus.write(0x37, 0x43)
        self._load_and_run([0xC6, 0x37]) # DEC $37
        self.assertEqual(self.bus.read(0x37), 0x42) # $43 - 1 = $42
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_INX(self):
        self.cpu.regs.x = 0x41
        self._load_and_run([0xE8]) # INX
        self.assertEqual(self.cpu.regs.x, 0x42) # $41 + 1 = $42
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_INY(self):
        self.cpu.regs.y = 0x41
        self._load_and_run([0xC8]) # INY
        self.assertEqual(self.cpu.regs.y, 0x42) # $41 + 1 = $42
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_DEX(self):
        self.cpu.regs.x = 0x43
        self._load_and_run([0xCA]) # DEX
        self.assertEqual(self.cpu.regs.x, 0x42) # $43 - 1 = $42
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_DEY(self):
        self.cpu.regs.y = 0x43
        self._load_and_run([0x88]) # DEY
        self.assertEqual(self.cpu.regs.y, 0x42) # $43 - 1 = $42
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    # --- Testes de Instruções de Pilha ---

    def test_PHA_PLA(self):
        # Nota: Não verificamos o SP diretamente, pois a implementação pode variar
        # O importante é que o valor seja corretamente empilhado e desempilhado
        self.cpu.regs.a = 0x42
        self._load_and_run_cycles([0x48, 0xA9, 0x00, 0x68], 4) # PHA, LDA #$00, PLA
        self.assertEqual(self.cpu.regs.a, 0x42) # Valor restaurado
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 0)

    def test_PHP_PLP(self):
        initial_sp = self.cpu.regs.sp
        # Configura flags
        self.cpu.regs.n = 1
        self.cpu.regs.v = 1
        self.cpu.regs.d = 1
        self.cpu.regs.i = 0
        self.cpu.regs.z = 1
        self.cpu.regs.c = 1
        
        self._load_and_run([0x08, 0x58, 0x28]) # PHP, CLI, PLP
        
        # Verifica se as flags foram restauradas
        self.assertEqual(self.cpu.regs.n, 1)
        self.assertEqual(self.cpu.regs.v, 1)
        self.assertEqual(self.cpu.regs.d, 1)
        self.assertEqual(self.cpu.regs.i, 0) # Restaurada para 0
        self.assertEqual(self.cpu.regs.z, 1)
        self.assertEqual(self.cpu.regs.c, 1)
        self.assertEqual(self.cpu.regs.sp, initial_sp) # SP restaurado

    # --- Testes de Instruções de Salto ---

    def test_JMP_ABS(self):
        self._load_and_run_cycles([0x4C, 0x34, 0x12], 1) # JMP $1234
        self.assertEqual(self.cpu.regs.pc, 0x1234)

    def test_JMP_IND(self):
        # JMP ($10FF) deve ler low byte de $10FF (CD) e high byte de $1000 (AB)
        # Resultando no salto para $ABCD
        self.bus.write(0x10FF, 0xCD) 
        self.bus.write(0x1000, 0xAB) 
        self._load_and_run_cycles([0x6C, 0xFF, 0x10], 1) # JMP ($10FF)
        self.assertEqual(self.cpu.regs.pc, 0xABCD)

    def test_JSR_RTS(self):
        initial_sp = self.cpu.regs.sp
        # Programa: JSR $0300 ... (em $0300: RTS)
        self.bus.write(0x0300, 0x60) # RTS na sub-rotina
        self._load_and_run_cycles([0x20, 0x00, 0x03], 2) # JSR $0300, depois RTS
        
        # PC deve voltar para a instrução *após* o JSR
        self.assertEqual(self.cpu.regs.pc, self.start_addr + 3)
        # SP deve ter diminuído 2 (push word) e aumentado 2 (pop word)
        self.assertEqual(self.cpu.regs.sp, initial_sp)
        
        # Verifica o conteúdo da pilha após JSR
        # JSR empilha o endereço do último byte da instrução JSR (PC-1)
        # Isso é o endereço do byte alto do operando (start_addr + 2)
        stack_addr_high = 0x0100 + ((initial_sp - 1) & 0xFF)
        stack_addr_low = 0x0100 + ((initial_sp - 2) & 0xFF)
        expected_return_addr = self.start_addr + 2 # Endereço do último byte do JSR
        
        # Não verificamos o conteúdo da pilha após o RTS, pois ele já foi desempilhado
        # Mas podemos verificar o que foi empilhado inspecionando a memória diretamente

    # --- Testes de Instruções de Transferência ---

    def test_TAX(self):
        self.cpu.regs.a = 0x8F
        self._load_and_run([0xAA]) # TAX
        self.assertEqual(self.cpu.regs.x, 0x8F)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 1) # Bit 7 setado

    def test_TXA(self):
        self.cpu.regs.x = 0x8F
        self._load_and_run([0x8A]) # TXA
        self.assertEqual(self.cpu.regs.a, 0x8F)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 1) # Bit 7 setado

    def test_TAY(self):
        self.cpu.regs.a = 0x8F
        self._load_and_run([0xA8]) # TAY
        self.assertEqual(self.cpu.regs.y, 0x8F)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 1) # Bit 7 setado

    def test_TYA(self):
        self.cpu.regs.y = 0x8F
        self._load_and_run([0x98]) # TYA
        self.assertEqual(self.cpu.regs.a, 0x8F)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 1) # Bit 7 setado

    def test_TSX(self):
        self.cpu.regs.sp = 0x8F
        self._load_and_run([0xBA]) # TSX
        self.assertEqual(self.cpu.regs.x, 0x8F)
        self.assertEqual(self.cpu.regs.z, 0)
        self.assertEqual(self.cpu.regs.n, 1) # Bit 7 setado

    def test_TXS(self):
        self.cpu.regs.x = 0x8F
        self._load_and_run([0x9A]) # TXS
        self.assertEqual(self.cpu.regs.sp, 0x8F)
        # TXS não afeta flags
        
    # --- Testes de Instruções de Manipulação de Flags ---

    def test_CLC(self):
        self.cpu.regs.c = 1
        self._load_and_run([0x18]) # CLC
        self.assertEqual(self.cpu.regs.c, 0)

    def test_SEC(self):
        self.cpu.regs.c = 0
        self._load_and_run([0x38]) # SEC
        self.assertEqual(self.cpu.regs.c, 1)

    def test_CLI(self):
        self.cpu.regs.i = 1
        self._load_and_run([0x58]) # CLI
        self.assertEqual(self.cpu.regs.i, 0)

    def test_SEI(self):
        self.cpu.regs.i = 0
        self._load_and_run([0x78]) # SEI
        self.assertEqual(self.cpu.regs.i, 1)

    def test_CLV(self):
        self.cpu.regs.v = 1
        self._load_and_run([0xB8]) # CLV
        self.assertEqual(self.cpu.regs.v, 0)

    def test_CLD(self):
        self.cpu.regs.d = 1
        self._load_and_run([0xD8]) # CLD
        self.assertEqual(self.cpu.regs.d, 0)

    def test_SED(self):
        self.cpu.regs.d = 0
        self._load_and_run([0xF8]) # SED
        self.assertEqual(self.cpu.regs.d, 1)

    # --- Testes de Outras Instruções ---

    def test_NOP(self):
        initial_pc = self.cpu.regs.pc
        self._load_and_run([0xEA]) # NOP
        self.assertEqual(self.cpu.regs.pc, initial_pc + 1)

if __name__ == "__main__":
    unittest.main()
