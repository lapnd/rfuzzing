import random
import re
import subprocess

import convention


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
        # There is a higher chance of generating shit numbers
        if random.random() < convention.p_shit_numbers:
            return hex(random.choice(convention.shit_numbers))
        else:
            return hex(random.randint(0, (1 << 64) - 1))

    def rand_idle_register(self):
        return convention.registers[random.randint(0, 30)]

    def rand_instruction(self):
        choose_rule = random.choice(convention.instruction_rule)
        if choose_rule[1] == 'I':
            opcode = choose_rule[0]
            rd = self.rand_idle_register()
            rs = self.rand_idle_register()
            self.writer.line(f'{opcode} {rd}, {rs}')
            self.writer.line(f'add t6, t6, {rd}')
        if choose_rule[1] == 'R':
            opcode = choose_rule[0]
            rd = self.rand_idle_register()
            rs1 = self.rand_idle_register()
            rs2 = self.rand_idle_register()
            self.writer.line(f'{opcode} {rd}, {rs1}, {rs2}')
            self.writer.line(f'add t6, t6, {rd}')
        if choose_rule[1] == 'R4':
            pass

    def loop(self):
        self.writer.line('.global _start')
        self.writer.line('_start:')

        # Fuzzer loop
        for _ in range(128):
            # Starts by initializing a registers: x0 to x31
            for i in range(32):
                self.writer.line(f'li {convention.registers[i]}, {self.rand_u256()}')
            for _ in range(1024):
                self.rand_instruction()

        # Returns checksum
        self.writer.line('addi a0, t6, 0')
        self.writer.line('li a7, 93')
        self.writer.line('ecall')
        self.writer.f.close()


def main():
    for i in range(1 << 32):
        print('generation', i)
        f = Fuzzer()
        f.loop()

        subprocess.call('/root/app/riscv64b/bin/riscv64-unknown-elf-as -march=rv64gcb -o main.o main.S', shell=True)
        subprocess.call('/root/app/riscv64b/bin/riscv64-unknown-elf-ld -o main main.o', shell=True)
        subprocess.call('rm main.o', shell=True)

        int_output = subprocess.getoutput('/src/ckb-vm-run/target/release/int main')
        int_match = re.match(r'int exit=Ok\((?P<code>-?\d+)\) cycles=\d+', int_output)
        int_exitcode = int(int_match.group('code'))

        asm_output = subprocess.getoutput('/src/ckb-vm-run/target/release/asm main')
        asm_match = re.match(r'asm exit=Ok\((?P<code>-?\d+)\) cycles=\d+', asm_output)
        asm_exitcode = int(asm_match.group('code'))

        aot_output = subprocess.getoutput('/src/ckb-vm-run/target/release/aot main')
        aot_match = re.match(r'aot exit=Ok\((?P<code>-?\d+)\) cycles=\d+', aot_output)
        aot_exitcode = int(aot_match.group('code'))

        cmp_exitcode = subprocess.call('/root/app/riscv64b/bin/spike --isa RV64GCB pk /src/rfuzzing/main', shell=True)
        if cmp_exitcode >= 128:
            cmp_exitcode = cmp_exitcode - 256

        assert int_exitcode == asm_exitcode
        assert int_exitcode == aot_exitcode
        assert int_exitcode == cmp_exitcode


if __name__ == '__main__':
    main()
