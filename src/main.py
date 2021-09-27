import os
import random
import re
import signal
import subprocess
import sys

import common
import convention

c_binary_gcc = 'dep/riscv/bin/riscv64-unknown-elf-gcc'
c_binary_as = 'dep/riscv/bin/riscv64-unknown-elf-as'
c_binary_as_args = ''
c_binary_ld = 'dep/riscv/bin/riscv64-unknown-elf-ld'
# https://github.com/mohanson/ckb-vm-run
c_binary_riscv_int = 'dep/ckb-vm-run/target/release/int64'
c_binary_riscv_asm = 'dep/ckb-vm-run/target/release/asm'
c_binary_riscv_aot = 'dep/ckb-vm-run/target/release/aot'
c_binary_riscv_mop = 'dep/ckb-vm-run/target/release/mop'
c_binary_riscv_spike = '/opt/riscv/bin/spike'
c_binary_riscv_spike_args = '--isa RV64GC_ZBA_ZBB_ZBC_ZBS /opt/riscv/riscv64-unknown-elf/bin/pk'
# https://github.com/XuJiandong/riscv-naive-assembler
c_binary_riscv_naive_assembler = 'dep/riscv-naive-assembler/target/release/riscv-naive-assembler'
# https://github.com/riscv/sail-riscv
c_binary_sail = 'dep/sail-riscv/c_emulator/riscv_sim_RV64'
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
        choose_rule = random.choice(convention.instruction_rule_imc)
        rule = choose_rule[1]
        rd = self.rand_idle_register()
        rs = [self.rand_idle_register() for _ in range(4)]

        for line in rule:
            args = []
            for i in line[1:]:
                if line[0] == '.byte':
                    e = i
                    while 'b' in e:
                        if self.rand_u64() % 2 == 0:
                            e = e.replace('b', '0', 1)
                        else:
                            e = e.replace('b', '1', 1)
                    args.append(hex(int('0b' + e, 2)))
                    continue
                if i == 'r?':
                    args.append(self.rand_idle_register())
                    continue
                if i == 'rd':
                    if line[0] in ['sb', 'sh', 'sw', 'sd']:
                        while rd == 'a0':
                            rd = self.rand_idle_register()
                    args.append(rd)
                    continue
                if i == 'r0':
                    args.append(rs[0])
                    continue
                if i == 'r1':
                    args.append(rs[1])
                    continue
                if i == 'r2':
                    args.append(rs[2])
                    continue
                if i == 'r3':
                    args.append(rs[3])
                    continue
                if i == 'i12':
                    args.append(str((self.rand_u64() & 0xfff) - 0x800))
                    continue
                if i == 'u5':
                    args.append(str(self.rand_u64() & 0x1f))
                    continue
                if i == 'u6':
                    args.append(str(self.rand_u64() & 0x3f))
                    continue
                if i == 'u20':
                    args.append(str(self.rand_u64() & 0xfffff))
                    continue
                if i == 'u64':
                    args.append(str(self.rand_u64()))
                    continue
                args.append(i)
            self.writer.line(f'{line[0]} {", ".join(args)}')
        self.writer.line(f'add t6, t6, {rd}')

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
                args.append(str(self.rand_u64() % 64))
                continue
            assert 0
        self.writer.line(f'{opcode} {", ".join(args)}')
        self.writer.line(f'add t6, t6, {args[0]}')

    def rand_instruction_mop(self):
        opcode = random.choice(list(convention.instruction_rule_mop))
        rule = convention.instruction_rule_mop[opcode]
        reg0 = self.rand_idle_register()
        reg1 = self.rand_idle_register()
        reg2 = self.rand_idle_register()
        reg3 = self.rand_idle_register()
        for i in rule:
            self.writer.line(i.replace('r0', reg0).replace('r1', reg1).replace('r2', reg2).replace('r3', reg3))
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

    def sail(self):
        self.writer.line('#include "riscv_test.h"')
        self.writer.line('#include "test_macros.h"')
        self.writer.line('RVTEST_RV64U')
        self.writer.line('RVTEST_CODE_BEGIN')

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

        # dep/riscv-tests/env/p/riscv_test.h::TESTNUM
        self.writer.line('beq t6, zero, ohno')
        self.writer.line('add TESTNUM, zero, t6')
        self.writer.line('RVTEST_FAIL')
        self.writer.line('ohno:')
        self.writer.line('li TESTNUM, 1')
        self.writer.line('RVTEST_FAIL')

        self.writer.line('RVTEST_CODE_END')
        self.writer.line('.data')
        self.writer.line('RVTEST_DATA_BEGIN')
        self.writer.line('TEST_DATA')
        self.writer.line('number:')
        self.writer.line('.quad 4')
        self.writer.line('.quad 2')
        self.writer.line('.quad 1')
        self.writer.line('.quad 0')
        self.writer.line('RVTEST_DATA_END')
        self.writer.f.close()


def call_lazy(cmd: str):
    return subprocess.run(cmd, shell=True, preexec_fn=lambda: signal.signal(0x02, signal.SIG_IGN), capture_output=True)


def call(cmd: str):
    c = call_lazy(cmd)
    if c.returncode != 0:
        print(c)
        assert 0
    return c


def main_imc():
    for i in range(1 << 32):
        if common.done:
            break
        print('generation', i)
        f = Fuzzer()
        f.sail()

        call(f'{c_binary_gcc} -march=rv64g -mabi=lp64 -static -mcmodel=medany -fvisibility=hidden -nostdlib \
               -nostartfiles -Idep/riscv-tests/env/p -Idep/riscv-tests/isa/macros/scalar \
               -Tdep/riscv-tests/env/p/link.ld -o /tmp/main /tmp/main.S')
        r = call(f'{c_binary_sail} /tmp/main')
        r = r.stdout.splitlines()
        if r[-1].decode().startswith('SUCCESS'):
            # SUCCESS means lower 32 bits is zero
            cmp_exitcode = 0
        if r[-1].decode().startswith('FAILURE'):
            cmp_output = r[-1].decode()
            cmp_match = re.match(r'FAILURE: (?P<a1>\d+)', cmp_output)
            cmp_exitcode = int(cmp_match.group('a1')) % 256
        else:
            cmp_output = r[-4].decode()
            cmp_match = re.match(r'FAILURE: (?P<a1>\d+)', cmp_output)
            cmp_exitcode = int(cmp_match.group('a1')) % 256

        r = call(f'{c_binary_gcc} -march=rv64g -mabi=lp64 -static -mcmodel=medany -fvisibility=hidden -nostdlib \
               -nostartfiles -DENTROPY=0x43877ce -std=gnu99 -O2 -Idep/riscv-tests/env/u \
               -Idep/riscv-tests/isa/macros/scalar -Tdep/riscv-tests/env/u/link.ld -o /tmp/main \
               dep/riscv-tests/env/u/entry.S dep/riscv-tests/env/u/*.c /tmp/main.S')
        int_output = call(f'{c_binary_riscv_int} {c_tempdir}/main').stdout.decode()
        int_match = re.match(r'int exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+) r\[a1\]=(?P<a1>\d+).*', int_output)
        int_exitcode = int(int_match.group('a1')) % 256

        asm_output = call(f'{c_binary_riscv_asm} {c_tempdir}/main').stdout.decode()
        asm_match = re.match(r'asm exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+) r\[a1\]=(?P<a1>\d+).*', asm_output)
        asm_exitcode = int(asm_match.group('a1')) % 256

        aot_output = call(f'{c_binary_riscv_aot} {c_tempdir}/main').stdout.decode()
        aot_match = re.match(r'aot exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+) r\[a1\]=(?P<a1>\d+).*', aot_output)
        aot_exitcode = int(aot_match.group('a1')) % 256

        mop_output = call(f'{c_binary_riscv_mop} {c_tempdir}/main').stdout.decode()
        mop_match = re.match(r'mop exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+) r\[a1\]=(?P<a1>\d+).*', mop_output)
        mop_exitcode = int(mop_match.group('a1')) % 256

        assert cmp_exitcode == int_exitcode
        assert cmp_exitcode == asm_exitcode
        assert cmp_exitcode == aot_exitcode
        assert cmp_exitcode == mop_exitcode


def main_b():
    for i in range(1 << 32):
        if common.done:
            break
        print('generation', i)
        f = Fuzzer()
        f.loop()

        call(f'mv {c_tempdir}/main.S {c_tempdir}/main_origin.S')

        output = call(f'{c_binary_riscv_naive_assembler} -i {c_tempdir}/main_origin.S').stdout.decode()
        with open(f'{c_tempdir}/main.S', 'w') as f:
            f.write(output)
        call(f'{c_binary_as} {c_binary_as_args} -o {c_tempdir}/main.o {c_tempdir}/main.S')
        call(f'{c_binary_ld} -o {c_tempdir}/main -T src/main.lds {c_tempdir}/main.o')

        cmp_exitcode = call_lazy(f'{c_binary_riscv_spike} {c_binary_riscv_spike_args} {c_tempdir}/main').returncode
        if cmp_exitcode >= 128:
            cmp_exitcode = cmp_exitcode - 256

        int_output = call(f'{c_binary_riscv_int} {c_tempdir}/main').stdout.decode()
        int_match = re.match(r'int exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+).*', int_output)
        int_exitcode = int(int_match.group('code'))

        asm_output = call(f'{c_binary_riscv_asm} {c_tempdir}/main').stdout.decode()
        asm_match = re.match(r'asm exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+).*', asm_output)
        asm_exitcode = int(asm_match.group('code'))

        aot_output = call(f'{c_binary_riscv_aot} {c_tempdir}/main').stdout.decode()
        aot_match = re.match(r'aot exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+).*', aot_output)
        aot_exitcode = int(aot_match.group('code'))

        mop_output = call(f'{c_binary_riscv_mop} {c_tempdir}/main').stdout.decode()
        mop_match = re.match(r'mop exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+).*', mop_output)
        mop_exitcode = int(mop_match.group('code'))

        assert cmp_exitcode == int_exitcode
        assert cmp_exitcode == asm_exitcode
        assert cmp_exitcode == aot_exitcode
        assert cmp_exitcode == mop_exitcode


def main_mop():
    for i in range(1 << 32):
        if common.done:
            break
        print('generation', i)
        f = Fuzzer()
        f.loop()

        call(f'{c_binary_as} {c_binary_as_args} -o {c_tempdir}/main.o {c_tempdir}/main.S')
        call(f'{c_binary_ld} -o {c_tempdir}/main -T src/main.lds {c_tempdir}/main.o')

        cmp_exitcode = call_lazy(f'{c_binary_riscv_spike} {c_binary_riscv_spike_args} {c_tempdir}/main').returncode
        if cmp_exitcode >= 128:
            cmp_exitcode = cmp_exitcode - 256

        int_output = call(f'{c_binary_riscv_int} {c_tempdir}/main').stdout.decode()
        int_match = re.match(r'int exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+).*', int_output)
        int_exitcode = int(int_match.group('code'))

        asm_output = call(f'{c_binary_riscv_asm} {c_tempdir}/main').stdout.decode()
        asm_match = re.match(r'asm exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+).*', asm_output)
        asm_exitcode = int(asm_match.group('code'))

        aot_output = call(f'{c_binary_riscv_aot} {c_tempdir}/main').stdout.decode()
        aot_match = re.match(r'aot exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+).*', aot_output)
        aot_exitcode = int(aot_match.group('code'))

        mop_output = call(f'{c_binary_riscv_mop} {c_tempdir}/main').stdout.decode()
        mop_match = re.match(r'mop exit=Ok\((?P<code>-?\d+)\) cycles=(?P<cycles>\d+).*', mop_output)
        mop_exitcode = int(mop_match.group('code'))

        assert cmp_exitcode == int_exitcode
        assert cmp_exitcode == asm_exitcode
        assert cmp_exitcode == aot_exitcode
        assert cmp_exitcode == mop_exitcode


if __name__ == '__main__':
    if sys.argv[1] == 'imc':
        convention.p_instruction_imc = 1
        convention.p_instruction_b = 1
        convention.p_instruction_mop = 1
        main_imc()
    if sys.argv[1] == 'b':
        convention.p_instruction_imc = 0
        convention.p_instruction_b = 1
        convention.p_instruction_mop = 1
        main_b()
    if sys.argv[1] == 'mop':
        convention.p_instruction_imc = 0
        convention.p_instruction_b = 0
        convention.p_instruction_mop = 1
        main_mop()
