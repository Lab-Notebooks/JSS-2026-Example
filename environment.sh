# Shell configuration shared across the lab notebook.
#
# Sourcing this file exports the project paths every orchestrator, skill, and
# tool depends on. It resolves the project root from THIS script's own location
# (via BASH_SOURCE), not the current working directory, so
#   source /abs/path/to/environment.sh
# is correct from any cwd — including inside a subagent whose cwd has drifted
# into a subdirectory. (The agent Bash tool persists cwd but resets env between
# calls, so a bare `source environment.sh` silently fails once cwd moves.)

export PROJECT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Per-machine site selector (config.sh sets SiteName; it is gitignored and
# generated from config.sh.example). Sourced only if the caller has not already.
if [ -z "$SiteName" ] && [ -f "$PROJECT_HOME/config.sh" ]; then
  source "$PROJECT_HOME/config.sh"
fi

# Per-machine toolchain/module loads live under the selected site.
SiteHome="$PROJECT_HOME/sites/$SiteName"
if [ -n "$SiteName" ] && [ -f "$SiteHome/config.sh" ]; then
  source "$SiteHome/config.sh"
fi

# The two scientific codebases under transformation. These are external clones
# obtained per software/README.md; the paths are fixed, the contents are not
# tracked by this repository.
export MCFM_HOME="$PROJECT_HOME/software/mcfm"       # Fortran -> C++ (stage 1)
export PEPPER_HOME="$PROJECT_HOME/software/pepper"   # C++ -> Kokkos (stage 2)

echo "---------------------------------------------------------------------------------------"
echo "Lab-notebook environment:"
echo "  PROJECT_HOME=$PROJECT_HOME"
echo "  SITE_HOME=$SiteHome"
echo "  MCFM_HOME=$MCFM_HOME"
echo "  PEPPER_HOME=$PEPPER_HOME"
echo "---------------------------------------------------------------------------------------"
