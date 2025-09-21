# Emulador 6502 (NES)

Este projeto é um emulador completo para o microprocessador MOS 6502, com foco na emulação do console Nintendo Entertainment System (NES). Ele inclui uma CPU 6502 funcional, uma Picture Processing Unit (PPU) para renderização de gráficos, um barramento de memória configurável, suporte a cartuchos (ROMs iNES), um assembler integrado e uma interface gráfica (GUI) interativa para depuração e execução de código.

## Funcionalidades Principais

*   **Emulação da CPU 6502:** Implementação detalhada das instruções e modos de endereçamento do 6502, incluindo tratamento de interrupções (IRQ, NMI, Reset) e contagem de ciclos.
*   **Emulação da PPU (Picture Processing Unit):** Simulação dos registradores da PPU, VRAM, OAM e timing de scanline, com capacidade de renderizar a pattern table e nametables.
*   **Barramento de Memória:** Um sistema de barramento flexível que permite o mapeamento de diferentes regiões de memória (RAM, ROM, registradores da PPU/APU).
*   **Suporte a Cartuchos:** Carregamento de ROMs no formato iNES, com detecção e instalação de mappers (atualmente NROM/Mapper 0).
*   **Assembler Integrado:** Um assembler de duas passagens para código 6502, com suporte a labels, diretivas (`.ORG`, `.BYTE`, `.WORD`, `.EQU`, `.DEFINE`) e detecção de modos de endereçamento.
*   **Interface Gráfica (GUI):** Desenvolvida com Tkinter, oferece:
    *   Editor de código Assembly com destaque de sintaxe e numeração de linhas.
    *   Controles de emulação (Montar, Executar, Pausar, Passo a Passo, Resetar, Carregar ROM).
    *   Visualização em tempo real do estado da CPU (registradores e flags).
    *   Visualização de memória e disassembly.
    *   Visualizador da PPU (pattern table/nametable) com zoom.
    *   Console de log para mensagens do emulador.
    *   Funcionalidade de Breakpoints para depuração.

## Estrutura do Projeto

O projeto é organizado nos seguintes módulos:

*   `Cpu.py`: Implementação da CPU 6502.
*   `Bus.py`: Simulação do barramento de memória.
*   `ppu.py`: Implementação da Picture Processing Unit (PPU).
*   `cartridge.py`: Lógica para carregar e interpretar ROMs de cartucho.
*   `mappers.py`: Implementação de mappers de memória (ex: NROMMapper).
*   `assembler_6502_final.py`: O assembler de código 6502.
*   `addressing_mode_detector.py`: Módulo auxiliar para detecção de modos de endereçamento no assembler.
*   `opcodes_table.py`: Definição da tabela de opcodes do 6502.
*   `macro_processor.py`: Módulo para processamento de macros no assembler.
*   `emulador_gui.py`: A interface gráfica do usuário principal.
*   `hardware_stub.py`: Stubs para hardware não implementado

## Como Usar

### Executando o Emulador

Para iniciar a interface gráfica do emulador, execute o arquivo `emulador_gui.py` na raiz do projeto:

```bash
python -m src.emulador_gui
```

### Usando a GUI

1.  **Editor de Código:** Escreva seu código Assembly 6502 no editor à esquerda.
2.  **Montar:** Clique no botão "Montar" para converter seu código Assembly em código de máquina.
3.  **Carregar ROM:** Use o botão "Carregar ROM" para carregar um arquivo `.nes` ou um binário puro.
4.  **Executar/Pausar/Passo:** Controle a execução do emulador usando os botões correspondentes.
5.  **Breakpoints:** Clique no `gutter` (área à esquerda dos números de linha) para adicionar ou remover breakpoints.
6.  **Visualizações:** Acompanhe o estado da CPU, memória, disassembly e a saída da PPU nas seções à direita.

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests para melhorias, correções de bugs ou novas funcionalidades.

