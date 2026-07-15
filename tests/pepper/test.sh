#!/usr/bin/env bash
# Build Pepper against the installed MCFM (the stage-2 build check).
# The stage-2 kernel verification itself is the doctest / libmcfm-equivalence loop
# (desired_spec.md §4-6, tools/kokkos/run_validation.sh); this builds the full app.
set -e

cd "$PEPPER_HOME/scripts"
rm -rf "$PEPPER_HOME/install"
export MCFM_DIR="$MCFM_HOME/install"
./build_pepper.sh "$PEPPER_HOME"
