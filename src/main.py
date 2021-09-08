import os
import random
import re
import signal
import subprocess
import sys

import common
import convention

c_binary_as = '/root/app/riscv/bin/riscv64-unknown-elf-as'
c_binary_as_args = ''
c_binary_ld = '/root/app/riscv/bin/riscv64-unknown-elf-ld'
# https://github.com/mohanson/ckb-vm-run
c_binary_riscv_int = '/src/ckb-vm-run/target/release/int64'
c_binary_riscv_asm = '/src/ckb-vm-run/target/release/asm'
c_binary_riscv_aot = '/src/ckb-vm-run/target/release/aot'
c_binary_riscv_mop = '/src/ckb-vm-run/target/release/mop'
c_binary_riscv_spike = '/opt/riscv64b/bin/spike'
c_binary_riscv_spike_args = '--isa RV64GCB /opt/riscv64b/riscv64-unknown-elf/bin/pk'
# https://github.com/XuJiandong/riscv-naive-assembler
c_binary_riscv_naive_assembler = '/src/riscv-naive-assembler/target/release/riscv-naive-assembler'
c_tempdir = '/tmp'


class Fuzzer:

    def __init__(self):
        self.writer = common.Writer(f'{c_tempdir}/main.S')

    def rand_u64(self):
        # There is a higher chance of generating best numbers
        if random.random() < convention.p_best_numbers:
            return random.choice(convention.best_numbers)
        else:
            return random.randint(0, (1 << 64) - 1)

    def rand_idle_register(self):
        return random.choice(convention.idle_registers)

    def rand_instruction_imc(self):
        pass

    def rand_instruction_b(self):
        choose_rule = random.choice(convention.instruction_rule_b)
        opcode = choose_rule[0]
        args = []
        for i in choose_rule[1]:
            if i == 'r':
                args.append(self.rand_idle_register())
                continue
            if i == 'u5':
                args.append(str(self.rand_u64() % 32))
                continue
            if i == 'u6':
                args.append(str(self.rand_u64() % 32))
                continue
            assert 0
        self.writer.line(f'{opcode} {", ".join(args)}')
        self.writer.line(f'add t6, t6, {args[0]}')

    def rand_instruction_mop(self):
        opcode, rule = random.choice(list(convention.instruction_rule_mop))
        rule = convention.instruction_rule_mop[opcode]
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

    def rand_instruction(self):
        p = random.random()
        if p < convention.p_instruction_imc:
            return self.rand_instruction_imc()
        if p < convention.p_instruction_b:
            return self.rand_instruction_b()
        if p < convention.p_instruction_mop:
            return self.rand_instruction_mop()
        assert 0

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
    c = subprocess.run(cmd, shell=True, preexec_fn=lambda: signal.signal(0x02, signal.SIG_IGN), capture_output=True)
    if c.returncode != 0:
        print(c)
        assert 0
    return c


def main():
    for i in range(1 << 32):
        if common.done:
            break
        print('generation', i)
        f = Fuzzer()
        f.loop()

        call(f'{c_binary_as} {c_binary_as_args} -o {c_tempdir}/main.o {c_tempdir}/main.S')
        call(f'{c_binary_ld} -o {c_tempdir}/main -T main.lds {c_tempdir}/main.o')

        int_output = call(f'{c_binary_riscv_int} {c_tempdir}/main').stdout.decode()
        int_match = re.match(r'int exit=Ok\((?P<code>-?\d+)\) cycles=\d+', int_output)
        int_exitcode = int(int_match.group('code'))

        cmp_exitcode = call(f'{c_binary_riscv_spike} {c_binary_riscv_spike_args} {c_tempdir}/main').returncode
        if cmp_exitcode >= 128:
            cmp_exitcode = cmp_exitcode - 256

        assert int_exitcode == cmp_exitcode

        asm_output = call(f'{c_binary_riscv_asm} {c_tempdir}/main').stdout.decode()
        asm_match = re.match(r'asm exit=Ok\((?P<code>-?\d+)\) cycles=\d+', asm_output)
        asm_exitcode = int(asm_match.group('code'))

        aot_output = call(f'{c_binary_riscv_aot} {c_tempdir}/main').stdout.decode()
        aot_match = re.match(r'aot exit=Ok\((?P<code>-?\d+)\) cycles=\d+', aot_output)
        aot_exitcode = int(aot_match.group('code'))

        mop_output = call(f'{c_binary_riscv_mop} {c_tempdir}/main').stdout.decode()
        mop_match = re.match(r'mop exit=Ok\((?P<code>-?\d+)\) cycles=\d+', mop_output)
        mop_exitcode = int(mop_match.group('code'))

        assert int_exitcode == asm_exitcode
        assert int_exitcode == aot_exitcode
        assert int_exitcode == mop_exitcode


def main_b_decode():
    for i in range(1 << 32):
        if common.done:
            break
        print('generation', i)
        f = Fuzzer()
        f.loop()

        output = call(f'{c_binary_riscv_naive_assembler} -i {c_tempdir}/main.S').stdout.decode()
        with open(f'{c_tempdir}/main_naive.S', 'w') as f:
            f.write(output)
        call(f'{c_binary_as} {c_binary_as_args} -o {c_tempdir}/main_naive.o {c_tempdir}/main_naive.S')
        call(f'{c_binary_ld} -o {c_tempdir}/main_naive -T main.lds {c_tempdir}/main_naive.o')

        a = output
        a = [i[2:] for i in a.split('\n') if i.startswith('#')]

        b = call(f'{c_binary_riscv_int} {c_tempdir}/main_naive').stdout.decode()
        b = b.split('\n')

        for i in range(len(a)):
            if a[i] != b[i]:
                print(a[i], b[i])
                assert False


def main_b():
    for i in range(1 << 32):
        if common.done:
            break
        print('generation', i)
        f = Fuzzer()
        f.loop()

        output = call(f'{c_binary_riscv_naive_assembler} -i {c_tempdir}/main.S').stdout.decode()
        with open(f'{c_tempdir}/main_naive.S', 'w') as f:
            f.write(output)
        call(f'{c_binary_as} {c_binary_as_args} -o {c_tempdir}/main_naive.o {c_tempdir}/main_naive.S')
        call(f'{c_binary_ld} -o {c_tempdir}/main_naive -T src/main.lds {c_tempdir}/main_naive.o')

        int_output = call(f'{c_binary_riscv_int} {c_tempdir}/main_naive').stdout.decode()
        int_match = re.match(r'int exit=Ok\((?P<code>-?\d+)\) cycles=\d+', int_output)
        int_exitcode = int(int_match.group('code'))

        asm_output = call(f'{c_binary_riscv_asm} {c_tempdir}/main_naive').stdout.decode()
        asm_match = re.match(r'asm exit=Ok\((?P<code>-?\d+)\) cycles=\d+', asm_output)
        asm_exitcode = int(asm_match.group('code'))

        aot_output = call(f'{c_binary_riscv_aot} {c_tempdir}/main_naive').stdout.decode()
        aot_match = re.match(r'aot exit=Ok\((?P<code>-?\d+)\) cycles=\d+', aot_output)
        aot_exitcode = int(aot_match.group('code'))

        mop_output = call(f'{c_binary_riscv_mop} {c_tempdir}/main_naive').stdout.decode()
        mop_match = re.match(r'mop exit=Ok\((?P<code>-?\d+)\) cycles=\d+', mop_output)
        mop_exitcode = int(mop_match.group('code'))

        assert int_exitcode == asm_exitcode
        assert int_exitcode == aot_exitcode
        assert int_exitcode == mop_exitcode


if __name__ == '__main__':
    if sys.argv[1] == 'imc':
        pass
    if sys.argv[1] == 'b':
        convention.p_instruction_imc = 0
        convention.p_instruction_b = 1
        convention.p_instruction_mop = 1
        main_b()
    if sys.argv[1] == 'mop':
        pass
