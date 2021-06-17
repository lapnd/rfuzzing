import os
import random
import re
import signal
import subprocess

import common
import convention

xlen = 64

assert xlen in [32, 64]

if xlen == 32:
    c_binary_as = '/opt/riscv32b/bin/riscv32-unknown-elf-as'
    c_binary_as_args = '-march=rv32gcb'
    c_binary_ld = '/opt/riscv32b/bin/riscv32-unknown-elf-ld'
    # https://github.com/mohanson/ckb-vm-run
    c_binary_riscv_int = '/src/ckb-vm-run/target/release/int32'
    c_binary_riscv_asm = ''
    c_binary_riscv_aot = ''
    c_binary_riscv_mop = ''
    c_binary_riscv_spike = '/opt/riscv32b/bin/spike'
    c_binary_riscv_spike_args = '--isa RV32GCB /opt/riscv32b/riscv32-unknown-elf/bin/pk'
else:
    c_binary_as = '/opt/riscv64b/bin/riscv64-unknown-elf-as'
    c_binary_as_args = '-march=rv64gcb'
    c_binary_ld = '/opt/riscv64b/bin/riscv64-unknown-elf-ld'
    c_binary_riscv_int = '/src/ckb-vm-run/target/release/int64'
    c_binary_riscv_asm = '/src/ckb-vm-run/target/release/asm'
    c_binary_riscv_aot = '/src/ckb-vm-run/target/release/aot'
    c_binary_riscv_mop = '/src/ckb-vm-run/target/release/mop'
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
        if xlen == 64:
            iset = convention.instruction_rule_64
        else:
            iset = convention.instruction_rule_32
        choose_rule = random.choice(iset)
        opcode = choose_rule[0]
        args = []
        for i in choose_rule[1]:
            if i == 'r':
                args.append(self.rand_idle_register())
                continue
            if i == 'half':
                args.append(hex(self.rand_u64() % (xlen >> 1)))
                continue
            if i == 'xlen':
                args.append(hex(self.rand_u64() % xlen))
                continue
            if i == 'i12':
                n = self.rand_u64() % (1 << 12)
                n -= (1 << 11)
                args.append(str(n))
                continue
            assert 0
        self.writer.line(f'{opcode} {", ".join(args)}')
        self.writer.line(f'add t6, t6, {args[0]}')

    def rand_instruction_mop(self):
        assert xlen == 64
        opcode, rule = random.choice(list(convention.instruction_rule_mop_cpx.items()))
        rule = convention.instruction_rule_mop_cpx[opcode]
        reg0 = self.rand_idle_register()
        reg1 = self.rand_idle_register()
        reg2 = self.rand_idle_register()
        reg3 = self.rand_idle_register()
        for i in rule:
            self.writer.line(i.replace('a0', reg0).replace('a1', reg1).replace('a2', reg2).replace('a3', reg3))
        self.writer.line(f'add t6, t6, {reg0}')
        self.writer.line(f'add t6, t6, {reg1}')
        self.writer.line(f'add t6, t6, {reg2}')
        self.writer.line(f'add t6, t6, {reg3}')

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
                if random.random() < convention.p_mop:
                    self.rand_instruction_mop()
                else:
                    self.rand_instruction()

        # Returns checksum
        self.writer.line('')
        self.writer.line('srli t6, t6, 0')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        self.writer.line('srli t6, t6, 8')
        self.writer.line('add a0, a0, t6')
        if xlen == 64:
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
        self.writer.line('.section .data')
        self.writer.line('number:')
        self.writer.line('.quad 4')
        self.writer.line('.quad 2')
        self.writer.line('.quad 1')
        self.writer.line('.quad 0')
        self.writer.f.close()


def call(cmd: str):
    return subprocess.run(cmd, shell=True, preexec_fn=lambda: signal.signal(0x02, signal.SIG_IGN), capture_output=True)


def main():
    for i in range(1 << 32):
        if common.done:
            break
        print('generation', i)
        f = Fuzzer()
        f.loop()

        call(f'{c_binary_as} {c_binary_as_args} -o main.o main.S')
        call(f'{c_binary_ld} -o main -T main.lds main.o')

        int_output = call(f'{c_binary_riscv_int} main').stdout.decode()
        int_match = re.match(r'int exit=Ok\((?P<code>-?\d+)\) cycles=\d+', int_output)
        int_exitcode = int(int_match.group('code'))

        cmp_exitcode = call(f'{c_binary_riscv_spike} {c_binary_riscv_spike_args} main').returncode
        if cmp_exitcode >= 128:
            cmp_exitcode = cmp_exitcode - 256

        assert int_exitcode == cmp_exitcode

        if xlen == 64:
            asm_output = call(f'{c_binary_riscv_asm} main').stdout.decode()
            asm_match = re.match(r'asm exit=Ok\((?P<code>-?\d+)\) cycles=\d+', asm_output)
            asm_exitcode = int(asm_match.group('code'))

            aot_output = call(f'{c_binary_riscv_aot} main').stdout.decode()
            aot_match = re.match(r'aot exit=Ok\((?P<code>-?\d+)\) cycles=\d+', aot_output)
            aot_exitcode = int(aot_match.group('code'))

            mop_output = call(f'{c_binary_riscv_mop} main').stdout.decode()
            mop_match = re.match(r'mop exit=Ok\((?P<code>-?\d+)\) cycles=\d+', mop_output)
            mop_exitcode = int(mop_match.group('code'))

            assert int_exitcode == asm_exitcode
            assert int_exitcode == aot_exitcode
            assert int_exitcode == mop_exitcode


if __name__ == '__main__':
    main()
