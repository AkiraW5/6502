# Programa de teste para validar o assembler 6502
# Este programa testa todas as instruções e modos de endereçamento

; Definição de constantes
.equ SCREEN_START $0200   ; Endereço inicial da tela
.equ COUNTER_MAX 10       ; Valor máximo do contador

; Definir o ponto de início do programa
.org $8000

; Início do programa
start:
    ; Instruções de transferência de dados
    LDA #$00          ; Carrega acumulador com valor imediato
    LDX #$01          ; Carrega X com valor imediato
    LDY #$02          ; Carrega Y com valor imediato
    
    STA SCREEN_START  ; Armazena A em endereço absoluto
    STX SCREEN_START,Y ; Armazena X em endereço absoluto indexado por Y
    STY $10           ; Armazena Y em endereço zeropage
    
    TAX               ; Transfere A para X
    TAY               ; Transfere A para Y
    TXA               ; Transfere X para A
    TYA               ; Transfere Y para A
    TXS               ; Transfere X para SP
    TSX               ; Transfere SP para X
    
    ; Instruções aritméticas
    CLC               ; Limpa carry
    ADC #$05          ; Adiciona com carry (imediato)
    ADC $20           ; Adiciona com carry (zeropage)
    ADC $2000         ; Adiciona com carry (absoluto)
    ADC $2000,X       ; Adiciona com carry (absoluto,X)
    ADC $20,X         ; Adiciona com carry (zeropage,X)
    ADC ($20,X)       ; Adiciona com carry (indireto,X)
    ADC ($20),Y       ; Adiciona com carry (indireto,Y)
    
    SEC               ; Seta carry
    SBC #$01          ; Subtrai com carry (imediato)
    
    INC $30           ; Incrementa memória (zeropage)
    INX               ; Incrementa X
    INY               ; Incrementa Y
    
    DEC $30           ; Decrementa memória (zeropage)
    DEX               ; Decrementa X
    DEY               ; Decrementa Y
    
    ; Instruções lógicas
    AND #$FF          ; AND lógico (imediato)
    ORA #$0F          ; OR lógico (imediato)
    EOR #$AA          ; XOR lógico (imediato)
    
    ASL A             ; Shift left acumulador
    ASL $40           ; Shift left memória (zeropage)
    
    LSR A             ; Shift right acumulador
    LSR $40           ; Shift right memória (zeropage)
    
    ROL A             ; Rotate left acumulador
    ROL $40           ; Rotate left memória (zeropage)
    
    ROR A             ; Rotate right acumulador
    ROR $40           ; Rotate right memória (zeropage)
    
    ; Instruções de comparação
    CMP #$10          ; Compara A (imediato)
    CPX #$10          ; Compara X (imediato)
    CPY #$10          ; Compara Y (imediato)
    
    BIT $50           ; Testa bits (zeropage)
    
    ; Instruções de desvio condicional
    BCC branch1       ; Desvia se carry clear
    BCS branch1       ; Desvia se carry set
branch1:
    BEQ branch2       ; Desvia se igual
    BNE branch2       ; Desvia se não igual
branch2:
    BMI branch3       ; Desvia se negativo
    BPL branch3       ; Desvia se positivo
branch3:
    BVC branch4       ; Desvia se overflow clear
    BVS branch4       ; Desvia se overflow set
branch4:

    ; Instruções de desvio e chamadas
    JMP absolute_jump ; Salto absoluto
    JSR subroutine    ; Chama subrotina
    
    ; Instruções de manipulação de flags
    CLC               ; Limpa carry
    SEC               ; Seta carry
    CLI               ; Limpa interrupt disable
    SEI               ; Seta interrupt disable
    CLD               ; Limpa decimal mode
    SED               ; Seta decimal mode
    CLV               ; Limpa overflow

    ; Instruções de pilha
    PHA               ; Push acumulador
    PLA               ; Pull acumulador
    PHP               ; Push processor status
    PLP               ; Pull processor status
    
    ; Outras instruções
    NOP               ; No operation
    BRK               ; Break/Force interrupt

absolute_jump:
    ; Teste de modos de endereçamento adicionais
    LDA ($60,X)       ; Indireto,X
    LDA ($60),Y       ; Indireto,Y
    JMP ($6000)       ; Indireto

subroutine:
    ; Corpo da subrotina
    LDA #$CC          ; Carrega A com valor
    RTS               ; Retorna da subrotina

interrupt_handler:
    ; Manipulador de interrupção
    RTI               ; Retorna de interrupção

; Dados
.org $8100
data:
    .byte $01, $02, $03, $04   ; Define bytes
    .word $1234, $5678         ; Define words (16 bits)
    .byte "Hello, 6502!"       ; Define string

