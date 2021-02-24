set -x

/opt/riscv32b/bin/riscv32-unknown-elf-as -march=rv32gcb -o main.o main.S
/opt/riscv32b/bin/riscv32-unknown-elf-ld -o main main.o
rm main.o
/src/ckb-vm-run/target/release/int32 main
/opt/riscv32b/bin/spike --isa RV32GCB /opt/riscv32b/riscv32-unknown-elf/bin/pk main
echo $?
