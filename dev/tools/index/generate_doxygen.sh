#!/usr/bin/env bash
# Generate the Doxygen call-graph XML the Index tool consumes.
#
# The stage-1 workflow is Doxygen-based: build_roadmap.py ranks translation leaves
# from Doxygen's cross-reference edges, so that XML must exist before the Index
# phase runs. This script produces it from the committed Doxyfile, feeding INPUT and
# OUTPUT_DIRECTORY from $MCFM_HOME so the same config works on any checkout.
#
# Output:  $MCFM_HOME/doxygen_dep/xml   (read by dev/tools/index/build_roadmap.py)
# Requires: doxygen on PATH; $MCFM_HOME set (source environment.sh first).
#
# Usage: source environment.sh && dev/tools/index/generate_doxygen.sh
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${MCFM_HOME:?set MCFM_HOME first (source environment.sh)}"

command -v doxygen >/dev/null || {
  echo "error: doxygen not found on PATH. Install it, then re-run." >&2
  echo "  Ubuntu: sudo apt-get install -y doxygen   (graphviz/dot optional)" >&2
  exit 1
}

out="$MCFM_HOME/doxygen_dep"
mkdir -p "$out"
echo "Generating Doxygen XML for $MCFM_HOME/src -> $out/xml"

# Append the per-checkout paths to the committed Doxyfile and run from stdin, so the
# committed file stays machine-independent.
{ cat "$here/Doxyfile"
  echo "INPUT = $MCFM_HOME/src"
  echo "OUTPUT_DIRECTORY = $out"
} | doxygen - >/dev/null

n=$(find "$out/xml" -name '*.xml' ! -name index.xml | wc -l)
echo "wrote $n XML file(s) to $out/xml"
[ "$n" -gt 0 ] || { echo "error: no XML produced — check doxygen output" >&2; exit 1; }
