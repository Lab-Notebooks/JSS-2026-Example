# Tools — the deterministic capabilities agents invoke

A **tool** is a reusable, deterministic coded capability the orchestrator runs
*instead of* a model call — computing a dependency layer, drafting a scaffold,
deriving a call-tree closure, checking a port. Keeping the mechanical steps in tools
does two useful things: it reserves model effort for the parts that actually need
judgment (authoring and verification), and, because a tool is defined independently of
any one agent, it lets the *same* tool run under either orchestrator so their
performance can be compared on equal footing.

Each tool lives in its own directory and does one thing. Read the docstring at the
top of each file for the exact interface; this page is the map of *why* each exists.

### `index/build_roadmap.py` — the Index tool
Fuses Doxygen's call graph with a translated/not-translated check to rank MCFM's
Fortran files by readiness. Its job is to answer the one question the Resolve phase
asks: which files are *leaves* — every routine they call is already C++, so they can
be translated now? It writes a metrics table (`deps`, `blind`, `fanin`, `bench`) and
the symbol → file map the Draft tool needs. Deterministic dependency ranking is
exactly the kind of work that should never cost a model call.

### `draft/scribe_draft.py` (+ `seed_examples.toml`) — the Draft tool
Produces a rough, mechanical first cut of one Fortran file — and, more usefully, a
block of hints flagging which called names are external functions defined elsewhere,
so the model does not fabricate them (Spec §2 rule 9a). The draft is scaffolding, not
an answer; the Author subagent reads it beside the worked examples in
`seed_examples.toml` and writes the real translation. Together they replicate the
reference *draft → translate* mechanism as a self-contained, orchestrator-independent
step.

### `closure/calltree_closure.py` — the Closure tool
The completeness check for the stage-2 Split phase. An agent maps a call tree by
reading source; this tool derives it from the *build itself* — every linked object's
undefined symbols are its real callees. Symbols do not lie, so a file in the closure
that is missing from a split plan is a genuine gap, not a matter of opinion. It also
flags any plain-Fortran object still in the tree as a stage-1 gap that must be closed
before a Kokkos port can proceed.

### `kokkos/` — the stage-2 porting and validation aids
- **`kokkosify.py`** applies the safe, mechanical subset of the stage-2 rules
  (complex-type and math-namespace renames, `KOKKOS_INLINE_FUNCTION` annotation) and
  *flags* everything it cannot decide — QCDLoop calls, module globals, `FArray`
  declarations — as `KOKKOSIFY-TODO`s for the Author agent to resolve. Zero tokens; it
  never guesses.
- **`run_validation.sh`** is the equivalence harness: it compiles a standalone
  validator that links the original MCFM (`libmcfm`) alongside the ported kernels,
  compiled host-side through the Kokkos shim, and runs the two against each other on
  the CPU — no Kokkos build required.
- **`kokkos_host_shim/`** are the small support headers that let device kernel code
  compile and run on the host for that comparison.

### `assets/`
Generated, runtime-only outputs — the roadmap metrics, the symbol index, per-run
scratch and check tables. Not authored by hand; safe to delete and regenerate.
