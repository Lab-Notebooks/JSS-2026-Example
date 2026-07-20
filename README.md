# Collaborative AI-Driven Workflows: a Lab Notebook

This repository is the demo that accompanies the paper *Designing Collaborative
AI-Driven Workflows for Scientific Software Engineering*. It is a lab notebook: one
versioned directory tree that carries the code, the agentic capabilities, and the
documents needed to stage AI-assisted code modernization. The paper explains the
design principles, the orchestration architecture, and the vocabulary; this page
does not repeat them. It assumes you have read the paper and want to run the demo.

## The top-level workflow

The demo modernizes MCFM, a high-energy-physics matrix-element code, in two staged
transformations with a human-reviewed boundary between them:

1. **Fortran → C++.** Translate the MCFM Fortran sources to C++, then confirm
   correctness by running MCFM's own benchmark tests together with the coverage
   check that the translated unit was actually exercised.
2. **C++ → Kokkos.** Rewrite the accepted C++ as native, device-portable Kokkos
   kernels hosted in Pepper, then verify again against Pepper's tests.

Each stage is defined by two human-readable documents under
`dev/transformations/<transformation>/`: a **Spec** (`desired_spec.md`, the rules
and the verification criteria) and a **Plan** (`current_plan.md`, the checklist
agents tick off). A **Workflow** under `.claude/workflows/` reads those documents
and drives the subagents; the workflows are transformation-agnostic, so the same
script runs any transformation that follows its shape.

## Running the demo

Three steps, once the paper's design is understood.

1. **Configure your site.** Set `SiteName` in `config.sh`, add
   `sites/<site>/config.sh` for your toolchain (a reference `sites/sedona/` is
   provided), then `source environment.sh`. Populate the codebases with
   `git submodule update --init` (see the submodule table below).
2. **Launch Claude Code** in the project root.
3. **Run a workflow for a transformation.** A workflow takes the transformation
   directory as an argument and reads its Spec from there, so it is invoked by name:
   - Stage 1: *"Run `translate` for `dev/transformations/fortran-to-cpp`"* —
     `args:{projectRoot:"<abs>", transformation:"fortran-to-cpp"}`. It discovers the
     ready units, records review bundles in the Plan, translates them, and applies
     the Spec's verification criteria. Verify a run with `jobrunner submit tests/mcfm`.
   - Stage 2: *"Run `port` for `dev/transformations/cpp-to-kokkos`"* —
     `args:{projectRoot:"<abs>", transformation:"cpp-to-kokkos", from:"fortran-to-cpp"}`
     ports the C++ units a human has already accepted in stage 1; pass
     `target:"<name>"` instead to port one. Verify with `jobrunner submit tests/pepper`.

Record each unit's outcome (verified / translated / failed) in the transformation's
`current_plan.md`. Vary the transformation, the workflow, or the per-phase models to
run different experiments over the same documents.

## The codebases (git submodules)

The scientific codebases are third-party software, tracked as git submodules pinned
to specific commits. `environment.sh` expects them at fixed paths and exports
`$MCFM_HOME`, `$PEPPER_HOME`, and `$QCDLOOP_HOME`.

| Path | Variable | Submodule | Role |
|------|----------|-----------|------|
| `software/mcfm` | `$MCFM_HOME` | `NeuCol/mcfminterface` @ `adhruv/Convert_to_c++` | MCFM Fortran translated to C++ (stage 1), then the C++ stage 2 ports. |
| `software/pepper` | `$PEPPER_HOME` | `maxkno/pepper-mcfm-amplitudes` @ `43-add-kokkos-mcfm-interface` | Pepper Kokkos event generator; stage-2 kernels live in `src/mcfm_analytics`. |
| `software/qcdloop` | `$QCDLOOP_HOME` | `ReetBarik/qcdloop` @ `master` | Header-only Kokkos QCDLoop scalar integrals Pepper's `texact` kernels link. |

```
git submodule update --init            # check out all three at their pinned commits
```

## Tree

```
AGENTS.md              agent-facing entry point (agents read this, not the README)
.claude/workflows/     translate.js, port.js, validate.js — transformation-agnostic Workflows
dev/tools/             one directory per Tool; each documents its interface in its own docstring
dev/transformations/   one directory per Transformation: desired_spec.md (Spec) + current_plan.md (Plan)
dev/tmp/               disposable scratch for tool output (git-ignored); durable state lives in the Plan
software/              the external clones (submodules): mcfm, pepper, qcdloop
tests/                 jobrunner wrappers: submit tests/mcfm (stage 1), submit tests/pepper (stage 2)
environment.sh         self-locating environment (exports MCFM_HOME, PEPPER_HOME, QCDLOOP_HOME)
config.sh              site selector; sites/<site>/ holds the toolchain
```
