# Programa de teste simplificado
# Este programa testa apenas instru��es b�sicas sem coment�rios em linha

.org $8000

start:
    LDA #$10
    STA $0200
    
    LDX #$05
    
loop:
    DEX
    BNE loop
    
    RTS

