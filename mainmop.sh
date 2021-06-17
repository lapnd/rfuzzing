set -x

/opt/riscv64b/bin/riscv64-unknown-elf-as -march=rv64gcb -o main.o main.S
/opt/riscv64b/bin/riscv64-unknown-elf-ld -o main main.o
rm main.o
/src/ckb-vm-run/target/release/int64 main
/src/ckb-vm-run/target/release/asm main
/src/ckb-vm-run/target/release/aot main
/src/ckb-vm-run/target/release/mop main
