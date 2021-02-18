# RISC-V fuzzing test framework

Since there is no branch instruction in the B extension, this means that we don't need to think about infinite loops, or wrong jump addresses. This makes my job a lot easier.

```text
Fuzzer loop ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
    ↓                                             ↑
Starts by initializing registers: x0 to x31       ↑
    ↓                                             ↑
Write random instruction ←←←←←←←←←←←←←←←←←←←←↑    ↑
    ↓                                        ↑    ↑
Do checksum for RD: x31 = x31 + RD →→→→→←←←←→↑    ↑
    ↓                                             ↑
Treat x31 as 8 byte and sum them                  ↑
    ↓                                             ↑
Returns the result as exit code                   ↑
    ↓                                             ↑
Compile, and run it by ckb-vm and spike →→→→→→→→→→↑
```

# Special number

Some special numbers, such as 0x800000000000, they are on the boundary, so it is always easier to trigger bugs. I adjusted the frequency of their appearance, hope this helps!

# Speed

Due to the maximum memory limit of ckb-vm, I cannot write too many instructions at once. Currently, 32768 random instructions can be tested every 2 seconds. They will be executed by 4 virtual machines:

- ckb-vm-interpreter
- ckb-vm-asm
- ckb-vm-aot
- spike
