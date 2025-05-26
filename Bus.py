class Bus:
    """Representa o barramento de memória, conectando CPU e RAM."""
    def __init__(self):
        """Inicializa a memória RAM com 64KB (0x0000 - 0xFFFF) de zeros."""
        self.ram = bytearray(64 * 1024)

    def read(self, address):
        """Lê um byte da memória no endereço especificado."""
        address &= 0xFFFF
        return self.ram[address]

    def read_word(self, address):
        """Lê uma palavra (16 bits, little-endian) da memória."""
        address &= 0xFFFF
        low_byte = self.read(address)
        high_byte = self.read((address + 1) & 0xFFFF)
        return (high_byte << 8) | low_byte

    def write(self, address, value):
        """Escreve um byte na memória no endereço especificado."""
        address &= 0xFFFF
        value &= 0xFF
        self.ram[address] = value
