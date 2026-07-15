# Collaborative AI-Driven Workflows — Lab Notebook

This repository is the reproducible artifact for the paper **"Designing
Collaborative AI-Driven Workflows for Scientific Software Engineering."** It is a
*lab notebook* in the paper's sense (Fig. 1): a single versioned directory tree that
carries the code, the agentic capabilities, and the documents needed to run staged
AI-assisted code-modernization transformations, so that cloning the tree shares both
the work and the means to continue it.

It packages the paper's **staged transformation workflow** for two transformations of
the MCFM high-energy-physics code, each with a numerical verification boundary. The
scientific codebases themselves are obtained separately; see
[`software/README.md`](software/README.md).

## The two parts: coded capabilities, and documents

The design separates the **coded part** from the **documents**:

- **Coded — `tools/` + `.claude/workflows/`.** Deterministic helpers (the Doxygen
  index, the call-tree closure, the draft annotator, the Kokkos validation
  templates) live in `tools/`; the orchestration that drives subagents through the
  staged pipeline lives in `.claude/workflows/`.
- **Documents — `dev/<transformation>/`.** Each transformation is defined by a
  **Spec** (`desired_spec.md` — the translation rules, conventions, and the
  verification bar) and a **Plan** (`current_plan.md` — the human-seeded worklist
  agents tick off and record outcomes in). Stage 1 also carries the few-shot
  **seed examples** (`seed_examples.toml`) the translate step reads, and a
  `loop.toml` documenting the reference CodeScribe orchestrator's input.

## The two transformations

| Stage | Transformation | Documents | Workflow | Verification bar |
|-------|----------------|-----------|----------|------------------|
| 1 | Fortran → C++ | [`dev/fortran-to-cpp/`](dev/fortran-to-cpp/) | [`mcfm-translate.js`](.claude/workflows/mcfm-translate.js) | benchmark ratios within `1e-13` **and** a coverage probe confirming the unit is exercised |
| 2 | C++ → Kokkos kernel | [`dev/cpp-to-kokkos/`](dev/cpp-to-kokkos/) | [`kokkos-translate.js`](.claude/workflows/kokkos-translate.js) | layered equivalence vs `libmcfm`, doctests passing |

A unit is **verified** only when its bar is met; a unit that builds but is not
exercised is **translated** (unverified) and recorded separately — the operational
form of the paper's principle P1.

## The staged pipeline

The Stage-1 workflow realizes the reference multi-stage translation as ordered phases
(paper §4.2): deterministic steps run as tools, model effort is reserved for
authoring and verification.

```
Index    Doxygen call graph -> dependency ranking + symbol map   tools/build_roadmap.py
Resolve  pick the next conflict-free leaf layer (deps==0)        (reads the graph)
Author   per file: Draft then Translate, in parallel            tools/scribe_draft.py + seed_examples.toml
Integrate  serial: rewire CMake, build once, verify + probe      (the trust anchor)
Fix      escalate FAILED units to a stronger model
```

- **Index** is Doxygen-based — a collaborator generated the call graph with Doxygen
  rather than a regex scan, so the index command emits both the leaf ranking and the
  symbol→file map the Draft step uses.
- **Author** replicates the reference *draft → translate* mechanism: `scribe_draft.py`
  emits a machine `<base>.scribe` draft (external-function hints + a mechanical
  first cut), and the subagent refines it into real C++/Fortran using the worked
  examples in `seed_examples.toml` and the Spec. Authoring is parallel and
  **size-gated**; integration is a single serial agent — the verification trust anchor.

Stage 2 is `Triage → (Direct | Split → Author → Assemble) → Validate → Test`, driven
by [`kokkos-translate.js`](.claude/workflows/kokkos-translate.js) with the nested
validate↔fix loop [`kokkos-validate-loop.js`](.claude/workflows/kokkos-validate-loop.js).

## CodeScribe (reference orchestrator)

CodeScribe is a collaborator's agent with special capabilities. It is **not run**
here; its valuable *index / draft / translate* mechanics are replicated as the tools
and workflow above, and `dev/fortran-to-cpp/loop.toml` documents how that reference
loop would read the same Spec and Plan under the same verification bar (paper §4.3).

## Tree

```
.claude/workflows/     coded: staged orchestration (mcfm-translate, kokkos-translate, kokkos-validate-loop)
tools/                 coded: build_roadmap.py (Doxygen index), calltree_closure.py, scribe_draft.py, kokkos/
dev/fortran-to-cpp/    documents: desired_spec.md, current_plan.md, seed_examples.toml, loop.toml
dev/cpp-to-kokkos/     documents: desired_spec.md, current_plan.md
software/              setup scripts + pointer README for the external MCFM/Pepper clones
tests/                 jobrunner wrappers for the build/benchmark harnesses
environment.sh         self-locating environment (exports MCFM_HOME, PEPPER_HOME)
config.sh              site selector (SiteName); sites/<site>/environment.sh holds the toolchain
```

## Running an experiment

1. **Configure the environment.** Edit `config.sh` (`SiteName`) and
   `sites/<site>/environment.sh` for your toolchain (a reference `sites/sedona/` is
   provided), then `source environment.sh`.
2. **Get the codebases.** `jobrunner setup software` (or clone by hand per
   [`software/README.md`](software/README.md)) places the MCFM and Pepper clones. For
   Stage 1, also generate the Doxygen XML under `software/mcfm/doxygen_dep/xml`.
3. **Run a transformation.** Launch the workflow on a fixed slice of the Plan:
   - Stage 1: `mcfm-translate` with `args:{projectRoot:"<abs>", resolver:"graph", scope:"ThreeJets"}`.
   - Stage 2: `kokkos-translate` with `args:{projectRoot:"<abs>", amplitude:"qqb_z1jet_v"}`.
   Vary the transformation (which `dev/<stage>/`), the workflow, or the per-phase
   models to run different experiments over the same documents.
4. **Verify and record.** `jobrunner submit tests/mcfm` (or the Stage-2 doctests)
   applies the bar; record per-unit outcomes in the transformation's `current_plan.md`.

## Map to the paper

- Lab-notebook structure — §2, Fig. 1.
- Design principles P1–P4 — §3: P1 in `desired_spec.md` §6 (the coverage probe); P2
  in the workflows' bounded escalation to a human; P3 in the durable Spec/Plan
  documents; P4 in the co-authored documents.
- Vocabulary and one-set-of-inputs / two-orchestrators — §4.1, Figs. 3–4.
- Staged transformations, middle-out, the index→…→verify pipeline — §4.2–§4.3.
- Verification criteria (translated vs verified, coverage probe) — §5.2,
  `desired_spec.md` §6.
