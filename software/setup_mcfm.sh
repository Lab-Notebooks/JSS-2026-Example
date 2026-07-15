#!/usr/bin/env bash
# Clone the MCFM Fortran/C++ codebase into $MCFM_HOME (software/mcfm).
# jobrunner runs this from the software/ directory with the environment sourced.
# The clone is gitignored; only this setup script is tracked. See software/README.md.
set -e

DEST="${MCFM_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/software/mcfm}"

if [ ! -d "$DEST" ]; then
  # Adjust the URL/branch to the MCFM (mcfminterface) source you are translating.
  git clone git@github.com:NeuCol/mcfminterface.git --branch adhruv/Convert_to_c++ "$DEST"
else
  echo "MCFM clone already present at $DEST"
fi
