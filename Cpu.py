class Registers:
    def __init__(self):
        self.initialize_registers()

    def initialize_registers(self):
        self.registers = {
            'A': 0, # Accumulator
            'X': 0, # Register X
            'Y': 0, # Register Y
            'SP': 0xFF, # Stack Pointer
            'PC': 0, # Program Counter
            'P' : { # Status Register
                'C': 0x01, # Carry
                'Z': 0x02, # Zero
                'I': 0x04, # Interrupt Disable
                'D': 0x08, # Decimal Mode
                'B': 0x10, # Break Command
                'V': 0x20, # Overflow
                'N': 0x80, # Negative

            },
        }

    def reset(self, pc):
        self.initialize_registers()
        self.registers['PC'] = pc

    def update_register(self, register, value):
                if register in self.registers:
                    self.registers[register] = value
                else:
                    raise ValueError(f"Register {register} not found.")
                
    def get_register(self, register):
        if register in self.registers:
            return self.registers[register]
        else:
            raise ValueError(f"Register {register} not found.")
        
    def update_flag(self, flag, value):
        if flag in self.registers['P']:
            self.registers['P'][flag] = value
        else:
            raise ValueError(f"Flag {flag} not found.")
        
    def get_flag(self, flag):
        if flag in self.registers['P']:
            return self.registers['P'][flag]
        else:
            raise ValueError(f"Flag {flag} not found.")
            

class Bus:
    def __init__(self):
        self.memory = [0x00] * 64 * 1024

    def read(self, address):
        if address < 0x0000 or address > 0xFFFF:
            raise ValueError(f"Address {address} out of bounds")
        return self.memory[address]
    
    def read_word(self, address):
        if address < 0x0000 or address > 0xFFFE:
            raise ValueError(f"Address {address} out of bounds")
        low_byte = self.memory[address]
        high_byte = self.memory[address + 1]
        return (high_byte << 8) | low_byte
    
    def write(self, address, value):
        if address < 0x0000 or address > 0xFFFF:
            raise ValueError(f"Address {address} out of bounds")
        self.memory[address] = value


class CPU:
    def __init__(self, bus):
        self.bus = bus
        self.running = True
        self.registers = Registers()
        self.bus = Bus()
        self.halted = False
        self.opcode_table = {
            'ADC': ('v', [(0x69, 'Imm', 2), (0x65, 'ZP', 3), (0x75, 'ZX', 4), (0x6D, 'A', 4), (0x7D, 'AX', 4), (0x79, 'AY', 4), (0x61, 'IX', 6), (0x71, 'IY', 5)]),

            'AND': ('a', [(0x29, 'Imm', 2), (0x25, 'ZP', 3), (0x35, 'ZX', 4), (0x2D, 'A', 4), (0x3D, 'AX', 4), (0x39, 'AY', 4), (0x21, 'IX', 6), (0x31, 'IY', 5)]),

            'ASL': ('a', [(0x0A, 'A', 2), (0x06, 'ZP', 5), (0x16, 'ZX', 6), (0x0E, 'A', 6), (0x1E, 'AX', 7)]),

            'LDA': ('v', [(0xA9, 'Imm', 2), (0xA5, 'ZP', 3), (0xB5, 'ZX', 4), (0xAD, 'A', 4), (0xBD, 'AX', 4), (0xB9, 'AY', 4), (0xA1, 'IX', 6), (0xB1, 'IY', 5)]),

            'STA': ('a', [(0x85, 'ZP', 3), (0x95, 'ZX', 4), (0x8D, 'A', 4), (0x9D, 'AX', 4), (0x99, 'AY', 4), (0x81, 'IX', 6), (0x91, 'IY', 5)]),

        }
        self.addressing_modes = {
            'Imm': self.fetch_byte,
            'ZP': self.zero_page_address,
            'ZX': self.zero_page_x_address,
            'ZY': self.zero_page_y_address,
            'A': self.absolute_address,
            'AX': self.absolute_x_address,
            'AY': self.absolute_y_address,
            'I': self.indirect_address,
            'IX': self.indirect_x_address,
            'IY': self.indirect_y_address,
        }

    def reset(self):
        # Redefine all registers to initial values
        for register in self.registers.registers:
            if register != 'P':
                self.registers.update_register(register, 0)
            else:
                for flag in self.registers.registers['P']:
                    self.registers.update_flag(flag, 0)
        self.registers.reset(self.bus.read(0xFFFC) | (self.bus.read(0xFFFD) << 8))

    def clear_flag(self, flag):
        if flag in self.registers['P']:
            self.registers['P'][flag] = 0
        else:
            raise ValueError(f"Flag {flag} not found.")
        
    def abort (self):
        # Push PC and P to stack
        self.push_stack_word(self.registers['PC'])
        self.push_stack(self.registers['P'])

        # Set I flag to 1
        self.registers['P']['I'] = 1

        # Read address from 0xFFFE and 0xFFFF
        self.registers['PC'] = self.bus.read(0xFFFE) | (self.bus.read(0xFFFF) << 8)

    def nmi(self):
        # Push PC and P to stack
        self.push_stack_word(self.registers['PC'])
        self.push_stack(self.registers['P'])

        # Set I flag to 1
        self.registers['P']['I'] = 1

        # Read address from 0xFFFA and 0xFFFB
        self.registers['PC'] = self.bus.read(0xFFFA) | (self.bus.read(0xFFFB) << 8)

    def irq_brk(self):
        # Verify if Interrupt is Maskable
        if self.registers['P']['I'] == 0:
            # Push PC and P to stack
            self.push_stack_word(self.registers['PC'])
            self.push_stack(self.registers['P'])

            # Set I flag to 1
            self.registers['P']['I'] = 1

            # Read address from 0xFFFE and 0xFFFF
            self.registers['PC'] = self.bus.read(0xFFFE) | (self.bus.read(0xFFFF) << 8)

    def handle_interrupt(self, interrupt_type):
        if interrupt_type == 'RESET':
            self.reset()
        elif interrupt_type == 'ABORT':
            self.abort()
        elif interrupt_type == 'NMI':
            self.nmi()
        elif interrupt_type == 'IRQ' or interrupt_type == 'BRK':
            self.irq_brk()
            pass
        else:
            raise ValueError(f"Interrupt type {interrupt_type} not found.")

    def fetch_byte(self):
        value = self.bus.read(self.registers.get_register('PC'))
        self.registers.update_register('PC', self.registers.get_register('PC') + 1)
        return value

    def fetch_word(self):
        low_byte = self.fetch_byte()
        high_byte = self.fetch_byte()
        return (high_byte << 8) | low_byte
    
    def push_stack(self, value):
        sp = self.registers.get_register('SP')
        self.bus.write(0x0100 + sp, value)
        self.registers.update_register('SP', sp - 1)

    def push_stack_word(self, value):
        high_byte = (value & 0xFF00) >> 8
        low_byte = value & 0x00FF
        self.push_stack(high_byte)
        self.push_stack(low_byte)

    def pop_stack(self):
        sp = self.registers.get_register('SP') + 1
        value = self.bus.read(0x0100 + sp)
        self.registers.update_register('SP', sp)
        return value
    
    def pop_stack_word(self):
        low_byte = self.pop_stack()
        high_byte = self.pop_stack()
        return (high_byte << 8) | low_byte

    def execute(self, opcode, addressing_mode):
        print(f"Modo de endereçamento: {addressing_mode}")
        if addressing_mode == 'immediate':
            value = self.fetch_byte()
        elif addressing_mode == 'zero_page':
            address = self.zero_page_address()
            value = self.read_byte(address)
        elif addressing_mode == 'absolute':
            address = self.absolute_address()
            value = self.read_byte(address)
        # adicione mais condições conforme necessário
        # ...

        # execute a instrução
        instruction = self.decode_instruction(opcode)
        getattr(self, instruction)(value)

    def ADC(self):
        value = self.fetch_byte()
        a = self.registers.get_register('A')
        c = self.registers.get_flag('C')
        result = a + value + c
        self.registers.update_register('A', result & 0xFF)
        self.registers.update_flag('C', 1 if result > 0xFF else 0)
        self.registers.update_flag('Z', 1 if (result & 0xFF) == 0 else 0)
        self.registers.update_flag('N', 1 if (result & 0x80) != 0 else 0)

    def AND(self, value):
        a = self.registers.get_register('A')
        result = a & value
        self.registers.update_register('A', result)
        self.registers.update_flag('Z', 1 if result == 0 else 0)
        self.registers.update_flag('N', 1 if (result & 0x80) != 0 else 0)

    def ASL(self, value):
        result = value << 1
        self.registers.update_flag('C', 1 if (result & 0x80) != 0 else 0)
        self.registers.update_flag('Z', 1 if (result & 0xFF) == 0 else 0)
        self.registers.update_flag('N', 1 if (result & 0x80) != 0 else 0)
        return result & 0xFF
    
    def LDA(self, value):
        value = int(value)
        self.registers.update_register('A', value)
        self.registers.update_flag('Z', 1 if value == 0 else 0)
        self.registers.update_flag('N', 1 if (value & 0x80) != 0 else 0)
    
    def STA(self, addressing_mode):
        value = self.registers.get_register('A')

        if addressing_mode == 'ZP':  # Zero Page
            addr = self.fetch_byte()
            self.memory[addr] = value
        elif addressing_mode == 'ZX':  # Zero Page, X
            addr = self.fetch_byte() + self.registers.get_register('X')
            self.memory[addr] = value
        elif addressing_mode == 'A':  # Absoluto
            addr = self.fetch_word()
            self.memory[addr] = value
        elif addressing_mode == 'AX':  # Absoluto, X
            addr = self.fetch_word() + self.registers.get_register('X')
            self.memory[addr] = value
        elif addressing_mode == 'AY':  # Absoluto, Y
            addr = self.fetch_word() + self.registers.get_register('Y')
            self.memory[addr] = value
        elif addressing_mode == 'IX':  # Indireto, X
            base = self.fetch_byte() + self.registers.get_register('X')
            addr = self.memory[base] + (self.memory[(base + 1) % 0x100] << 8)
            self.memory[addr] = value
        elif addressing_mode == 'IY':  # Indireto, Y
            base = self.fetch_byte()
            addr = self.memory[base] + (self.memory[(base + 1) % 0x100] << 8) + self.registers.get_register('Y')
            self.memory[addr] = value
        else:
            raise ValueError(f'Modo de endereçamento {addressing_mode} não suportado')


    def read_pc(self):
        value = self.bus.read(self.registers.get_register('PC'))
        self.registers.update_register('PC', self.registers.get_register('PC') + 1)
        return value

    def read_word_pc(self):
        value = self.bus.read_word(self.registers.get_register('PC'))
        self.registers.update_register('PC', self.registers.get_register('PC') + 2)  # increment by 2 because we're reading a word
        return value

    def zero_page_address(self):
        return self.read_pc()

    def zero_page_x_address(self):
        return (self.read_pc() + self.registers['X']) & 0xFF

    def zero_page_y_address(self):
        return (self.read_pc() + self.registers['Y']) & 0xFF

    def absolute_address(self):
        return self.read_word_pc()

    def absolute_x_address(self):
        return (self.read_word_pc() + self.registers['X']) & 0xFFFF

    def absolute_y_address(self):
        return (self.read_word_pc() + self.registers['Y']) & 0xFFFF

    def indirect_address(self):
        return self.bus.read_word(self.read_word_pc())

    def indirect_x_address(self):
        return self.bus.read_word((self.read_pc() + self.registers['X']) & 0xFF)

    def indirect_y_address(self):
        return (self.bus.read_word(self.read_pc()) + self.registers['Y']) & 0xFFFF
    
    def fetch_address(self, mode):
        if mode in self.addressing_modes:
            return self.addressing_modes[mode]()
        else:
            raise ValueError(f"Addressing mode {mode} not found.")


    def run(self):
        while not self.halted:
            opcode = self.fetch_byte()
            if opcode in self.addressing_modes:
                addressing_mode = self.addressing_modes[opcode]  # determine the addressing mode
                self.execute(opcode, addressing_mode)
            else:
                print(f"Opcode {opcode} não encontrado.")
                break  # or continue, depending on what you want to do when an unknown opcode is encountered

    def print_registers(self):
        for register, value in self.registers.registers.items():
            if register != 'P':
                print(f"{register}: {value}")
            else: 
                print('P:')
                for flag, value in self.registers.registers['P'].items():
                    print(f"\t{flag}: {value}")


    def load_and_execute_program(self, filename):
        address = 0x0100

        with open(filename, 'r') as file:
            for line in file:
                words = line.split()
                for word in words:
                    opcode = int(word, 16)
                    self.bus.write(address, opcode)
                    address += 1

        self.registers.update_register('PC', 0x0100)
        self.run()

with open('program.txt', 'w') as file:
    file.write('A9 01 8D 00 02 A9 05 8D 01 02 A9 08 8D 02 02')

bus = Bus()
cpu = CPU(bus)
cpu.load_and_execute_program('program.txt')