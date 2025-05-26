# Exemplo de programa 6502 para testar o assembler
# Este programa demonstra várias instruções e modos de endereçamento

.org $8000    ; Define o endereço de início como $8000

; Definição de constantes
.equ SCREEN_START, $0200  ; Endereço inicial da tela
.equ COUNTER_MAX, 10      ; Valor máximo do contador

; Início do programa
start:  ; Inicialização de registradores
    LDA #$00    ; Carrega acumulador com 0
    TAX         ; Transfere A para X
    TAY         ; Transfere A para Y
    
    ; Operações de pilha
    PHA         ; Empilha A
    PLA         ; Desempilha para A
    
    ; Operações lógicas
    LDA #$FF    ; Carrega A com $FF (todos os bits em 1)
    AND #$0F    ; AND com $0F (mantém apenas os 4 bits menos significativos)
    ORA #$A0    ; OR com $A0 (liga os bits 7 e 5)
    EOR #$FF    ; XOR com $FF (inverte todos os bits)
    
    ; Incrementos e decrementos
    LDX #$05    ; Carrega X com 5
    INX         ; Incrementa X (X = 6)
    INX         ; Incrementa X (X = 7)
    DEX         ; Decrementa X (X = 6)
    
    ; Acesso à memória
    LDA #$AA    ; Carrega A com $AA
    STA SCREEN_START  ; Armazena A no endereço SCREEN_START
    
    ; Modos de endereçamento indexado
    LDY #$04    ; Carrega Y com 4
    LDA #$BB    ; Carrega A com $BB
    STA SCREEN_START,Y  ; Armazena A no endereço SCREEN_START + Y
    
    ; Loop com contador
    LDX #$00    ; Inicializa X com 0
loop:
    CPX #COUNTER_MAX  ; Compara X com COUNTER_MAX
    BEQ end_loop      ; Se igual, sai do loop
    INX               ; Incrementa X
    TXA               ; Transfere X para A
    STA SCREEN_START,X  ; Armazena A no endereço SCREEN_START + X
    JMP loop          ; Volta ao início do loop
end_loop:
    
    ; Operações aritméticas
    CLC               ; Limpa o carry
    LDA #$05          ; Carrega A com 5
    ADC #$03          ; Adiciona 3 a A (A = 8)
    
    ; Chamada de sub-rotina
    JSR subroutine    ; Chama a sub-rotina
    
    ; Fim do programa
    BRK               ; Interrompe a execução
    
; Sub-rotina
subroutine:
    LDA #$CC          ; Carrega A com $CC
    STA SCREEN_START  ; Armazena A no endereço SCREEN_START
    RTS               ; Retorna da sub-rotina

; Dados
.org $8100    ; Define novo endereço para os dados
data:
.byte $01, $02, $03, $04  ; Define bytes individuais
.word $1234, $5678        ; Define palavras (16 bits)
.byte "Hello, 6502!"      ; Define uma string
