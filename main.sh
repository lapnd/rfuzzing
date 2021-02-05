set -x

/root/app/riscv64b/bin/riscv64-unknown-elf-as -march=rv64gcb -o main.o main.S
/root/app/riscv64b/bin/riscv64-unknown-elf-ld -o main main.o
rm main.o
/src/ckb-vm-run/target/release/asm main
/root/app/riscv64b/bin/spike --isa RV64GCB pk /src/rfuzzing/main
echo $?
