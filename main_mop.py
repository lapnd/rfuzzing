import random
import re
import subprocess

import common
import convention

c_binary_as = '/opt/riscv64b/bin/riscv64-unknown-elf-as'
c_binary_as_args = '-march=rv64gcb'
c_binary_ld = '/opt/riscv64b/bin/riscv64-unknown-elf-ld'
c_binary_riscv_int = '/src/ckb-vm-run/target/release/int64'
c_binary_riscv_asm = '/src/ckb-vm-run/target/release/asm'
c_binary_riscv_aot = '/src/ckb-vm-run/target/release/aot'
c_binary_riscv_spike = '/opt/riscv64b/bin/spike'
c_binary_riscv_spike_args = '--isa RV64GCB /opt/riscv64b/riscv64-unknown-elf/bin/pk'


class Fuzzer:

    def __init__(self):
        self.writer = common.Writer('main.S')

    def rand_u64(self):
        # There is a higher chance of generating best numbers
        if random.random() < convention.p_best_numbers:
            return random.choice(convention.best_numbers)
        else:
            return random.randint(0, (1 << 64) - 1)

    def rand_idle_register(self):
        return random.choice(convention.idle_registers)

    def rand_instruction(self):
        choose_rule = random.choice(convention.instruction_rule_mop)
        for e in choose_rule:
            opcode = e[0]
            args = []
            for i in e[1]:
                if i == 'r':
                    args.append(self.rand_idle_register())
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
            for i in convention.idle_registers:
                self.writer.line(f'li {i}, {hex(self.rand_u64())}')
            # Randomly add a nop to change the index of the instruction
            for _ in range(random.randint(0, 1)):
                self.writer.line('nop')
            # Da da da!
            for _ in range(1024):
                self.rand_instruction()

        self.writer.line('')
        self.writer.line('srli t6, t6, 0')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')

        self.writer.line('li a7, 93')
        self.writer.line('ecall')
        self.writer.f.close()


def main():
    i = 0
    while not common.done:
        i += 1
        print('generation', i)
        f = Fuzzer()
        f.loop()

        subprocess.call(f'{c_binary_as} {c_binary_as_args} -o main.o main.S', shell=True)
        subprocess.call(f'{c_binary_ld} -o main main.o', shell=True)

        int_output = subprocess.getoutput(f'{c_binary_riscv_int} main')
        int_match = re.match(r'int exit=Ok\((?P<code>-?\d+)\) cycles=\d+', int_output)
        int_exitcode = int(int_match.group('code'))

        cmp_exitcode = subprocess.call(f'{c_binary_riscv_spike} {c_binary_riscv_spike_args} main', shell=True)
        if cmp_exitcode >= 128:
            cmp_exitcode = cmp_exitcode - 256

        assert int_exitcode == cmp_exitcode

        asm_output = subprocess.getoutput(f'{c_binary_riscv_asm} main')
        asm_match = re.match(r'asm exit=Ok\((?P<code>-?\d+)\) cycles=\d+', asm_output)
        asm_exitcode = int(asm_match.group('code'))

        aot_output = subprocess.getoutput(f'{c_binary_riscv_aot} main')
        aot_match = re.match(r'aot exit=Ok\((?P<code>-?\d+)\) cycles=\d+', aot_output)
        aot_exitcode = int(aot_match.group('code'))

        assert int_exitcode == asm_exitcode
        assert int_exitcode == aot_exitcode


if __name__ == '__main__':
    main()
