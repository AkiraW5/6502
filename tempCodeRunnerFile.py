 def ADC(self, value):
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