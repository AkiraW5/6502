import sys
import os
import logging
from src.assembler_6502_final import Assembler
from src.Cpu import CPU, Bus

class EmuladorIntegrado:
    """
    Classe que integra o assembler 6502 com o emulador, permitindo
    carregar e executar programas assembly diretamente.
    """
    
    def __init__(self, debug_mode=False):
        """
        Inicializa o emulador integrado.
        
        Args:
            debug_mode (bool): Se True, ativa o modo de depuração.
        """
        self.debug_mode = debug_mode
        self.bus = Bus()
        self.cpu = CPU(self.bus)
        self.assembler = Assembler(debug_mode)
        self.program_origin = 0x8000  # Endereço padrão de origem
        self.program_size = 0
        self.symbols = {}
        
        if debug_mode:
            logging.basicConfig(level=logging.DEBUG, 
                               format='%(asctime)s - %(levelname)s - %(message)s')
        else:
            logging.basicConfig(level=logging.INFO, 
                               format='%(asctime)s - %(levelname)s - %(message)s')
    
    def assemble_file(self, asm_file):
        """
        Monta um arquivo assembly e retorna o código binário gerado.
        
        Args:
            asm_file (str): Caminho para o arquivo assembly.
            
        Returns:
            tuple: (código binário, endereço de origem, símbolos)
        """
        try:
            with open(asm_file, 'r') as f:
                source = f.read()
                
            self.program_origin = self._extract_origin(source)
            
            binary_code = self.assembler.assemble(source)
            self.program_size = len(binary_code)
            
            logging.info(f"Programa montado com sucesso: {self.program_size} bytes")
            logging.info(f"Endereço de origem: ${self.program_origin:04X}")
            
            return binary_code
            
        except Exception as e:
            logging.error(f"Erro ao montar o arquivo: {e}")
            return None
    
    def _extract_origin(self, source):
        """
        Extrai o endereço de origem (.org) do código fonte.
        
        Args:
            source (str): Código fonte assembly.
            
        Returns:
            int: Endereço de origem, ou 0x8000 se não encontrado.
        """
        lines = source.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('.org'):
                parts = line.split()
                if len(parts) >= 2:
                    addr_str = parts[1].strip()
                    if addr_str.startswith('$'):
                        return int(addr_str[1:], 16)
                    else:
                        return int(addr_str)
        
        return 0x8000
    
    def load_program(self, binary_code):
        """
        Carrega o código binário na memória do emulador.
        
        Args:
            binary_code (bytearray): Código binário gerado pelo assembler.
            
        Returns:
            bool: True se o carregamento foi bem-sucedido, False caso contrário.
        """
        if not binary_code:
            logging.error("Nenhum código binário para carregar")
            return False
        
        for i, byte in enumerate(binary_code):
            self.bus.write(self.program_origin + i, byte)
        
        logging.info(f"Programa carregado na memória: {len(binary_code)} bytes em ${self.program_origin:04X}")
        return True
    
    def reset_cpu(self, start_address=None):
        """
        Reseta a CPU e define o PC para o endereço de início.
        
        Args:
            start_address (int, optional): Endereço de início. Se None, usa o endereço de origem.
            
        Returns:
            bool: True se o reset foi bem-sucedido, False caso contrário.
        """
        try:
            self.cpu.reset()
            
            if start_address is not None:
                self.cpu.regs.pc = start_address
            else:
                self.cpu.regs.pc = self.program_origin
            
            logging.info(f"CPU resetada. PC definido para ${self.cpu.regs.pc:04X}")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao resetar a CPU: {e}")
            return False
    
    def run_program(self, max_cycles=10000):
        """
        Executa o programa carregado na memória.
        
        Args:
            max_cycles (int): Número máximo de ciclos a executar.
            
        Returns:
            int: Número de ciclos executados.
        """
        cycles_executed = 0
        
        try:
            while not self.cpu.halted and cycles_executed < max_cycles:
                if self.debug_mode:
                    self._print_debug_info()
                
                self.cpu.clock()
                cycles_executed += self.cpu.cycles
            
            if self.cpu.halted:
                logging.info(f"Programa finalizado (BRK). Ciclos executados: {cycles_executed}")
            else:
                logging.info(f"Limite de ciclos atingido ({max_cycles}). Ciclos executados: {cycles_executed}")
            
            return cycles_executed
            
        except Exception as e:
            logging.error(f"Erro durante a execução: {e}")
            return cycles_executed
    
    def _print_debug_info(self):
        """Imprime informações de depuração sobre o estado atual da CPU."""
        pc = self.cpu.regs.pc
        opcode = self.bus.read(pc)
        
        instr_func, addr_mode_func, _ = self.cpu.lookup[opcode]
        instr_name = instr_func.__name__
        addr_mode_name = addr_mode_func.__name__
        
        # Imprime o estado atual
        logging.debug(f"PC=${pc:04X} A=${self.cpu.regs.a:02X} X=${self.cpu.regs.x:02X} Y=${self.cpu.regs.y:02X} SP=${self.cpu.regs.sp:02X}")
        logging.debug(f"Flags: N={self.cpu.regs.n} V={self.cpu.regs.v} B={self.cpu.regs.b} D={self.cpu.regs.d} I={self.cpu.regs.i} Z={self.cpu.regs.z} C={self.cpu.regs.c}")
        logging.debug(f"Opcode: ${opcode:02X} ({instr_name} {addr_mode_name})")
    
    def assemble_and_run(self, asm_file, max_cycles=10000):
        """
        Monta um arquivo assembly, carrega na memória e executa.
        
        Args:
            asm_file (str): Caminho para o arquivo assembly.
            max_cycles (int): Número máximo de ciclos a executar.
            
        Returns:
            int: Número de ciclos executados, ou -1 em caso de erro.
        """
        binary_code = self.assemble_file(asm_file)
        if not binary_code:
            return -1
        
        if not self.load_program(binary_code):
            return -1
        
        if not self.reset_cpu():
            return -1
        
        return self.run_program(max_cycles)
    
    def dump_memory(self, start_addr, end_addr, bytes_per_row=16):
        """
        Exibe o conteúdo da memória em formato hexadecimal.
        
        Args:
            start_addr (int): Endereço inicial.
            end_addr (int): Endereço final.
            bytes_per_row (int): Número de bytes por linha.
            
        Returns:
            str: Representação formatada da memória.
        """
        result = []
        result.append(f"Dump de memória (${start_addr:04X}-${end_addr:04X}):")
        
        for addr in range(start_addr, end_addr + 1, bytes_per_row):
            line = f"${addr:04X}: "
            hex_values = []
            for offset in range(bytes_per_row):
                if addr + offset <= end_addr:
                    value = self.bus.read(addr + offset)
                    hex_values.append(f"{value:02X}")
                else:
                    hex_values.append("  ")
            line += " ".join(hex_values)
            ascii_values = []
            for offset in range(bytes_per_row):
                if addr + offset <= end_addr:
                    value = self.bus.read(addr + offset)
                    if 32 <= value <= 126:
                        ascii_values.append(chr(value))
                    else:
                        ascii_values.append(".")
                else:
                    ascii_values.append(" ")
            line += "  |" + "".join(ascii_values) + "|"
            
            result.append(line)
        
        return "\n".join(result)

def main():
    """Função principal para uso via linha de comando."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Integração do Assembler com o Emulador 6502')
    parser.add_argument('asm_file', help='Arquivo assembly para montar e executar')
    parser.add_argument('--debug', action='store_true', help='Ativa o modo de depuração')
    parser.add_argument('--max-cycles', type=int, default=10000, help='Número máximo de ciclos a executar')
    parser.add_argument('--dump-start', type=str, help='Endereço inicial para dump de memória (formato: $XXXX)')
    parser.add_argument('--dump-end', type=str, help='Endereço final para dump de memória (formato: $XXXX)')
    
    args = parser.parse_args()
    
    emulador = EmuladorIntegrado(debug_mode=args.debug)
    
    cycles = emulador.assemble_and_run(args.asm_file, args.max_cycles)
    
    if cycles >= 0:
        print(f"Programa executado com sucesso. Ciclos executados: {cycles}")
        
        if args.dump_start and args.dump_end:
            start_addr = int(args.dump_start.replace('$', ''), 16)
            end_addr = int(args.dump_end.replace('$', ''), 16)
            print(emulador.dump_memory(start_addr, end_addr))
    else:
        print("Erro ao executar o programa.")
    
    return 0 if cycles >= 0 else 1

if __name__ == '__main__':
    sys.exit(main())
