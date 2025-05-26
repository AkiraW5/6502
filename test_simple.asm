# Programa de teste simplificado
# Este programa testa apenas instruções básicas sem comentários em linha

.org $8000

start:
    LDA #$10
    STA $0200
    
    LDX #$05
    
loop:
    DEX
    BNE loop
    
    RTS
