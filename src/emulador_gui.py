from src.ppu import SimplePPU, FullPPU
from src.Bus import Bus
from src.Cpu import CPU
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from typing import Any, cast
import sys
import os
import subprocess
import threading
import time

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from src.assembler_6502_final import Assembler
except Exception:
    from assembler_6502_final import Assembler


class EmuladorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Emulador 6502")
        self.root.geometry("1200x800")

        # Variáveis de estado
        self.bus = Bus()
        self.cpu = CPU(self.bus)
        self.running = False
        self.paused = False
        self.current_file = None
        self.binary_data = None
        self.data_ranges = []

        self.create_menu()
        self.create_main_frame()
        self._last_editor_y = None
        self.root.after(100, self._sync_gutter_with_editor)

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
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        editor_frame = ttk.LabelFrame(
            left_frame, text="Editor de Código Assembly")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        editor_inner = ttk.Frame(editor_frame)
        editor_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.gutter = tk.Text(editor_inner, width=6, padx=2, pady=2, takefocus=0,
                              borderwidth=0, background='#f0f0f0', state=tk.DISABLED)
        self.gutter.pack(side=tk.LEFT, fill=tk.Y)

        self.gutter.bind('<MouseWheel>', self._on_gutter_mousewheel)

        self.gutter.bind('<Button-4>', self._on_gutter_mousewheel)
        self.gutter.bind('<Button-5>', self._on_gutter_mousewheel)

        # Code editor
        self.code_editor = scrolledtext.ScrolledText(
            editor_inner, wrap=tk.WORD, width=50, height=30)
        self.code_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.code_editor.tag_configure('current_line', background='#fff59d')
        self.current_highlighted_line = None
        self.addr_line_map = {}
        self.breakpoints = set()

        self.gutter.tag_configure('gutter_bp', foreground='red')
        self.gutter.tag_configure('gutter_arrow', foreground='green')
        self.gutter.bind('<Button-1>', self._on_gutter_click)

        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(control_frame, text="Montar",
                   command=self.assemble_code).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Executar",
                   command=self.run_emulator).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Pausar",
                   command=self.pause_emulator).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Passo",
                   command=self.step_emulator).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Resetar",
                   command=self.reset_cpu).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Carregar ROM",
                   command=self.load_rom).pack(side=tk.LEFT, padx=5)

        # Controles de execução: delay (ms) e toggle highlight
        exec_ctrl = ttk.Frame(left_frame)
        exec_ctrl.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(exec_ctrl, text="Delay (ms):").pack(
            side=tk.LEFT, padx=(0, 4))
        self.delay_ms = tk.IntVar(value=10)
        ttk.Scale(exec_ctrl, from_=0, to=500, variable=self.delay_ms,
                  orient=tk.HORIZONTAL).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.show_highlight = tk.BooleanVar(value=True)
        ttk.Checkbutton(exec_ctrl, text="Destacar linha",
                        variable=self.show_highlight).pack(side=tk.LEFT, padx=8)
        # Alternar NMI (simula interrupção de VBlank da PPU)
        # O NMI (Non-Maskable Interrupt) é usado no NES para sinalizar o início do VBlank,
        # permitindo que o CPU execute tarefas relacionadas à renderização gráfica.
        # Aqui, o checkbox permite ao usuário habilitar ou desabilitar a geração periódica de NMI (~60Hz).
        # Quando ativado, o método _tick_nmi será chamado periodicamente, disparando cpu.nmi().
        # Isso é útil para testar rotinas de VBlank, animações e sincronização de gráficos no emulador.
        self.nmi_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(exec_ctrl, text="Enable NMI (~60Hz)",
                        variable=self.nmi_enabled).pack(side=tk.LEFT, padx=8)

        # Estado da CPU
        cpu_frame = ttk.LabelFrame(right_frame, text="Estado da CPU")
        cpu_frame.pack(fill=tk.X, padx=5, pady=5)

        reg_frame = ttk.Frame(cpu_frame)
        reg_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(reg_frame, text="A:").grid(row=0, column=0, padx=5, pady=2)
        self.reg_a = ttk.Label(reg_frame, text="$00")
        self.reg_a.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(reg_frame, text="X:").grid(row=0, column=2, padx=5, pady=2)
        self.reg_x = ttk.Label(reg_frame, text="$00")
        self.reg_x.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(reg_frame, text="Y:").grid(row=0, column=4, padx=5, pady=2)
        self.reg_y = ttk.Label(reg_frame, text="$00")
        self.reg_y.grid(row=0, column=5, padx=5, pady=2)

        ttk.Label(reg_frame, text="PC:").grid(row=1, column=0, padx=5, pady=2)
        self.reg_pc = ttk.Label(reg_frame, text="$0000")
        self.reg_pc.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(reg_frame, text="SP:").grid(row=1, column=2, padx=5, pady=2)
        self.reg_sp = ttk.Label(reg_frame, text="$FF")
        self.reg_sp.grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(reg_frame, text="Flags:").grid(
            row=2, column=0, padx=5, pady=2)
        self.reg_flags = ttk.Label(reg_frame, text="NV-BDIZC")
        self.reg_flags.grid(row=2, column=1, columnspan=5, padx=5, pady=2)

        # Visualização de Memória
        mem_frame = ttk.LabelFrame(right_frame, text="Memória")
        mem_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.memory_view = scrolledtext.ScrolledText(
            mem_frame, wrap=tk.WORD, width=40, height=15)
        self.memory_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Disassembly
        disasm_frame = ttk.LabelFrame(right_frame, text="Disassembly")
        disasm_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.disasm_view = scrolledtext.ScrolledText(
            disasm_frame, wrap=tk.WORD, width=40, height=10)
        self.disasm_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # PPU Viewer
        ppu_frame = ttk.LabelFrame(right_frame, text="PPU - Pattern Table")
        ppu_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        # Canvas para desenhar a pattern table
        self.ppu_canvas = tk.Canvas(
            ppu_frame, width=256, height=128, bg='black')
        self.ppu_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # PPU status labels (scanline / PPUSTATUS)
        ppu_status_frame = ttk.Frame(ppu_frame)
        ppu_status_frame.pack(fill=tk.X, padx=5, pady=(0, 4))
        ttk.Label(ppu_status_frame, text="PPU Scanline:").pack(side=tk.LEFT)
        self.ppu_scan_label = ttk.Label(ppu_status_frame, text="-")
        self.ppu_scan_label.pack(side=tk.LEFT, padx=(2, 10))
        ttk.Label(ppu_status_frame, text="PPUSTATUS:").pack(side=tk.LEFT)
        self.ppu_status_label = ttk.Label(ppu_status_frame, text="$00")
        self.ppu_status_label.pack(side=tk.LEFT, padx=(2, 4))

        ppu_ctrl = ttk.Frame(ppu_frame)
        ppu_ctrl.pack(fill=tk.X, padx=2, pady=2)
        ttk.Label(ppu_ctrl, text="Table:").pack(side=tk.LEFT, padx=(2, 4))
        self.ppu_table_var = tk.StringVar(value="0")
        self.ppu_table_combo = ttk.Combobox(ppu_ctrl, values=[
            "0", "1"], width=3, textvariable=self.ppu_table_var, state='readonly')
        self.ppu_table_combo.pack(side=tk.LEFT)
        ttk.Label(ppu_ctrl, text="Scale:").pack(side=tk.LEFT, padx=(8, 4))
        self.ppu_scale_var = tk.IntVar(value=3)
        self.ppu_scale_slider = ttk.Scale(
            ppu_ctrl, from_=1, to=6, variable=self.ppu_scale_var, orient=tk.HORIZONTAL)
        self.ppu_scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(ppu_ctrl, text="Renderizar PPU",
                   command=lambda: self._render_ppu()).pack(side=tk.LEFT, padx=4)
        ttk.Button(ppu_ctrl, text="Dump OAM",
                   command=lambda: self._dump_oam()).pack(side=tk.LEFT, padx=4)
        self.show_sprites_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ppu_ctrl, text="Mostrar Sprites (overlay)",
                        variable=self.show_sprites_var).pack(side=tk.LEFT, padx=4)
        self.log_oam_var = tk.BooleanVar(value=False)

        def _on_toggle_log_oam(*args):
            try:
                val = bool(self.log_oam_var.get())
                if hasattr(self, 'ppu') and self.ppu:
                    try:
                        setattr(self.ppu, 'log_oam', val)
                        try:
                            setattr(self.ppu, '_oam_log_count', 0)
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass

        ttk.Checkbutton(ppu_ctrl, text="Log OAM writes",
                        variable=self.log_oam_var).pack(side=tk.LEFT, padx=4)
        try:
            try:
                self.log_oam_var.trace_add('write', _on_toggle_log_oam)
            except Exception:
                self.log_oam_var.trace('w', _on_toggle_log_oam)
        except Exception:
            pass
        try:
            try:
                self.show_sprites_var.trace_add(
                    'write', lambda *args: self._render_ppu())
            except Exception:
                self.show_sprites_var.trace(
                    'w', lambda *args: self._render_ppu())
        except Exception:
            pass

        # Console
        console_frame = ttk.LabelFrame(right_frame, text="Console")
        console_frame.pack(fill=tk.X, padx=5, pady=5)

        self.console = scrolledtext.ScrolledText(
            console_frame, wrap=tk.WORD, width=40, height=5)
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
                messagebox.showerror(
                    "Erro", f"Não foi possível abrir o arquivo: {str(e)}")

    def save_file(self):
        if self.current_file:
            try:
                with open(self.current_file, 'w') as file:
                    content = self.code_editor.get(1.0, tk.END)
                    file.write(content)
                self.log(f"Arquivo salvo: {self.current_file}")
            except Exception as e:
                messagebox.showerror(
                    "Erro", f"Não foi possível salvar o arquivo: {str(e)}")
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
                self.log(f"Arquivo salvo: {file_path}")
            except Exception as e:
                messagebox.showerror(
                    "Erro", f"Não foi possível salvar o arquivo: {str(e)}")

    def assemble_code(self):
        """Assembla o código atual no editor usando Assembler e carrega o binário na memória."""
        source_code = self.code_editor.get(1.0, tk.END)
        try:
            assembler = Assembler()
            binary_data = assembler.assemble(source_code)
            if binary_data:
                self.binary_data = binary_data
                self.log(
                    f"Código montado com sucesso: {len(binary_data)} bytes.")
                self.load_binary_to_memory()

                try:
                    self.addr_line_map = {}
                    self.data_ranges = []
                    current_address = 0
                    origin_set = False
                    for stmt in getattr(assembler, 'statements', []):
                        if getattr(stmt, 'directive', None) == '.ORG':
                            try:
                                addr = assembler._parse_number(
                                    stmt.operands[0])
                                current_address = addr
                                origin_set = True
                            except Exception:
                                pass
                        else:
                            if getattr(stmt, 'mnemonic', None):
                                self.addr_line_map[current_address] = stmt.line
                            if getattr(stmt, 'directive', None) in ('.BYTE', '.DB', '.WORD', '.DW'):
                                size = getattr(stmt, 'size', 0) or 0
                                if size > 0:
                                    self.data_ranges.append(
                                        (current_address, size, stmt.line))
                            size = getattr(stmt, 'size', 0) or 0
                            current_address += size
                except Exception as e:
                    self.log(
                        f"Aviso: falha ao construir mapeamento endereço->linha: {e}")

                self.update_memory_view()
                self.update_disassembly()
                self._refresh_gutter()
            else:
                self.log("Erro ao montar código: saída vazia do assembler.")
        except Exception as e:
            self.log(f"Erro ao montar código: {e}")
            messagebox.showerror("Erro", f"Erro ao montar código: {e}")

    def load_binary_to_memory(self):
        if not self.binary_data:
            return

        self.reset_cpu()

        start_address = 0x8000
        for i, byte in enumerate(self.binary_data):
            self.bus.write(start_address + i, byte)
        try:
            self.bus.write(0xFFFC, start_address & 0xFF)
            self.bus.write(0xFFFD, (start_address >> 8) & 0xFF)
        except Exception:
            pass
        self.cpu.regs.pc = start_address

        self.log(
            f"Código carregado na memória a partir de ${start_address:04X}.")
        self.update_cpu_state()

    def load_rom(self):
        """Abre um arquivo .nes/.bin simples e mapeia PRG ROM em memória (NROM-like)."""
        rom_path = filedialog.askopenfilename(
            filetypes=[("NES/ROM", "*.nes;*.bin"), ("All files", "*.*")])
        if not rom_path:
            return

        try:
            with open(rom_path, 'rb') as f:
                data = f.read()

            prg = b''
            if len(data) >= 16 and data[0:4] == b'NES\x1A':
                prg_size_units = data[4]
                prg_size = prg_size_units * 16384
                # Ignora trainer e flags, pega PRG a partir do offset 16 (+ trainer se presente)
                trainer_present = (data[6] & 0x04) != 0
                prg_start = 16 + (512 if trainer_present else 0)
                prg = data[prg_start:prg_start + prg_size]
            else:
                prg = data

            prg_size = len(prg)
            if prg_size == 0:
                self.log("ROM sem PRG válido ou arquivo vazio.")
                return

            self.reset_cpu()

            try:
                from .mappers import NROMMapper
                mapper = NROMMapper(prg)
                self.bus.install_mapper(mapper)
                # Instalar hardware stub (PPU registers + controllers)
                try:
                    from .hardware_stub import SimpleHardware
                    hw = SimpleHardware()
                    try:
                        if not hasattr(self, 'ppu') or self.ppu is None:
                            try:
                                if 'FullPPU' in globals():
                                    self.ppu = FullPPU()
                                else:
                                    self.ppu = SimplePPU()
                            except Exception:
                                self.ppu = SimplePPU()
                        hw.ppu = self.ppu
                        try:
                            setattr(self.bus, 'ppu', self.ppu)
                        except Exception:
                            pass
                    except Exception:
                        pass
                    hw.map_to_bus(self.bus)
                    try:
                        setattr(self.bus, 'ppu', self.ppu)
                    except Exception:
                        pass
                    try:
                        if hasattr(self.bus, 'enable_write_logging'):
                            self.bus.enable_write_logging(0x2000, 0x2007)
                            self.log(
                                'Bus write logging enabled for PPU registers (0x2000-0x2007).')
                    except Exception:
                        pass
                    self.hw = hw
                except Exception:
                    self.hw = None
                    pass
                try:
                    # data contém todo o arquivo; tentamos extrair CHR após o PRG
                    if len(data) >= 16 and data[0:4] == b'NES\x1A':
                        prg_units = data[4]
                        chr_units = data[5]
                        trainer_present = (data[6] & 0x04) != 0
                        chr_offset = 16 + \
                            (512 if trainer_present else 0) + prg_units * 16384
                        chr_size = chr_units * 8192
                        if chr_size > 0 and len(data) >= chr_offset + chr_size:
                            chr_bytes = data[chr_offset: chr_offset + chr_size]
                            try:
                                if hasattr(self, 'ppu') and self.ppu:
                                    self.ppu.set_chr(chr_bytes)
                                    try:
                                        self._render_ppu()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                except Exception:
                    pass
            except Exception as e:
                self.log(f"Erro ao instalar mapper: {e}")
                return

            self.cpu.regs.pc = 0x8000
            try:
                self.binary_data = bytearray(prg)
            except Exception:
                self.binary_data = None
            self.rom_loaded = True
            self.update_cpu_state()
            self.update_memory_view()
            self.update_disassembly()
            try:
                has_ppu = hasattr(self.bus, 'ppu') and self.bus.ppu is not None
                self.log(f"Debug: bus.ppu attached: {has_ppu}")
            except Exception:
                pass
            self.log(
                f"ROM carregada: {os.path.basename(rom_path)} ({prg_size} bytes) mapeada via NROM.")
            try:
                scale = int(self.ppu_scale_var.get()) if hasattr(
                    self, 'ppu_scale_var') else 3
                pref_w = 32 * 8 * scale + 400
                pref_h = 30 * 8 * scale + 200
                pref_w = min(pref_w, 1920)
                pref_h = min(pref_h, 1080)
                self.root.geometry(f"{pref_w}x{pref_h}")
                try:
                    self.ppu_canvas.config(width=32*8*scale, height=30*8*scale)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                if hasattr(self.bus, 'get_write_log'):
                    wl = self.bus.get_write_log()
                    if wl:
                        self.log(
                            f"Write log sample (first {min(50, len(wl))} entries):")
                        for entry in wl[:50]:
                            if len(entry) >= 3:
                                a, v, pc = entry
                                try:
                                    self.log(
                                        f"  ${a:04X} <= ${v:02X} (instr @ ${pc:04X})")
                                except Exception:
                                    self.log(
                                        f"  ${a:04X} <= ${v:02X} (instr @ {pc})")
                            else:
                                a, v = entry
                                self.log(f"  ${a:04X} <= ${v:02X}")
                    else:
                        self.log("Write log empty after ROM load.")
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar ROM: {str(e)}")

    def run_emulator(self):
        if not getattr(self, 'rom_loaded', False) and not self.binary_data:
            messagebox.showwarning(
                "Aviso", "Nenhum código montado ou ROM carregada para executar.")
            return
        self.running = True
        self.paused = False

        self.log("Iniciando execução (modo automático)...")
        self.root.after(0, self._run_emulation_step)

    def _run_emulation_step(self):
        """Executa um passo (uma instrução) do emulador e agenda o próximo passo via after.

        Isso garante que as atualizações de UI ocorram no thread principal a cada instrução.
        """
        if not self.running or self.paused:
            return

        try:
            delay_ms = max(0, int(self.delay_ms.get()))
            if delay_ms == 0:
                batch_size = 1024
                if not hasattr(self, '_fast_batches_since_ui_update'):
                    self._fast_batches_since_ui_update = 0
                for i in range(batch_size):
                    self.cpu.clock()

                    if self.cpu.regs.pc in self.addr_line_map:
                        curr_line = self.addr_line_map[self.cpu.regs.pc]
                        if curr_line in self.breakpoints:
                            self.paused = True
                            self.log(
                                f"Breakpoint atingido na linha {curr_line}. Execução pausada.")
                            break

                    try:
                        if self.bus.read(self.cpu.regs.pc) == 0x00:
                            self.log(
                                "Instrução BRK encontrada. Execução interrompida.")
                            self.running = False
                            break
                    except Exception:
                        pass

                self._fast_batches_since_ui_update += 1
                if self._fast_batches_since_ui_update >= 4:
                    self._fast_batches_since_ui_update = 0
                    self.update_cpu_state()
                    self.update_memory_view()
                    self.update_disassembly()
                if self.running and not self.paused:
                    self.root.after(1, self._run_emulation_step)
                return
            self.cpu.clock()
            if self.show_highlight.get():
                pc = self.cpu.regs.pc
                line = self.addr_line_map.get(pc)
                if line:
                    self._highlight_source_line(line)
                    self._set_gutter_arrow(line)

            if self.cpu.regs.pc in self.addr_line_map:
                curr_line = self.addr_line_map[self.cpu.regs.pc]
                if curr_line in self.breakpoints:
                    self.paused = True
                    self.log(
                        f"Breakpoint atingido na linha {curr_line}. Execução pausada.")
                    self.update_cpu_state()
                    self.update_memory_view()
                    self.update_disassembly()
                    return

            self.update_cpu_state()
            self.update_memory_view()
            self.update_disassembly()

            if self.bus.read(self.cpu.regs.pc) == 0x00:  # BRK
                self.log("Instrução BRK encontrada. Execução interrompida.")
                self.running = False
                return

            delay_ms = max(0, int(self.delay_ms.get()))
            self.root.after(delay_ms, self._run_emulation_step)
        except Exception as e:
            self.log(f"Erro durante a execução: {str(e)}")
            self.running = False

    def pause_emulator(self):
        if self.running:
            self.paused = True
            self.log("Execução pausada.")

    def step_emulator(self):
        if not getattr(self, 'rom_loaded', False) and not self.binary_data:
            messagebox.showwarning(
                "Aviso", "Nenhum código montado ou ROM carregada para executar.")
            return

        try:
            _ = self.cpu.clock()

            if self.show_highlight.get():
                pc = self.cpu.regs.pc
                line = self.addr_line_map.get(pc)
                if line:
                    self._highlight_source_line(line)
                    self._set_gutter_arrow(line)

            self.update_cpu_state()
            self.update_memory_view()
            self.update_disassembly()

            self.log("Passo executado.")
        except Exception as e:
            self.log(f"Erro durante o passo: {str(e)}")

    def reset_cpu(self):
        self.bus = Bus()
        self.cpu = CPU(self.bus)
        try:
            if 'FullPPU' in globals():
                self.ppu = FullPPU()
            else:
                self.ppu = SimplePPU()
        except Exception:
            try:
                self.ppu = SimplePPU()
            except Exception:
                self.ppu = None
        self.running = False
        self.paused = False
        self.log("CPU resetada.")
        self.update_cpu_state()
        self.update_memory_view()
        try:
            if hasattr(self, 'bus') and self.ppu:
                setattr(self.bus, 'ppu', self.ppu)
                try:
                    if hasattr(self.ppu, 'nmi_callback'):
                        setattr(self.ppu, 'nmi_callback', lambda: getattr(
                            self, 'cpu', None) and self.cpu.nmi())
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.root.bind('<KeyPress>', self._on_key_press)
            self.root.bind('<KeyRelease>', self._on_key_release)
        except Exception:
            pass
        try:
            self.root.after(16, self._tick_nmi)
        except Exception:
            pass
        try:
            try:
                self._last_ppu_vblank = False
            except Exception:
                self._last_ppu_vblank = False
            self.root.after(100, self._update_ppu_view)
        except Exception:
            pass

    def _update_ppu_view(self):
        try:
            should_render = True
            try:
                if hasattr(self, 'ppu') and self.ppu:
                    in_vblank = getattr(self.ppu, 'in_vblank', None)
                    if in_vblank is not None:
                        if in_vblank and not getattr(self, '_last_ppu_vblank', False):
                            should_render = True
                        else:
                            should_render = False
                        self._last_ppu_vblank = bool(in_vblank)
                    else:
                        st = getattr(self.ppu, 'regs', {}).get(0x2002, 0)
                        vbit = bool(st & 0x80)
                        if vbit and not getattr(self, '_last_ppu_vblank', False):
                            should_render = True
                        else:
                            should_render = False
                        self._last_ppu_vblank = vbit
                else:
                    should_render = True
            except Exception:
                should_render = True

            if should_render:
                try:
                    is_full_ppu = getattr(self.ppu, '__class__', None) and getattr(
                        self.ppu.__class__, '__name__', '') == 'FullPPU'
                    display_table = int(self.ppu_table_var.get()) if hasattr(
                        self, 'ppu_table_var') else 0
                    if is_full_ppu:
                        try:
                            self._start_ppu_full_render_worker(display_table)
                        except Exception:
                            try:
                                self.draw_ppu_tiles()
                            except Exception:
                                pass
                    else:
                        try:
                            self.draw_ppu_tiles()
                        except Exception:
                            pass
                except Exception:
                    pass

            try:
                if hasattr(self, 'ppu') and self.ppu:
                    scan = getattr(self.ppu, 'scanline', '-')
                    self.ppu_scan_label.config(text=str(scan))
                    st = getattr(self.ppu, 'regs', {}).get(0x2002, 0)
                    self.ppu_status_label.config(text=f"${st:02X}")
            except Exception:
                pass

            self.root.after(16, self._update_ppu_view)
        except Exception:
            try:
                self.root.after(100, self._update_ppu_view)
            except Exception:
                pass

    def draw_ppu_tiles(self):
        if not hasattr(self, 'ppu') or not self.ppu:
            return
        try:
            # Prefira o grid de alta fidelidade para implementações PPU leves.
            # Para implementações FullPPU pesadas, evite chamar
            # get_name_table_color_grid() de forma síncrona e utilize o
            # renderizador tile_map mais rápido (32x30 tiles) para manter a
            # interface Tkinter responsiva. Isso evita travar o mainloop.
            if hasattr(self.ppu, 'get_name_table_color_grid'):
                is_full_ppu = getattr(self.ppu, '__class__', None) and getattr(
                    self.ppu.__class__, '__name__', '') == 'FullPPU'
                if is_full_ppu:
                    try:
                        tile_map = self.ppu.get_tile_map(
                            int(self.ppu_table_var.get()) if hasattr(self, 'ppu_table_var') else 0)
                        width = 32 * 8
                        height = 30 * 8
                        try:
                            self.ppu_canvas.config(width=width, height=height)
                        except Exception:
                            pass
                        self.ppu_canvas.delete('all')
                        palette = ['#000000', '#555555', '#AAAAAA', '#FFFFFF']
                        for y in range(30):
                            for x in range(32):
                                color = palette[tile_map[y][x] & 0x3]
                                x0 = x * 8
                                y0 = y * 8
                                self.ppu_canvas.create_rectangle(
                                    x0, y0, x0+8, y0+8, outline=color, fill=color)
                        return
                    except Exception:
                        pass
            if hasattr(self.ppu, 'get_name_table_color_grid'):
                try:
                    selected = int(self.ppu_table_var.get()) if hasattr(
                        self, 'ppu_table_var') else 0
                    counts = [0, 0]
                    v = getattr(self.ppu, 'vram', None)
                    if v is not None:
                        for ti in (0, 1):
                            start = (ti & 1) * 0x400
                            chunk = v[start:start+0x400]
                            counts[ti] = sum(1 for b in chunk if b != 0)
                    display_table = selected
                    if counts[selected] == 0 and max(counts) > 0:
                        display_table = 0 if counts[0] >= counts[1] else 1
                        try:
                            if getattr(self, '_last_auto_selected_table', None) != display_table:
                                try:
                                    import logging
                                    logging.getLogger(__name__).debug(
                                        f"EmuladorGUI: auto-selecting PPU table {display_table} (counts={counts})")
                                except Exception:
                                    pass
                                self._last_auto_selected_table = display_table
                        except Exception:
                            pass
                except Exception:
                    display_table = int(self.ppu_table_var.get()) if hasattr(
                        self, 'ppu_table_var') else 0

                grid = self.ppu.get_name_table_color_grid(display_table)
                if not getattr(self, '_ppu_saved_debug', False):
                    try:
                        from PIL import Image
                        import json
                        src_h = len(grid)
                        src_w = len(grid[0]) if src_h else 0
                        if src_h and src_w:
                            img = Image.new('RGB', (src_w, src_h))
                            pix = img.load()
                            for yy in range(src_h):
                                for xx in range(src_w):
                                    col = grid[yy][xx]
                                    try:
                                        if isinstance(col, str) and col.startswith('#') and len(col) >= 7:
                                            r = int(col[1:3], 16)
                                            g = int(col[3:5], 16)
                                            b = int(col[5:7], 16)
                                        else:
                                            r, g, b = (255, 0, 255)
                                    except Exception:
                                        r, g, b = (255, 0, 255)
                                    try:
                                        if pix is not None:
                                            pix[xx, yy] = (r, g, b)
                                        else:
                                            try:
                                                img.putpixel(
                                                    (xx, yy), (r, g, b))
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                            try:
                                img.save('ppu_grid_debug.png')
                            except Exception:
                                pass
                            sample_h = min(16, src_h)
                            sample_w = min(16, src_w)
                            sample = [[grid[y][x] for x in range(
                                sample_w)] for y in range(sample_h)]
                            try:
                                with open('ppu_grid_debug.json', 'w', encoding='utf-8') as jf:
                                    json.dump(sample, jf)
                            except Exception:
                                pass
                            self._ppu_saved_debug = True
                    except Exception:
                        pass
                if not getattr(self, '_ppu_diag_printed', False):
                    try:
                        src_h_diag = len(grid)
                        src_w_diag = len(grid[0]) if src_h_diag else 0
                        sample_rows = [row[:8]
                                       for row in grid[:2]] if src_h_diag else []
                        uniq = len({c for row in grid for c in row}
                                   ) if src_h_diag else 0
                        try:
                            import logging
                            logging.getLogger(__name__).debug(
                                f"PPU_DIAG: grid size={src_h_diag}x{src_w_diag} sample_rows={sample_rows} unique_colors={uniq}")
                        except Exception:
                            pass
                    except Exception:
                        pass
                    self._ppu_diag_printed = True
                src_h = len(grid)
                src_w = len(grid[0]) if src_h else 0
                scale = int(self.ppu_scale_var.get()) if hasattr(
                    self, 'ppu_scale_var') else 2

                try:
                    g_h = len(grid)
                    g_w = len(grid[0]) if g_h else 0
                except Exception:
                    g_h, g_w = 0, 0
                if g_h == 256 and g_w == 240:
                    try:
                        self.log(
                            'Debug: detected transposed PPU grid, transposing to 240x256')
                        grid = [list(row) for row in zip(*grid)]
                        src_h = len(grid)
                        src_w = len(grid[0]) if src_h else 0
                    except Exception:
                        pass

                try:
                    from PIL import Image, ImageTk
                    src_w = src_w or 256
                    src_h = src_h or 240
                    scale = int(self.ppu_scale_var.get()) if hasattr(
                        self, 'ppu_scale_var') else 2

                    pil = Image.new('RGB', (src_w, src_h))
                    pix = pil.load()

                    def _to_rgb(col):
                        try:
                            if isinstance(col, str) and col.startswith('#') and len(col) >= 7:
                                r = int(col[1:3], 16)
                                g = int(col[3:5], 16)
                                b = int(col[5:7], 16)
                                return (r, g, b)
                            if isinstance(col, (tuple, list)) and len(col) >= 3:
                                return (int(col[0]) & 0xFF, int(col[1]) & 0xFF, int(col[2]) & 0xFF)
                            if isinstance(col, int):
                                v = max(0, min(255, col))
                                return (v, v, v)
                        except Exception:
                            pass
                        return (255, 0, 255)

                    for y in range(src_h):
                        row = grid[y]
                        for x in range(src_w):
                            try:
                                rgb = _to_rgb(row[x])
                                if pix is not None:
                                    pix[x, y] = rgb
                                else:
                                    try:
                                        pil.putpixel((x, y), rgb)
                                    except Exception:
                                        pass
                            except Exception:
                                try:
                                    if pix is not None:
                                        pix[x, y] = (255, 0, 255)
                                    else:
                                        pil.putpixel((x, y), (255, 0, 255))
                                except Exception:
                                    pass

                    if scale != 1:
                        try:
                            resample_filter = getattr(
                                Image, 'Resampling', None)
                            if resample_filter is not None:
                                pil = pil.resize(
                                    (src_w*scale, src_h*scale), resample=getattr(resample_filter, 'NEAREST', None) or 0)
                            else:
                                pil = pil.resize((src_w*scale, src_h*scale))
                        except Exception:
                            pil = pil.resize((src_w*scale, src_h*scale))

                    photo = ImageTk.PhotoImage(pil)
                    self.ppu_canvas.delete('all')
                    self._ppu_photo_image = photo
                    self.ppu_canvas.config(
                        width=src_w*scale, height=src_h*scale)
                    self.ppu_canvas.create_image(
                        0, 0, anchor=tk.NW, image=photo)
                    try:
                        if getattr(self, 'show_sprites_var', None) and self.show_sprites_var.get() and hasattr(self.ppu, 'oam'):
                            self.ppu_canvas.delete('ppu_sprite_overlay')
                            oam = getattr(self.ppu, 'oam')
                            for si in range(0, min(len(oam), 256), 4):
                                try:
                                    y = oam[si]
                                    tile = oam[si+1]
                                    attr = oam[si+2]
                                    x = oam[si+3]
                                    if y == 0xFF:
                                        continue
                                    sx = int(x) * scale
                                    sy = int(y) * scale
                                    ex = sx + 8 * scale
                                    ey = sy + 8 * scale
                                    self.ppu_canvas.create_rectangle(
                                        sx, sy, ex, ey, outline='red', width=1, tags=('ppu_sprite_overlay',))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    return
                except Exception:
                    pass

            try:
                from PIL import Image, ImageTk
                if hasattr(self.ppu, 'get_name_table_color_grid'):
                    grid = self.ppu.get_name_table_color_grid(
                        int(self.ppu_table_var.get()) if hasattr(self, 'ppu_table_var') else 0)
                    src_h = len(grid)
                    src_w = len(grid[0]) if src_h else 0
                    scale = int(self.ppu_scale_var.get()) if hasattr(
                        self, 'ppu_scale_var') else 2
                    pil = Image.new('RGB', (src_w, src_h))
                    pix = pil.load()
                    if pix is None:
                        pix = {}
                    for y in range(src_h):
                        row = grid[y]
                        for x in range(src_w):
                            col = row[x]
                            try:
                                if isinstance(col, str) and len(col) >= 7 and col[0] == '#':
                                    r = int(col[1:3], 16)
                                    g = int(col[3:5], 16)
                                    b = int(col[5:7], 16)
                                else:
                                    r, g, b = (255, 0, 255)
                            except Exception:
                                r, g, b = (255, 0, 255)
                            try:
                                pix[x, y] = (r, g, b)
                            except Exception:
                                pass
                    if scale != 1:
                        resample_filter = getattr(Image, 'Resampling', None)
                        if resample_filter is not None:
                            enum_nearest = getattr(
                                resample_filter, 'NEAREST', None)
                            if enum_nearest is not None:
                                try:
                                    pil = pil.resize(
                                        (src_w*scale, src_h*scale), resample=enum_nearest)
                                except Exception:
                                    pil = pil.resize(
                                        (src_w*scale, src_h*scale))
                            else:
                                pil = pil.resize((src_w*scale, src_h*scale))
                        else:
                            nearest = getattr(Image, 'NEAREST', None)
                            if nearest is not None:
                                try:
                                    pil = pil.resize(
                                        (src_w*scale, src_h*scale), resample=nearest)
                                except Exception:
                                    pil = pil.resize(
                                        (src_w*scale, src_h*scale))
                            else:
                                pil = pil.resize((src_w*scale, src_h*scale))
                    photo = ImageTk.PhotoImage(pil)
                    self.ppu_canvas.delete('all')
                    self._ppu_photo_image = photo
                    self.ppu_canvas.config(
                        width=src_w*scale, height=src_h*scale)
                    self.ppu_canvas.create_image(
                        0, 0, anchor=tk.NW, image=photo)
                    return
            except Exception:
                pass

            tile_map = self.ppu.get_tile_map(
                int(self.ppu_table_var.get()) if hasattr(self, 'ppu_table_var') else 0)
            width = 32 * 8
            height = 30 * 8
            try:
                self.ppu_canvas.config(width=width, height=height)
            except Exception:
                pass
            self.ppu_canvas.delete('all')
            palette = ['#000000', '#555555', '#AAAAAA', '#FFFFFF']
            for y in range(30):
                for x in range(32):
                    color = palette[tile_map[y][x] & 0x3]
                    x0 = x * 8
                    y0 = y * 8
                    self.ppu_canvas.create_rectangle(
                        x0, y0, x0+8, y0+8, outline=color, fill=color)
            try:
                if getattr(self, 'show_sprites_var', None) and self.show_sprites_var.get() and hasattr(self.ppu, 'oam'):
                    oam = getattr(self.ppu, 'oam')
                    for si in range(0, min(len(oam), 256), 4):
                        try:
                            y = oam[si]
                            tile = oam[si+1]
                            attr = oam[si+2]
                            x = oam[si+3]
                            if y == 0xFF:
                                continue
                            sx = x
                            sy = y
                            ex = sx + 8
                            ey = sy + 8
                            self.ppu_canvas.create_rectangle(
                                sx, sy, ex, ey, outline='red', width=1)
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            return

    def _tick_nmi(self):
        try:
            if getattr(self, 'nmi_enabled', None) and self.nmi_enabled.get():
                if hasattr(self, 'cpu') and self.cpu:
                    try:
                        self.cpu.nmi()
                    except Exception:
                        pass
        except Exception:
            pass

    def _dump_oam(self):
        """Abre uma pequena janela mostrando as entradas atuais da OAM e opcionalmente salva em um arquivo JSON."""
        try:
            ppu = getattr(self, 'ppu', None)
            oam_attr = getattr(ppu, 'oam', None) if ppu is not None else None
            if not ppu or not oam_attr:
                messagebox.showinfo(
                    "Dump OAM", "PPU OAM vazio ou PPU não disponível.")
                return
            oam = bytes(oam_attr)
            sprites = []
            for i in range(0, min(len(oam), 256), 4):
                y = oam[i]
                tile = oam[i+1]
                attr = oam[i+2]
                x = oam[i+3]
                if y == 0xFF:
                    continue
                sprites.append({
                    'index': i//4,
                    'x': int(x),
                    'y': int(y),
                    'tile': int(tile),
                    'attr': int(attr)
                })

            try:
                import json
                import os
                out_path = os.path.join(os.getcwd(), 'oam_dump.json')
                with open(out_path, 'w', encoding='utf-8') as jf:
                    json.dump(sprites, jf, indent=2)
            except Exception:
                out_path = None

            win = tk.Toplevel(self.root)
            win.title('OAM Dump')
            st = scrolledtext.ScrolledText(win, width=60, height=20)
            st.pack(fill=tk.BOTH, expand=True)
            if not sprites:
                st.insert(tk.END, 'No sprites found in OAM (all Y==0xFF?)\n')
            else:
                for s in sprites:
                    st.insert(
                        tk.END, f"#{s['index']:02d}: X={s['x']:03d} Y={s['y']:03d} tile={s['tile']:03d} attr=0x{s['attr']:02X}\n")
            if out_path:
                st.insert(tk.END, f"\nSaved OAM dump to: {out_path}\n")
            ttk.Button(win, text='Close', command=win.destroy).pack(pady=4)
        except Exception as e:
            messagebox.showerror('Dump OAM', f'Erro durante dump OAM: {e}')
        try:
            self.root.after(16, self._tick_nmi)
        except Exception:
            pass

    def _on_key_press(self, event):
        if not hasattr(self, 'hw') or not self.hw:
            return
        key = event.keysym
        mask = 0
        if key.lower() == 'z':
            mask = 0x01
        elif key.lower() == 'x':
            mask = 0x02
        elif key == 'Return':
            mask = 0x08
        elif key in ('Shift_R', 'Shift_L'):
            mask = 0x04
        elif key == 'Up':
            mask = 0x10
        elif key == 'Down':
            mask = 0x20
        elif key == 'Left':
            mask = 0x40
        elif key == 'Right':
            mask = 0x80
        if mask:
            try:
                self.hw.controller_state[0] |= mask
            except Exception:
                pass

    def _on_key_release(self, event):
        if not hasattr(self, 'hw') or not self.hw:
            return
        key = event.keysym
        mask = 0
        if key.lower() == 'z':
            mask = 0x01
        elif key.lower() == 'x':
            mask = 0x02
        elif key == 'Return':
            mask = 0x08
        elif key in ('Shift_R', 'Shift_L'):
            mask = 0x04
        elif key == 'Up':
            mask = 0x10
        elif key == 'Down':
            mask = 0x20
        elif key == 'Left':
            mask = 0x40
        elif key == 'Right':
            mask = 0x80
        if mask:
            try:
                self.hw.controller_state[0] &= (~mask) & 0xFF
            except Exception:
                pass

    def update_cpu_state(self):
        self.reg_a.config(text=f"${self.cpu.regs.a:02X}")
        self.reg_x.config(text=f"${self.cpu.regs.x:02X}")
        self.reg_y.config(text=f"${self.cpu.regs.y:02X}")
        self.reg_pc.config(text=f"${self.cpu.regs.pc:04X}")
        self.reg_sp.config(text=f"${self.cpu.regs.sp:02X}")

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
        self.memory_view.delete(1.0, tk.END)

        start_address = max(0, self.cpu.regs.pc - 64)
        start_address = start_address & 0xFFF0

        for i in range(16):
            address = start_address + i * 16
            line = f"${address:04X}: "

            for j in range(16):
                byte = self.bus.read(address + j)
                line += f"{byte:02X} "

                if address + j == self.cpu.regs.pc:
                    line = line[:-1] + "*"

            line += "  "
            for j in range(16):
                byte = self.bus.read(address + j)
                if 32 <= byte <= 126:
                    line += chr(byte)
                else:
                    line += "."

            self.memory_view.insert(tk.END, line + "\n")

    def update_disassembly(self):
        self.disasm_view.delete(1.0, tk.END)
        start_address = max(0, self.cpu.regs.pc - 8) & 0xFFFF

        addr = start_address

        def mode_size(mode_fn):
            if mode_fn in (self.cpu.IMP, self.cpu.ACC):
                return 1
            if mode_fn in (self.cpu.IMM, self.cpu.ZP0, self.cpu.ZPX, self.cpu.ZPY,
                           self.cpu.IZX, self.cpu.IZY, self.cpu.REL):
                return 2
            return 3

        def format_operand(mode_fn, base_addr):
            try:
                if mode_fn == self.cpu.IMM:
                    value = self.bus.read(base_addr + 1)
                    return f"#${value:02X}"
                if mode_fn == self.cpu.ZP0:
                    value = self.bus.read(base_addr + 1)
                    return f"${value:02X}"
                if mode_fn == self.cpu.ZPX:
                    value = self.bus.read(base_addr + 1)
                    return f"${value:02X},X"
                if mode_fn == self.cpu.ZPY:
                    value = self.bus.read(base_addr + 1)
                    return f"${value:02X},Y"
                if mode_fn == self.cpu.IZX:
                    value = self.bus.read(base_addr + 1)
                    return f"(${value:02X},X)"
                if mode_fn == self.cpu.IZY:
                    value = self.bus.read(base_addr + 1)
                    return f"(${value:02X}),Y"
                if mode_fn == self.cpu.REL:
                    offset = self.bus.read(base_addr + 1)
                    if offset & 0x80:
                        offset = offset - 0x100
                    target = (base_addr + 2 + offset) & 0xFFFF
                    return f"${target:04X}"
                if mode_fn == self.cpu.ABS:
                    lo = self.bus.read(base_addr + 1)
                    hi = self.bus.read(base_addr + 2)
                    return f"${(hi << 8 | lo):04X}"
                if mode_fn == self.cpu.ABX:
                    lo = self.bus.read(base_addr + 1)
                    hi = self.bus.read(base_addr + 2)
                    return f"${(hi << 8 | lo):04X},X"
                if mode_fn == self.cpu.ABY:
                    lo = self.bus.read(base_addr + 1)
                    hi = self.bus.read(base_addr + 2)
                    return f"${(hi << 8 | lo):04X},Y"
                if mode_fn == self.cpu.IND:
                    lo = self.bus.read(base_addr + 1)
                    hi = self.bus.read(base_addr + 2)
                    return f"(${(hi << 8 | lo):04X})"
            except Exception:
                pass
            return ""

        def _render_ppu(self):
            try:
                self.draw_ppu_tiles()
            except Exception:
                pass

        def _update_ppu_view(self):
            try:
                self.draw_ppu_tiles()
            except Exception:
                pass
            try:
                self.root.after(100, self._update_ppu_view)
            except Exception:
                pass

        for _ in range(16):
            current_address = addr
            data_hit = None
            for (dstart, dsize, dline) in getattr(self, 'data_ranges', []):
                if dstart <= current_address < (dstart + dsize):
                    data_hit = (dstart, dsize, dline)
                    break

            if data_hit:
                dstart, dsize, dline = data_hit
                remaining = (dstart + dsize) - current_address
                bytes_len = min(remaining, 16)
                bytes_repr = " ".join(
                    f"{self.bus.read(current_address + i):02X}" for i in range(bytes_len))
                ascii_repr = "".join(chr(self.bus.read(current_address + i)) if 32 <= self.bus.read(
                    current_address + i) <= 126 else '.' for i in range(bytes_len))
                line = f"${current_address:04X}: {bytes_repr:<48} DATA {ascii_repr}"
                if current_address == self.cpu.regs.pc:
                    line = "> " + line
                else:
                    line = "  " + line
                self.disasm_view.insert(tk.END, line + "\n")
                addr = (addr + bytes_len) & 0xFFFF
                continue
            opcode = self.bus.read(current_address)

            instr_func, mode_fn, _ = self.cpu.lookup[opcode]
            try:
                mnemonic = instr_func.__name__.upper()
            except Exception:
                mnemonic = f"OP{opcode:02X}"

            size = mode_size(mode_fn)

            bytes_repr = " ".join(
                f"{self.bus.read(current_address + i):02X}" for i in range(size))

            operand_text = format_operand(mode_fn, current_address)

            if size == 1:
                line = f"${current_address:04X}: {bytes_repr:<8} {mnemonic} {operand_text}"
            else:
                line = f"${current_address:04X}: {bytes_repr:<8} {mnemonic} {operand_text}"

            if current_address == self.cpu.regs.pc:
                line = "> " + line
            else:
                line = "  " + line

            self.disasm_view.insert(tk.END, line + "\n")

            addr = (addr + size) & 0xFFFF

    def log(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)

    def _highlight_source_line(self, line_no):
        try:
            if self.current_highlighted_line:
                self.code_editor.tag_remove(
                    'current_line', f"{self.current_highlighted_line}.0", f"{self.current_highlighted_line}.end")
        except Exception:
            pass
        try:
            self.code_editor.tag_add(
                'current_line', f"{line_no}.0", f"{line_no}.end")
            self.current_highlighted_line = line_no
            self.code_editor.see(f"{line_no}.0")
        except Exception:
            pass

    def _refresh_gutter(self):
        """Atualiza o conteúdo da barra lateral (gutter) com números de linha e marcadores de breakpoint."""
        total_lines = int(self.code_editor.index('end-1c').split('.')[0])
        try:
            cur_view = self.gutter.yview()
        except Exception:
            cur_view = (0.0, 1.0)
        self.gutter.config(state=tk.NORMAL)
        self.gutter.delete(1.0, tk.END)
        for i in range(1, total_lines + 1):
            marker = '   '
            if i in self.breakpoints:
                marker = '● '
            line_text = f"{marker}{i:3d}\n"
            self.gutter.insert(tk.END, line_text)
        self.gutter.config(state=tk.DISABLED)
        try:
            self.gutter.yview_moveto(cur_view[0])
        except Exception:
            pass

    def _on_gutter_mousewheel(self, event):
        """Rola o editor principal quando o usuário rola sobre a barra lateral (gutter)."""
        try:
            if hasattr(event, 'delta') and event.delta:
                lines = -int(event.delta / 120)
                self.code_editor.yview_scroll(lines, 'units')
            elif event.num == 4:
                self.code_editor.yview_scroll(-1, 'units')
            elif event.num == 5:
                self.code_editor.yview_scroll(1, 'units')
        except Exception:
            pass
        try:
            top = self.code_editor.yview()[0]
            self.gutter.yview_moveto(top)
        except Exception:
            pass
        return 'break'

    def _sync_gutter_with_editor(self):
        """Verificação leve para manter a barra lateral (gutter) alinhada verticalmente com o editor de código.

        Isso é robusto para interações (roda do mouse, arrastar barra de rolagem, navegação por teclado)
        porque observa a fração yview do editor e a espelha na barra lateral.
        """
        try:
            top = self.code_editor.yview()[0]
            if self._last_editor_y is None or abs(top - self._last_editor_y) > 1e-6:
                try:
                    self.gutter.yview_moveto(top)
                except Exception:
                    pass
                self._last_editor_y = top
        except Exception:
            pass
        try:
            self.root.after(50, self._sync_gutter_with_editor)
        except Exception:
            pass

    def _on_gutter_click(self, event):
        """Alterna o breakpoint na linha clicada na barra lateral (gutter)."""
        index = self.gutter.index(f"@{event.x},{event.y}")
        line_no = int(index.split('.')[0])
        if line_no in self.breakpoints:
            self.breakpoints.remove(line_no)
            self.log(f"Breakpoint removido na linha {line_no}.")
        else:
            self.breakpoints.add(line_no)
            self.log(f"Breakpoint adicionado na linha {line_no}.")
        self._refresh_gutter()

    def _set_gutter_arrow(self, line_no):
        """Coloca um marcador de seta na barra lateral (gutter) na linha de código fonte indicada."""
        self._refresh_gutter()
        try:
            self.gutter.config(state=tk.NORMAL)
            self.gutter.delete(f"{line_no}.0", f"{line_no}.0 lineend")
            marker = '▶ '
            line_text = f"{marker}{line_no:3d}\n"
            self.gutter.insert(f"{line_no}.0", line_text)
            self.gutter.config(state=tk.DISABLED)
        except Exception:
            pass

    def show_about(self):
        messagebox.showinfo(
            "Sobre",
            "Emulador 6502\n\n"
            "Um emulador completo para o processador MOS 6502.\n"
            "Desenvolvido como parte do projeto de emulação de sistemas retro.\n\n"
            "© 2025 Projeto 6502"
        )

    def _render_ppu(self):
        """Função auxiliar para renderizar a tabela de padrões selecionada usando os controles atuais da interface."""
        try:
            table = int(self.ppu_table_var.get()) if hasattr(
                self, 'ppu_table_var') else 0
            scale = int(self.ppu_scale_var.get()) if hasattr(
                self, 'ppu_scale_var') else 2
            if hasattr(self, 'ppu') and self.ppu and hasattr(self, 'ppu_canvas'):
                self.ppu.render_pattern_table(
                    self.ppu_canvas, table_index=table, scale=scale)
        except Exception:
            pass

    def _start_ppu_full_render_worker(self, display_table: int):
        """Inicia uma thread em segundo plano para renderizar a tabela de nomes completa da PPU em uma imagem PIL.

        Isso evita bloquear o mainloop do Tkinter durante renderizações FullPPU custosas.
        O worker agenda a atualização final do PhotoImage na thread principal via root.after.
        """
        try:
            if getattr(self, '_ppu_full_render_running', False):
                return
            self._ppu_full_render_running = True

            def _worker(table_idx: int):
                try:
                    grid = None
                    try:
                        ppu_obj = getattr(self, 'ppu', None)
                        if ppu_obj is None:
                            return
                        grid = ppu_obj.get_name_table_color_grid(table_idx)
                    except Exception:
                        grid = None
                    if not grid:
                        return
                    try:
                        from PIL import Image
                        src_h = len(grid)
                        src_w = len(grid[0]) if src_h else 0
                        pil = Image.new('RGB', (src_w, src_h))
                        pix = pil.load()
                        use_pix = pix is not None
                        for yy in range(src_h):
                            row = grid[yy]
                            for xx in range(src_w):
                                col = row[xx]
                                try:
                                    if isinstance(col, str) and col.startswith('#') and len(col) >= 7:
                                        r = int(col[1:3], 16)
                                        g = int(col[3:5], 16)
                                        b = int(col[5:7], 16)
                                    elif isinstance(col, (tuple, list)) and len(col) >= 3:
                                        r, g, b = int(col[0]) & 0xFF, int(
                                            col[1]) & 0xFF, int(col[2]) & 0xFF
                                    else:
                                        r, g, b = (255, 0, 255)
                                except Exception:
                                    r, g, b = (255, 0, 255)
                                if use_pix:
                                    try:
                                        pix[xx, yy] = (r, g, b)
                                    except Exception:
                                        try:
                                            pil.putpixel((xx, yy), (r, g, b))
                                        except Exception:
                                            pass
                                else:
                                    try:
                                        pil.putpixel((xx, yy), (r, g, b))
                                    except Exception:
                                        pass
                        try:
                            scale = int(self.ppu_scale_var.get()) if hasattr(
                                self, 'ppu_scale_var') else 1
                        except Exception:
                            scale = 1
                        if scale != 1:
                            try:
                                pil = pil.resize(
                                    (src_w * scale, src_h * scale))
                            except Exception:
                                pass
                        try:
                            self.root.after(
                                0, lambda im=pil: self._apply_ppu_full_render(im))
                        except Exception:
                            pass
                    except Exception:
                        pass
                finally:
                    try:
                        self._ppu_full_render_running = False
                    except Exception:
                        pass

            t = threading.Thread(target=_worker, args=(
                display_table,), daemon=True)
            t.start()
        except Exception:
            try:
                self._ppu_full_render_running = False
            except Exception:
                pass

    def _apply_ppu_full_render(self, pil_image):
        """Aplica uma imagem PIL ao canvas da PPU na thread principal do Tkinter."""
        try:
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(pil_image)
            self.ppu_canvas.delete('all')
            self._ppu_photo_image = photo
            self.ppu_canvas.config(width=pil_image.width,
                                   height=pil_image.height)
            self.ppu_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = EmuladorGUI(root)
    root.mainloop()
