# Collaborative AI-Driven Workflows — a Lab Notebook

This repository is a worked example of **designing collaborative, AI-driven
workflows for scientific software engineering.** It is a *lab notebook*: a single
versioned directory tree that carries the code, the agentic capabilities, and the
documents needed to run staged, AI-assisted code-modernization transformations — so
that cloning the tree shares both the work and the means to continue it.

It is also meant to be *read*. A collaborative workflow should be legible: humans own
intent and acceptance, deterministic tools do the mechanical steps, and a thin
orchestration layer drives agents while pointing at a shared specification rather than
restating it. The files here are written to show that, not just to run it. If you read
only three things, read this page, then the two guided tours it links to below, then
one Spec.

The scientific codebases themselves (MCFM and Pepper) are obtained separately; see
[`software/README.md`](software/README.md).

## The shape of the design: documents and coded capabilities

The whole design turns on one separation — what a human writes from what an agent
runs:

- **Documents — [`dev/transformations/`](dev/transformations/).** Each transformation
  is defined by exactly two shared, human-readable documents: a **Spec**
  (`desired_spec.md`, the rules and the verification bar) and a **Plan**
  (`current_plan.md`, the worklist agents tick off). They hold intent and state,
  independent of any orchestrator. → guided tour:
  [`dev/transformations/README.md`](dev/transformations/README.md).
- **Coded — [`dev/tools/`](dev/tools/) + [`.claude/workflows/`](.claude/workflows/).**
  The **tools** are deterministic capabilities an agent invokes instead of a model
  call; the **workflows** are the orchestration that drives subagents through the
  staged pipeline. → guided tour: [`dev/tools/README.md`](dev/tools/README.md).

Keeping the documents separate from the orchestrator is what lets the *same* task run
under either agent — the Claude Code workflow or the CodeScribe loop — against the
same verification bar.

## The two transformations

| Stage | Transformation | Documents | Workflow | Verification bar |
|-------|----------------|-----------|----------|------------------|
| 1 | Fortran → C++ | [`fortran-to-cpp/`](dev/transformations/fortran-to-cpp/) | [`mcfm-translate.js`](.claude/workflows/mcfm-translate.js) | benchmark ratios within `1e-13` **and** a coverage probe confirming the unit is exercised |
| 2 | C++ → Kokkos kernel | [`cpp-to-kokkos/`](dev/transformations/cpp-to-kokkos/) | [`kokkos-translate.js`](.claude/workflows/kokkos-translate.js) | layered equivalence vs `libmcfm`, doctests passing |

One distinction carries the correctness guarantee throughout: a unit is **verified**
only when its bar is met and a check confirms the code was exercised; a unit that
merely builds is **translated** (unverified) and recorded separately.

## The staged pipeline

The stage-1 workflow runs as ordered phases — deterministic steps as tools, model
effort reserved for authoring and verification:

```
Index      Doxygen call graph -> dependency ranking + symbol map   (a tool)
Resolve    pick the next leaf layer (files with no untranslated deps)
Author     per file: Draft then Translate, in PARALLEL, size-gated
Integrate  SERIAL: rewire CMake, build once, verify + coverage probe (the trust anchor)
Fix        escalate FAILED units to a stronger model; then to a human
```

Two structural choices recur and are worth naming: **authoring is parallel but
integration is serial** (many authors write only their own files; one integrator owns
the build and the correctness check), and **authoring is size-gated** (an ordinary
file goes to a lighter model, a large one to a stronger model). Stage 2 mirrors this
as `Triage → (Direct | Split → Author → Assemble) → Validate → Test`, with the nested
validate↔fix [`kokkos-validate-loop.js`](.claude/workflows/kokkos-validate-loop.js) —
the minimal "loop" primitive: a deterministic cycle whose state lives on disk.

## CodeScribe (the second orchestrator)

CodeScribe is a collaborator's agent with its own orchestration. It is **not run**
here; its *index / draft / translate* mechanics are replicated as the tools and
workflows above. When CodeScribe drives this task it reads the same Spec and Plan
under the same verification bar, configured by its own `loop.toml` (which lives with
CodeScribe, not in this artifact). The point of holding the documents fixed is to let
a comparison isolate the orchestrator, not the task.

## Tree

```
.claude/workflows/     coded: staged orchestration (mcfm-translate, kokkos-translate, kokkos-validate-loop)
dev/tools/             coded: one directory per tool (see dev/tools/README.md)
  index/               the Index tool — Doxygen dependency roadmap + symbol map
  draft/               the Draft tool + seed_examples.toml (worked examples)
  closure/             the Closure tool — call-tree closure (stage-2 completeness)
  kokkos/              Kokkos pre-pass, validation harness, host shim
  assets/              generated outputs; runtime-only
dev/transformations/   documents: Spec + Plan per transformation (see dev/transformations/README.md)
  fortran-to-cpp/        desired_spec.md, current_plan.md
  cpp-to-kokkos/         desired_spec.md, current_plan.md
software/mcfm, pepper  per-component folders for the external clones
tests/                 jobrunner wrappers for the build/benchmark harnesses
environment.sh         self-locating environment (exports MCFM_HOME, PEPPER_HOME)
config.sh              site selector; sites/<site>/ holds the toolchain
```

## Running an experiment

1. **Configure the environment.** Edit `config.sh` (`SiteName`) and
   `sites/<site>/environment.sh` for your toolchain (a reference `sites/sedona/` is
   provided), then `source environment.sh`.
2. **Get the codebases.** `git submodule update --init` populates MCFM and Pepper
   under `software/` (see [`software/README.md`](software/README.md)). For stage 1,
   also generate the Doxygen XML under `software/mcfm/doxygen_dep/xml`.
3. **Run a transformation.** A workflow is independent of the transformation it
   drives — it takes the transformation directory as an argument and reads the Spec
   from there — so it is invoked as *"Run `<workflow>` for
   `dev/transformations/<transformation>`"*:
   - Stage 1: run `mcfm-translate` for `dev/transformations/fortran-to-cpp` —
     `args:{projectRoot:"<abs>", transformation:"fortran-to-cpp", scope:"ThreeJets"}`.
   - Stage 2: run `kokkos-translate` for `dev/transformations/cpp-to-kokkos` —
     `args:{projectRoot:"<abs>", transformation:"cpp-to-kokkos", amplitude:"qqb_z1jet_v"}`.
   `transformation` defaults to each stage's directory, so it can be omitted for the
   defaults. Vary the transformation, the workflow, or the per-phase models to run
   different experiments over the same documents.
4. **Verify and record.** `jobrunner submit tests/mcfm` (or the stage-2 doctests)
   applies the bar; record per-unit outcomes in the transformation's `current_plan.md`.

## The design in four commitments

Everything above serves four commitments, and it is worth naming them:

- **Correctness is verified at every boundary.** A transformation is not done when it
  compiles — it is done when a check a scientist accepts has passed, and the workflow
  must confirm the check actually reached the code (the coverage probe,
  `fortran-to-cpp/desired_spec.md` §5).
- **Humans own intent and acceptance; agents own mechanical breadth.** Agents expand
  breadth in parallel; humans hold the small number of high-value decision points —
  acceptance at each boundary, and the failures agents cannot resolve.
- **Reproducibility and provenance.** State lives in durable, human-readable files —
  the Spec and Plan — not in an agent's transient context, so a run can be inspected,
  resumed, and audited.
- **Collaboration across disciplines.** The units of work are packaged so a domain
  scientist can specify and review intent while a software engineer maintains the
  tools, and the two meet at the same verification boundary.
