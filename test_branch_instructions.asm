# Programa de teste para instruções de branch e comparação do 6502
# Este programa testa todas as instruções de branch e comparação implementadas

.org $8000    ; Define o endereço de origem

; Definição de constantes
.equ COUNTER $05
.equ TEST_RESULT $0200  ; Endereço para armazenar resultados dos testes

; Início do programa
start:
    ; Inicializa registradores
    LDA #$00        ; Acumulador = 0
    LDX #$00        ; X = 0
    LDY #$00        ; Y = 0
    
    ; Teste 1: BNE (Branch if Not Equal)
    LDA #$01        ; A = 1
    CMP #$01        ; Compara A com 1 (deve setar Z=1)
    BNE test1_fail  ; Não deve desviar (Z=1)
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT ; Armazena resultado
    JMP test2
test1_fail:
    LDA #$FF        ; Marca falha
    STA TEST_RESULT ; Armazena resultado

test2:
    ; Teste 2: BEQ (Branch if Equal)
    LDA #$02        ; A = 2
    CMP #$02        ; Compara A com 2 (deve setar Z=1)
    BEQ test2_pass  ; Deve desviar (Z=1)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+1 ; Armazena resultado
    JMP test3
test2_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+1 ; Armazena resultado

test3:
    ; Teste 3: BCC (Branch if Carry Clear)
    CLC             ; Limpa carry
    BCC test3_pass  ; Deve desviar (C=0)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+2 ; Armazena resultado
    JMP test4
test3_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+2 ; Armazena resultado

test4:
    ; Teste 4: BCS (Branch if Carry Set)
    SEC             ; Seta carry
    BCS test4_pass  ; Deve desviar (C=1)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+3 ; Armazena resultado
    JMP test5
test4_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+3 ; Armazena resultado

test5:
    ; Teste 5: BMI (Branch if Minus)
    LDA #$80        ; A = 128 (bit 7 = 1, negativo)
    BMI test5_pass  ; Deve desviar (N=1)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+4 ; Armazena resultado
    JMP test6
test5_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+4 ; Armazena resultado

test6:
    ; Teste 6: BPL (Branch if Plus)
    LDA #$01        ; A = 1 (bit 7 = 0, positivo)
    BPL test6_pass  ; Deve desviar (N=0)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+5 ; Armazena resultado
    JMP test7
test6_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+5 ; Armazena resultado

test7:
    ; Teste 7: BVC (Branch if Overflow Clear)
    CLV             ; Limpa overflow
    BVC test7_pass  ; Deve desviar (V=0)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+6 ; Armazena resultado
    JMP test8
test7_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+6 ; Armazena resultado

test8:
    ; Teste 8: BVS (Branch if Overflow Set)
    ; Para setar V, usamos uma operação que causa overflow
    LDA #$7F        ; A = 127 (01111111)
    ADC #$01        ; A = 128 (10000000), seta V porque 127+1 causa overflow em complemento de 2
    BVS test8_pass  ; Deve desviar (V=1)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+7 ; Armazena resultado
    JMP test9
test8_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+7 ; Armazena resultado

test9:
    ; Teste 9: CMP (Compare Accumulator)
    LDA #$50        ; A = 80
    CMP #$30        ; Compara com 48 (A > operando, deve setar C=1, Z=0)
    BCS test9_pass  ; Deve desviar (C=1)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+8 ; Armazena resultado
    JMP test10
test9_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+8 ; Armazena resultado

test10:
    ; Teste 10: CPX (Compare X Register)
    LDX #$40        ; X = 64
    CPX #$40        ; Compara com 64 (X == operando, deve setar Z=1, C=1)
    BEQ test10_pass ; Deve desviar (Z=1)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+9 ; Armazena resultado
    JMP test11
test10_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+9 ; Armazena resultado

test11:
    ; Teste 11: CPY (Compare Y Register)
    LDY #$20        ; Y = 32
    CPY #$10        ; Compara com 16 (Y > operando, deve setar C=1, Z=0)
    BCS test11_pass ; Deve desviar (C=1)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+10 ; Armazena resultado
    JMP test12
test11_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+10 ; Armazena resultado

test12:
    ; Teste 12: BIT (Bit Test)
    LDA #$C0        ; A = 11000000
    BIT #$80        ; Testa com 10000000 (bit 7 = 1, bit 6 = 0)
                    ; Resultado AND = 10000000 (não zero)
                    ; Deve setar N=1 (bit 7 do operando), V=0 (bit 6 do operando), Z=0
    BMI test12_pass ; Deve desviar (N=1)
    LDA #$FF        ; Marca falha
    STA TEST_RESULT+11 ; Armazena resultado
    JMP end
test12_pass:
    LDA #$AA        ; Marca sucesso
    STA TEST_RESULT+11 ; Armazena resultado

end:
    ; Fim do programa
    BRK              ; Break

