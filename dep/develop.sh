set -ex

ROOT=$(pwd)

cd dep

if [ ! -d ./riscv-naive-assembler ]; then
    git clone https://github.com/XuJiandong/riscv-naive-assembler
    cd riscv-naive-assembler
    cargo build --release
    cd ..
fi

if [ ! -d ./ckb-vm-run ]; then
    git clone https://github.com/mohanson/ckb-vm-run
    cd ckb-vm-run
    cargo build --release
    cd ..
fi

if [ ! -d ./riscv ]; then
    git clone https://github.com/riscv-software-src/riscv-gnu-toolchain
    cd riscv-gnu-toolchain
    ./configure --prefix=$ROOT/dep/riscv
    make
    cd ..
fi

if [ ! -d ./sail-riscv ]; then
    git clone https://github.com/riscv/sail-riscv
    cd sail-riscv
    make
    cd ..
fi

if [ ! -d ./riscv-tests ]; then
    git clone https://github.com/nervosnetwork/riscv-tests
    cd riscv-tests
    git submodule update --init --recursive
    cd ..
fi
