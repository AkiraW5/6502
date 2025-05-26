import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import sys
import os
import subprocess
import threading
import time

# Importar os módulos do emulador e assembler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from assembler_6502_final import Assembler

# Importar as classes CPU e Bus
try:
    # Tenta importar da pasta upload
    from upload.Cpu import CPU
    from upload.Bus import Bus
except ImportError:
    try:
        # Tenta importar diretamente
        from Cpu import CPU
        from Bus import Bus
    except ImportError:
        print("ERRO: Não foi possível importar as classes CPU e Bus.")
        print("Certifique-se de que os arquivos Cpu.py e Bus.py estão disponíveis.")
        sys.exit(1)

class EmuladorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Emulador 6502")
        self.root.geometry("1200x800")
        
        # Variáveis de estado
        self.bus = Bus()  # Inicializa o barramento
        self.cpu = CPU(self.bus)  # Inicializa a CPU com o barramento
        self.running = False
        self.paused = False
        self.current_file = None
        self.binary_data = None
        
        # Criar a interface
        self.create_menu()
        self.create_main_frame()
        
        # Inicializar o emulador
        self.reset_cpu()
        
    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        # Menu Arquivo
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Novo", command=self.new_file)
        file_menu.add_command(label="Abrir", command=self.open_file)
        file_menu.add_command(label="Salvar", command=self.save_file)
        file_menu.add_command(label="Salvar como", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.root.quit)
        menubar.add_cascade(label="Arquivo", menu=file_menu)
        
        # Menu Emulador
        emulator_menu = tk.Menu(menubar, tearoff=0)
        emulator_menu.add_command(label="Montar", command=self.assemble_code)
        emulator_menu.add_command(label="Executar", command=self.run_emulator)
        emulator_menu.add_command(label="Pausar", command=self.pause_emulator)
        emulator_menu.add_command(label="Passo", command=self.step_emulator)
        emulator_menu.add_command(label="Resetar", command=self.reset_cpu)
        menubar.add_cascade(label="Emulador", menu=emulator_menu)
        
        # Menu Ajuda
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Sobre", command=self.show_about)
        menubar.add_cascade(label="Ajuda", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def create_main_frame(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Dividir em duas colunas
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Coluna esquerda: Editor de código
        editor_frame = ttk.LabelFrame(left_frame, text="Editor de Código Assembly")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.code_editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.WORD, width=50, height=30)
        self.code_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Botões de controle
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Montar", command=self.assemble_code).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Executar", command=self.run_emulator).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Pausar", command=self.pause_emulator).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Passo", command=self.step_emulator).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Resetar", command=self.reset_cpu).pack(side=tk.LEFT, padx=5)
        
        # Coluna direita: Estado da CPU e Memória
        # Estado da CPU
        cpu_frame = ttk.LabelFrame(right_frame, text="Estado da CPU")
        cpu_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Registradores
        reg_frame = ttk.Frame(cpu_frame)
        reg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Linha 1: A, X, Y
        ttk.Label(reg_frame, text="A:").grid(row=0, column=0, padx=5, pady=2)
        self.reg_a = ttk.Label(reg_frame, text="$00")
        self.reg_a.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(reg_frame, text="X:").grid(row=0, column=2, padx=5, pady=2)
        self.reg_x = ttk.Label(reg_frame, text="$00")
        self.reg_x.grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(reg_frame, text="Y:").grid(row=0, column=4, padx=5, pady=2)
        self.reg_y = ttk.Label(reg_frame, text="$00")
        self.reg_y.grid(row=0, column=5, padx=5, pady=2)
        
        # Linha 2: PC, SP
        ttk.Label(reg_frame, text="PC:").grid(row=1, column=0, padx=5, pady=2)
        self.reg_pc = ttk.Label(reg_frame, text="$0000")
        self.reg_pc.grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(reg_frame, text="SP:").grid(row=1, column=2, padx=5, pady=2)
        self.reg_sp = ttk.Label(reg_frame, text="$FF")
        self.reg_sp.grid(row=1, column=3, padx=5, pady=2)
        
        # Linha 3: Flags
        ttk.Label(reg_frame, text="Flags:").grid(row=2, column=0, padx=5, pady=2)
        self.reg_flags = ttk.Label(reg_frame, text="NV-BDIZC")
        self.reg_flags.grid(row=2, column=1, columnspan=5, padx=5, pady=2)
        
        # Visualização de Memória
        mem_frame = ttk.LabelFrame(right_frame, text="Memória")
        mem_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.memory_view = scrolledtext.ScrolledText(mem_frame, wrap=tk.WORD, width=40, height=15)
        self.memory_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Disassembly
        disasm_frame = ttk.LabelFrame(right_frame, text="Disassembly")
        disasm_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.disasm_view = scrolledtext.ScrolledText(disasm_frame, wrap=tk.WORD, width=40, height=10)
        self.disasm_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Console
        console_frame = ttk.LabelFrame(right_frame, text="Console")
        console_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.console = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, width=40, height=5)
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def new_file(self):
        self.code_editor.delete(1.0, tk.END)
        self.current_file = None
        self.log("Novo arquivo criado.")
    
    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Assembly Files", "*.asm"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    self.code_editor.delete(1.0, tk.END)
                    self.code_editor.insert(tk.END, content)
                self.current_file = file_path
                self.log(f"Arquivo aberto: {file_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir o arquivo: {str(e)}")
    
    def save_file(self):
        if self.current_file:
            try:
                with open(self.current_file, 'w') as file:
                    content = self.code_editor.get(1.0, tk.END)
                    file.write(content)
                self.log(f"Arquivo salvo: {self.current_file}")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar o arquivo: {str(e)}")
        else:
            self.save_file_as()
    
    def save_file_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".asm",
            filetypes=[("Assembly Files", "*.asm"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w') as file:
                    content = self.code_editor.get(1.0, tk.END)
                    file.write(content)
                self.current_file = file_path
                self.log(f"Arquivo salvo como: {file_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar o arquivo: {str(e)}")
    
    def assemble_code(self):
        if not self.current_file:
            # Salvar o código temporariamente
            temp_file = "temp_code.asm"
            with open(temp_file, 'w') as file:
                content = self.code_editor.get(1.0, tk.END)
                file.write(content)
            self.current_file = temp_file
            self.log("Código salvo temporariamente.")
        
        try:
            # Montar o código
            self.log("Montando código...")
            assembler = Assembler()
            with open(self.current_file, 'r') as file:
                source_code = file.read()
            
            binary_data = assembler.assemble(source_code)
            if binary_data:
                self.binary_data = binary_data
                self.log(f"Código montado com sucesso: {len(binary_data)} bytes.")
                
                # Carregar o código na memória do emulador
                self.load_binary_to_memory()
                
                # Atualizar a visualização de memória
                self.update_memory_view()
                
                # Atualizar o disassembly
                self.update_disassembly()
            else:
                self.log("Erro ao montar código.")
        except Exception as e:
            self.log(f"Erro ao montar código: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao montar código: {str(e)}")
    
    def load_binary_to_memory(self):
        if not self.binary_data:
            return
        
        # Resetar a CPU
        self.reset_cpu()
        
        # Carregar o código na memória
        # Assumindo que o código começa no endereço $8000 (padrão)
        start_address = 0x8000
        for i, byte in enumerate(self.binary_data):
            self.bus.write(start_address + i, byte)
        
        # Definir o PC para o endereço inicial
        self.cpu.regs.pc = start_address
        
        self.log(f"Código carregado na memória a partir de ${start_address:04X}.")
        self.update_cpu_state()
    
    def run_emulator(self):
        if not self.binary_data:
            messagebox.showwarning("Aviso", "Nenhum código montado para executar.")
            return
        
        self.running = True
        self.paused = False
        
        # Executar em uma thread separada para não bloquear a interface
        threading.Thread(target=self._run_emulation, daemon=True).start()
    
    def _run_emulation(self):
        self.log("Iniciando execução...")
        
        # Limite de ciclos para evitar loops infinitos
        max_cycles = 10000
        cycles = 0
        
        try:
            while self.running and not self.paused and cycles < max_cycles:
                # Executar um ciclo da CPU
                self.cpu.clock()  # Alterado de step() para clock()
                cycles += 1
                
                # Atualizar a interface a cada 100 ciclos
                if cycles % 100 == 0:
                    self.update_cpu_state()
                    self.update_memory_view()
                    self.root.update()
                    time.sleep(0.01)  # Pequena pausa para não sobrecarregar a CPU
                
                # Verificar se chegou a uma instrução BRK
                if self.bus.read(self.cpu.regs.pc) == 0x00:  # BRK
                    self.log("Instrução BRK encontrada. Execução interrompida.")
                    break
            
            if cycles >= max_cycles:
                self.log(f"Limite de ciclos atingido ({max_cycles}). Ciclos executados: {cycles}")
            
            # Atualizar a interface uma última vez
            self.update_cpu_state()
            self.update_memory_view()
            self.update_disassembly()
            
            self.running = False
        except Exception as e:
            self.log(f"Erro durante a execução: {str(e)}")
            self.running = False
    
    def pause_emulator(self):
        if self.running:
            self.paused = True
            self.log("Execução pausada.")
    
    def step_emulator(self):
        if not self.binary_data:
            messagebox.showwarning("Aviso", "Nenhum código montado para executar.")
            return
        
        try:
            # Executar um ciclo da CPU
            cycles = self.cpu.clock()  # Alterado de step() para clock()
            
            # Atualizar a interface
            self.update_cpu_state()
            self.update_memory_view()
            self.update_disassembly()
            
            self.log(f"Passo executado. Ciclos: {cycles}")
        except Exception as e:
            self.log(f"Erro durante o passo: {str(e)}")
    
    def reset_cpu(self):
        self.bus = Bus()
        self.cpu = CPU(self.bus)
        self.running = False
        self.paused = False
        self.log("CPU resetada.")
        self.update_cpu_state()
        self.update_memory_view()
    
    def update_cpu_state(self):
        # Atualizar os registradores
        self.reg_a.config(text=f"${self.cpu.regs.a:02X}")
        self.reg_x.config(text=f"${self.cpu.regs.x:02X}")
        self.reg_y.config(text=f"${self.cpu.regs.y:02X}")
        self.reg_pc.config(text=f"${self.cpu.regs.pc:04X}")
        self.reg_sp.config(text=f"${self.cpu.regs.sp:02X}")
        
        # Atualizar as flags
        flags = ""
        flags += "N" if self.cpu.regs.n else "n"
        flags += "V" if self.cpu.regs.v else "v"
        flags += "-"
        flags += "B" if self.cpu.regs.b else "b"
        flags += "D" if self.cpu.regs.d else "d"
        flags += "I" if self.cpu.regs.i else "i"
        flags += "Z" if self.cpu.regs.z else "z"
        flags += "C" if self.cpu.regs.c else "c"
        self.reg_flags.config(text=flags)
    
    def update_memory_view(self):
        # Limpar a visualização
        self.memory_view.delete(1.0, tk.END)
        
        # Mostrar a memória a partir do PC
        start_address = max(0, self.cpu.regs.pc - 64)
        start_address = start_address & 0xFFF0  # Alinhar a 16 bytes
        
        for i in range(16):  # 16 linhas
            address = start_address + i * 16
            line = f"${address:04X}: "
            
            # 16 bytes por linha
            for j in range(16):
                byte = self.bus.read(address + j)
                line += f"{byte:02X} "
                
                # Destacar o PC
                if address + j == self.cpu.regs.pc:
                    line = line[:-1] + "*"
            
            # Caracteres ASCII
            line += "  "
            for j in range(16):
                byte = self.bus.read(address + j)
                if 32 <= byte <= 126:  # Caracteres imprimíveis
                    line += chr(byte)
                else:
                    line += "."
            
            self.memory_view.insert(tk.END, line + "\n")
    
    def update_disassembly(self):
        # Limpar a visualização
        self.disasm_view.delete(1.0, tk.END)
        
        # Mostrar o disassembly a partir do PC
        address = max(0, self.cpu.regs.pc - 8)
        
        # Disassembly simplificado (apenas para demonstração)
        opcodes = {
            0xA9: ("LDA", "#$%02X", 2),
            0xA2: ("LDX", "#$%02X", 2),
            0xA0: ("LDY", "#$%02X", 2),
            0x8D: ("STA", "$%02X%02X", 3),
            0x8E: ("STX", "$%02X%02X", 3),
            0x8C: ("STY", "$%02X%02X", 3),
            0xE8: ("INX", "", 1),
            0xC8: ("INY", "", 1),
            0xCA: ("DEX", "", 1),
            0x88: ("DEY", "", 1),
            0xD0: ("BNE", "$%02X", 2),
            0x18: ("CLC", "", 1),
            0x38: ("SEC", "", 1),
            0x58: ("CLI", "", 1),
            0x78: ("SEI", "", 1),
            0x48: ("PHA", "", 1),
            0x08: ("PHP", "", 1),
            0x68: ("PLA", "", 1),
            0x28: ("PLP", "", 1),
            0x4C: ("JMP", "$%02X%02X", 3),
            0x20: ("JSR", "$%02X%02X", 3),
            0x60: ("RTS", "", 1),
            0x00: ("BRK", "", 1),
            0xEA: ("NOP", "", 1),
        }
        
        for i in range(16):  # 16 instruções
            current_address = address + i
            opcode = self.bus.read(current_address)
            
            if opcode in opcodes:
                mnemonic, operand_format, size = opcodes[opcode]
                
                if size == 1:
                    line = f"${current_address:04X}: {opcode:02X}       {mnemonic}"
                elif size == 2:
                    operand = self.bus.read(current_address + 1)
                    line = f"${current_address:04X}: {opcode:02X} {operand:02X}    {mnemonic} "
                    if operand_format:
                        line += operand_format % operand
                elif size == 3:
                    operand1 = self.bus.read(current_address + 1)
                    operand2 = self.bus.read(current_address + 2)
                    line = f"${current_address:04X}: {opcode:02X} {operand1:02X} {operand2:02X} {mnemonic} "
                    if operand_format:
                        line += operand_format % (operand2, operand1)
            else:
                line = f"${current_address:04X}: {opcode:02X}       ???"
            
            # Destacar o PC
            if current_address == self.cpu.regs.pc:
                line = "> " + line
            else:
                line = "  " + line
            
            self.disasm_view.insert(tk.END, line + "\n")
            
            # Avançar para a próxima instrução
            if opcode in opcodes:
                address += opcodes[opcode][2]
            else:
                address += 1
    
    def log(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
    
    def show_about(self):
        messagebox.showinfo(
            "Sobre",
            "Emulador 6502\n\n"
            "Um emulador completo para o processador MOS 6502.\n"
            "Desenvolvido como parte do projeto de emulação de sistemas retro.\n\n"
            "© 2025 Projeto 6502"
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = EmuladorGUI(root)
    root.mainloop()
