; Exemplo de programa 6502

.org $8000    ; Define endere�o de origem

start:
    LDA #$10  ; Carrega acumulador com valor imediato
    STA $0200 ; Armazena em mem�ria
    LDX #$05  ; Carrega X com valor imediato

loop:
    DEX       ; Decrementa X
    BNE loop  ; Desvia se n�o for zero
    RTS       ; Retorna da subrotina

