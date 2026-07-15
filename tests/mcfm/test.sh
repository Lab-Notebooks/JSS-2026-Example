#!/usr/bin/env bash
# Build MCFM and run the benchmark suite (the stage-1 verification harness).
# Requires $MCFM_HOME (set by environment.sh) and a GNU toolchain (see sites/).
set -e

cd "$MCFM_HOME/Bin"
rm -rf "$MCFM_HOME/install"

make clean || true
cmake -DCMAKE_Fortran_COMPILER=gfortran -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ \
      -DCMAKE_INSTALL_PREFIX="$MCFM_HOME/install" ..
make install

# Benchmark processes, mapped to src/ directories (desired_spec.md §5).
./test -b u d~ ve e+        # W
./test -b u d~ ve e+ g      # W1jet
./test -b u d~ ve e+ g g    # W2jet, BDK, loop
./test -b u u~ e- e+        # Z
./test -b u u~ e- e+ g      # Z1jet, loop
./test -b u u~ e- e+ g g    # Z2jet, W2jet, BDK, loop
./test -b -Pmodel=heft g g h   # ggH
./test -b g g h             # ggH
./test -b g g g g g         # ThreeJets
./test -b g g h g g         # gghgg_dep
