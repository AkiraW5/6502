import unittest
from Cpu import CPU
from Cpu import Bus

class TestCPU(unittest.TestCase):
    def setUp(self):
        self.bus = Bus()
        self.cpu = CPU(self.bus)

    def test_ADC(self):
        self.cpu.registers.update_register('A', 0x10)
        self.cpu.bus.write(0x0100, 0x69)  # ADC opcode
        self.cpu.bus.write(0x0101, 0x05)  # value to add
        self.cpu.execute(0x69, 'Imm')
        self.assertEqual(self.cpu.registers.get_register('A'), 0x15)
        self.assertEqual(self.cpu.registers.get_flag('C'), 0)
        self.assertEqual(self.cpu.registers.get_flag('Z'), 0)
        self.assertEqual(self.cpu.registers.get_flag('N'), 0)

    def test_AND(self):
        self.cpu.registers.update_register('A', 0x0F)
        self.cpu.bus.write(0x0100, 0x29)  # AND opcode
        self.cpu.bus.write(0x0101, 0x0A)  # value to AND
        self.cpu.execute(0x29, 'Imm')
        self.assertEqual(self.cpu.registers.get_register('A'), 0x0A)
        self.assertEqual(self.cpu.registers.get_flag('Z'), 0)
        self.assertEqual(self.cpu.registers.get_flag('N'), 0)

    def test_ASL(self):
        self.cpu.registers.update_register('A', 0x80)
        self.cpu.bus.write(0x0100, 0x0A)  # ASL opcode
        self.cpu.execute(0x0A, 'A')
        self.assertEqual(self.cpu.registers.get_register('A'), 0x00)
        self.assertEqual(self.cpu.registers.get_flag('C'), 1)
        self.assertEqual(self.cpu.registers.get_flag('Z'), 1)
        self.assertEqual(self.cpu.registers.get_flag('N'), 0)

    def test_LDA(self):
        self.cpu.bus.write(0x0100, 0xA9)  # LDA opcode
        self.cpu.bus.write(0x0101, 0x42)  # value to load
        self.cpu.execute(0xA9, 'Imm')
        self.assertEqual(self.cpu.registers.get_register('A'), 0x42)
        self.assertEqual(self.cpu.registers.get_flag('Z'), 0)
        self.assertEqual(self.cpu.registers.get_flag('N'), 0)

    def test_STA(self):
        self.cpu.registers.update_register('A', 0x55)
        self.cpu.bus.write(0x0100, 0x85)  # STA opcode
        self.cpu.bus.write(0x0101, 0x10)  # memory address
        self.cpu.execute(0x85, 'ZP')
        self.assertEqual(self.cpu.bus.read(0x0010), 0x55)

if __name__ == '__main__':
    unittest.main()