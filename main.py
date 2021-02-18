import random
import re
import subprocess

import convention

c_binary_as = '/root/app/riscv64b/bin/riscv64-unknown-elf-as'
c_binary_ld = '/root/app/riscv64b/bin/riscv64-unknown-elf-ld'
c_binary_riscv_int = '/src/ckb-vm-run/target/release/int'
c_binary_riscv_asm = '/src/ckb-vm-run/target/release/asm'
c_binary_riscv_aot = '/src/ckb-vm-run/target/release/aot'
c_binary_riscv_spike = '/root/app/riscv64b/bin/spike'

class Writer:

    def __init__(self, name: str):
        self.name = name
        self.f = open(self.name, 'w')

    def line(self, line: str):
        self.f.write(line)
        self.f.write('\n')


class Fuzzer:

    def __init__(self):
        self.writer = Writer('main.S')

    def rand_u256(self):
        # There is a higher chance of generating best numbers
        if random.random() < convention.p_best_numbers:
            return random.choice(convention.best_numbers)
        else:
            return random.randint(0, (1 << 64) - 1)

    def rand_idle_register(self):
        return random.choice(convention.idle_registers)

    def rand_instruction(self):
        choose_rule = random.choice(convention.instruction_rule)
        opcode = choose_rule[0]
        args = []
        for i in choose_rule[1]:
            if i == 'r':
                args.append(self.rand_idle_register())
                continue
            if i == 'u5':
                args.append(hex(self.rand_u256() % 32))
                continue
            if i == 'u6':
                args.append(hex(self.rand_u256() % 64))
                continue
            if i == 'u7':
                args.append(hex(self.rand_u256() % 128))
                continue
            assert 0
        self.writer.line(f'{opcode} {", ".join(args)}')
        self.writer.line(f'add t6, t6, {args[0]}')

    def loop(self):
        self.writer.line('.global _start')
        self.writer.line('_start:')

        # Fuzzer loop
        for _ in range(32):
            # Starts by initializing registers: x0 to x30
            for i in convention.registers:
                self.writer.line(f'li {i}, {hex(self.rand_u256())}')
            # Randomly add a nop to change the index of the instruction
            for _ in range(random.randint(0, 1)):
                self.writer.line('nop')
            # Da da da!
            for _ in range(1024):
                self.rand_instruction()

        # Returns checksum
        self.writer.line('')
        self.writer.line('addi a0, t6, 0')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 16')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 24')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 32')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 40')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 48')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 56')
        self.writer.line('add a0, a0, t6')
        self.writer.line('li a7, 93')
        self.writer.line('ecall')
        self.writer.f.close()


def main():
    for i in range(1 << 32):
        print('generation', i)
        f = Fuzzer()
        f.loop()

        subprocess.call(f'{c_binary_as} -march=rv64gcb -o main.o main.S', shell=True)
        subprocess.call(f'{c_binary_ld} -o main main.o', shell=True)

        int_output = subprocess.getoutput(f'{c_binary_riscv_int} main')
        int_match = re.match(r'int exit=Ok\((?P<code>-?\d+)\) cycles=\d+', int_output)
        int_exitcode = int(int_match.group('code'))

        asm_output = subprocess.getoutput(f'{c_binary_riscv_asm} main')
        asm_match = re.match(r'asm exit=Ok\((?P<code>-?\d+)\) cycles=\d+', asm_output)
        asm_exitcode = int(asm_match.group('code'))

        aot_output = subprocess.getoutput(f'{c_binary_riscv_aot} main')
        aot_match = re.match(r'aot exit=Ok\((?P<code>-?\d+)\) cycles=\d+', aot_output)
        aot_exitcode = int(aot_match.group('code'))

        cmp_exitcode = subprocess.call(f'{c_binary_riscv_spike} --isa RV64GCB pk main', shell=True)
        if cmp_exitcode >= 128:
            cmp_exitcode = cmp_exitcode - 256

        assert int_exitcode == asm_exitcode
        assert int_exitcode == aot_exitcode
        assert int_exitcode == cmp_exitcode


if __name__ == '__main__':
    main()
