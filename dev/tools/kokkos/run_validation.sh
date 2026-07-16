#!/usr/bin/env bash
# Validation harness — compile and run a standalone validator that links the
# original MCFM C++ (libmcfm) alongside the ported Kokkos kernels, compiled
# host-side through the Kokkos shim. This is the stage-2 equivalence step: it runs
# the real kernel headers on the CPU and compares them against MCFM, no Kokkos build.
#
# Usage: run_validation.sh <validator.cpp> [extra g++ args...]
# Overrides: MCFM_DIR, KERNELS_DIR, SHIM_DIR, CXX (g++-15/g++/c++), CXXFLAGS.
set -euo pipefail

validator="${1:?usage: run_validation.sh <validator.cpp> [extra g++ args...]}"
shift || true

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHIM_DIR="${SHIM_DIR:-$script_dir}"

# --- locate MCFM install (headers + libmcfm) ---
# Fall back through $MCFM_HOME, then the repo layout: prefer $PROJECT_HOME (set by
# environment.sh, as the Python tools do), else derive the repo root from this
# script's location (dev/tools/kokkos/ -> three levels up).
MCFM_DIR="${MCFM_DIR:-${MCFM_HOME:-}}"
if [[ -z "${MCFM_DIR}" ]]; then
  repo_root="${PROJECT_HOME:-$(cd "$script_dir/../../.." && pwd)}"
  MCFM_DIR="$(cd "$repo_root/software/mcfm" 2>/dev/null && pwd || true)"
fi
if   [[ -d "${MCFM_DIR}/install/include" ]]; then inc="$MCFM_DIR/install/include"; lib="$MCFM_DIR/install/lib"
elif [[ -d "${MCFM_DIR}/include"        ]]; then inc="$MCFM_DIR/include";        lib="$MCFM_DIR/lib"
else echo "error: set MCFM_DIR to the mcfminterface dir (with install/include and install/lib)" >&2; exit 1; fi

# --- locate Pepper kernels ---
KERNELS_DIR="${KERNELS_DIR:-${PEPPER_HOME:+$PEPPER_HOME/src/mcfm_analytics}}"
if [[ -z "${KERNELS_DIR}" || ! -d "${KERNELS_DIR}" ]]; then
  echo "error: set KERNELS_DIR to .../src/mcfm_analytics (or export PEPPER_HOME)" >&2; exit 1; fi

# --- compiler ---
if [[ -z "${CXX:-}" ]]; then
  for c in g++-15 g++ c++; do command -v "$c" >/dev/null 2>&1 && { CXX="$c"; break; }; done
fi
: "${CXX:?no C++ compiler found; set CXX}"
CXXFLAGS="${CXXFLAGS:--O3 -march=native}"

# --- build a shim include tree so the kernels' relative includes resolve ---
# The kernel headers do #include "../math.h" etc.; placing copies of them under
# <build>/mcfm_analytics/ makes "../" resolve to the shim headers in <build>/.
build="$(mktemp -d)"
trap 'rm -rf "$build"' EXIT
mkdir -p "$build/mcfm_analytics"
# -R: split kernels keep their fragments in <name>_parts/ subdirs; copy those too
cp -R "$KERNELS_DIR"/. "$build/mcfm_analytics/"
cp "$SHIM_DIR/kokkos_host_shim/math.h"          "$build/math.h"
cp "$SHIM_DIR/kokkos_host_shim/event_handle.h"  "$build/event_handle.h"
cp "$SHIM_DIR/kokkos_host_shim/kernel_macros.h" "$build/kernel_macros.h"

bin="$build/validator"
echo "compiler : $CXX $CXXFLAGS"
echo "MCFM     : $inc"
echo "kernels  : $KERNELS_DIR"
"$CXX" -std=c++17 $CXXFLAGS -I "$inc" -I "$build" "$validator" \
  -L "$lib" -lmcfm -Wl,-rpath,"$lib" "$@" -o "$bin"
"$bin"
