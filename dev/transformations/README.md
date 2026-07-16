# Transformations — the documents that hold intent

A **transformation** moves source code from one state to another, and in this
project the work proceeds as a sequence of them: Fortran → C++, then C++ → Kokkos
kernels, each ending at a human-reviewed verification boundary. This directory holds
the *documents* half of the design — the part a human reads and writes. The *coded*
half, the tools and the orchestration, lives under `dev/tools/` and `.claude/`.

Each transformation is defined by exactly two shared documents, and nothing else:

- **The Spec** (`desired_spec.md`) — the correctness specification. It describes the
  code we want and defines what "done" means *before any agent runs*: the translation
  rules, the conventions, and the verification bar. It is the single source of truth
  for *how*; the workflows and tools point at it rather than repeating it.
- **The Plan** (`current_plan.md`) — a checklist a human seeds and agents then edit,
  ticking units off and recording outcomes. It is the running record the two share
  across sessions.

Together they are the provenance record of the work: intent and state kept in durable,
human-readable files, independent of any one agent's transient context. That
independence is the point. Because the documents live on disk and not
inside an orchestrator, the same transformation can be handed to a different
orchestrator — the Claude Code workflow or the CodeScribe loop — without rewriting
it. One set of documents, either engine, the same verification bar.

The coupling runs only one way, too: a workflow does not name its transformation, it
*takes* one. Each workflow reads the Spec from whatever transformation directory it
is pointed at, so it is invoked as *"Run `<workflow>` for
`dev/transformations/<transformation>`"* — the same script can drive any
transformation that follows its stage's contract.

The two roles of a multidisciplinary team meet on these pages: a domain scientist can
specify and review intent in the Spec, a software engineer maintains the tools the Spec
refers to, and both write the Plan. The verification bar in each Spec is where they
converge, and where a human accepts or rejects a result.

```
fortran-to-cpp/     Stage 1 — Fortran → C++      (bar: benchmark ratios + coverage probe)
  desired_spec.md   the Spec
  current_plan.md   the Plan
cpp-to-kokkos/      Stage 2 — C++ → Kokkos kernel (bar: layered equivalence + doctests)
  desired_spec.md   the Spec
  current_plan.md   the Plan
```

Throughout, one distinction carries the weight of the correctness guarantee: a unit is
**verified** only when its bar is actually met and a check confirms the code was
exercised; anything that merely builds is **translated** and recorded as such. Never
let the two blur.
