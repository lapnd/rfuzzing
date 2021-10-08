set -ex

ROOT=$(pwd)
export RISCV=$ROOT/dep/riscv
export PATH=$PATH:$RISCV/bin

cd dep

if [ "$1" = "env" ]; then
    sudo apt install autoconf automake autotools-dev curl libmpc-dev libmpfr-dev libgmp-dev gawk build-essential bison flex texinfo gperf libtool patchutils bc zlib1g-dev libexpat-dev
    sudo apt install build-essential libgmp-dev z3 pkg-config zlib1g-dev
    sudo apt install device-tree-compiler

    sudo apt install opam
    opam init
    opam install sail
fi

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

if [ ! -d ./riscv-isa-sim ]; then
    git clone https://github.com/riscv-software-src/riscv-isa-sim
    cd riscv-isa-sim
    mkdir build
    cd build
    ../configure --prefix=$ROOT/dep/riscv
    make
    make install
    cd ../..
fi

if [ ! -d ./riscv-pk ]; then
    git clone https://github.com/riscv-software-src/riscv-pk
    cd riscv-pk
    mkdir build
    cd build
    ../configure --prefix=$ROOT/dep/riscv --host=riscv64-unknown-elf
    make
    make install
    cd ../..
fi