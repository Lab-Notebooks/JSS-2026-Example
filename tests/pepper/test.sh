#!/usr/bin/env bash
# Build Pepper (the local $PEPPER_HOME checkout) against the installed MCFM and the
# Kokkos QCDLoop clone, then run the unit-test / doctest suite (the stage-2 build +
# verification harness; desired_spec.md §4-6, tools/kokkos/run_validation.sh).
#
# Requires environment.sh to have exported MCFM_HOME, PEPPER_HOME and QCDLOOP_HOME,
# and tests/mcfm to have installed MCFM under $MCFM_HOME/install (libmcfm) first.
#
# -DPEPPER_QCDLOOP_DIR adds $QCDLOOP_HOME/src (+ /src/qcdloop) to the include path and
# defines PEPPER_QCDLOOP, enabling the massive-top (texact) scalar-integral kernels in
# src/mcfm_analytics and their doctests in tests/unit_tests/matrix_elements.cpp.
set -e

# Kokkos: prefer an externally-provided install (Kokkos_ROOT / CMAKE_PREFIX_PATH, e.g.
# from a site module). Otherwise build and cache a pinned Kokkos that matches Pepper's
# own build_pepper.sh (4.5.00): Pepper's EnableKokkos.cmake FetchContent pulls Kokkos
# 5.0.0, which needs GCC >= 10.4 / Clang >= 14 — newer than some site toolchains — so we
# provide a compatible Kokkos and let find_package(Kokkos CONFIG) pick it up instead.
KOKKOS_TAG=4.5.00
KOKKOS_CACHE="$PEPPER_HOME/external/kokkos-$KOKKOS_TAG"
if [ -z "$Kokkos_ROOT" ] && [ -z "$KOKKOS_ROOT" ]; then
  if ! ls "$KOKKOS_CACHE"/install/lib*/cmake/Kokkos/KokkosConfig.cmake >/dev/null 2>&1; then
    echo "Kokkos not provided externally; building pinned Kokkos $KOKKOS_TAG into $KOKKOS_CACHE"
    rm -rf "$KOKKOS_CACHE"
    git clone --depth 1 -b "$KOKKOS_TAG" https://github.com/kokkos/kokkos.git "$KOKKOS_CACHE/src"
    cmake -S "$KOKKOS_CACHE/src" -B "$KOKKOS_CACHE/build" \
          -DCMAKE_BUILD_TYPE=Release \
          -DCMAKE_INSTALL_PREFIX="$KOKKOS_CACHE/install" \
          -DKokkos_ENABLE_THREADS=ON \
          -DKokkos_ARCH_NATIVE=ON \
          -DCMAKE_CXX_STANDARD=17 \
          -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
          -DBUILD_SHARED_LIBS=ON
    cmake --build "$KOKKOS_CACHE/build" -j --target install
  fi
  export Kokkos_ROOT="$KOKKOS_CACHE/install"
fi

BUILD_DIR="$PEPPER_HOME/build"
rm -rf "$BUILD_DIR"

cmake -S "$PEPPER_HOME" -B "$BUILD_DIR" \
      -DCMAKE_BUILD_TYPE=Release \
      -DPEPPER_QCDLOOP_DIR="$QCDLOOP_HOME"

cmake --build "$BUILD_DIR" --target pepper_test -j

"$BUILD_DIR/tests/unit_tests/pepper_test"
