#!/usr/bin/env bash
# Clone the Pepper (Kokkos) codebase into $PEPPER_HOME (software/pepper).
# jobrunner runs this from the software/ directory with the environment sourced.
# The clone is gitignored; only this setup script is tracked. See software/README.md.
set -e

DEST="${PEPPER_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/software/pepper}"

if [ ! -d "$DEST" ]; then
  # Adjust the URL/branch to the Pepper source carrying the mcfm_analytics kernels.
  git clone https://gitlab.com/spice-mc/pepper.git --branch 43-add-kokkos-mcfm-interface "$DEST"
else
  echo "Pepper clone already present at $DEST"
fi
