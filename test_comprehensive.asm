# Programa de teste abrangente para o assembler 6502
# Este programa testa todos os modos de endereçamento e instruções principais

.org $8000    ; Define o endereço de origem

; Definição de constantes
.equ SCREEN_START $0200
.equ COUNTER $05

; Início do programa
start:
    ; Testes de instruções de transferência de dados
    LDA #$10        ; Modo imediato
    STA SCREEN_START ; Modo absoluto
    LDX #COUNTER    ; Modo imediato com constante
    LDY #$00        ; Modo imediato
    
    ; Testes de modos de endereçamento indexados
    STA SCREEN_START,X  ; Modo absoluto indexado por X
    LDA SCREEN_START,Y  ; Modo absoluto indexado por Y
    
    ; Testes de instruções de incremento/decremento
    INX              ; Modo implícito
    INY              ; Modo implícito
    DEX              ; Modo implícito
    
    ; Testes de instruções de branch
loop:
    DEX              ; Decrementa X
    BNE loop         ; Branch se não for zero
    
    ; Testes de instruções de manipulação de flags
    CLC              ; Limpa carry
    SEC              ; Seta carry
    CLI              ; Limpa interrupt disable
    SEI              ; Seta interrupt disable
    
    ; Testes de instruções de pilha
    PHA              ; Push acumulador
    PHP              ; Push processor status
    PLA              ; Pull acumulador
    PLP              ; Pull processor status
    
    ; Testes de instruções de salto
    JSR subroutine   ; Jump to subroutine
    JMP end          ; Jump incondicional

; Subrotina de teste
subroutine:
    LDA #$FF         ; Carrega valor no acumulador
    RTS              ; Retorna da subrotina

; Fim do programa
end:
    BRK              ; Break
