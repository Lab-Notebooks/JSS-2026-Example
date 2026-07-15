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

The design separates the **coded part** (the **tools** and the orchestration) from
the **documents**:

- **Coded — `dev/tools/` + `.claude/workflows/`.** Each reusable **tool** is a
  deterministic helper in its own directory under `dev/tools/`: `index/`
  (the Doxygen dependency roadmap), `draft/` (the draft annotator, plus the
  `seed_examples.toml` translation template it pairs with), `closure/` (the
  call-tree closure), and `kokkos/` (the Kokkos validation templates + host shim).
  The orchestration that drives subagents through the staged pipeline lives in
  `.claude/workflows/`. Tools are orchestrator-independent — the same tool runs
  under either orchestrator.
- **Documents — `dev/transformations/<transformation>/`.** Each transformation is
  defined by exactly two shared documents: a **Spec** (`desired_spec.md` — the
  translation rules, conventions, and the verification bar) and a **Plan**
  (`current_plan.md` — the human-seeded worklist agents tick off and record
  outcomes in).

## The two transformations

| Stage | Transformation | Documents | Workflow | Verification bar |
|-------|----------------|-----------|----------|------------------|
| 1 | Fortran → C++ | [`dev/transformations/fortran-to-cpp/`](dev/transformations/fortran-to-cpp/) | [`mcfm-translate.js`](.claude/workflows/mcfm-translate.js) | benchmark ratios within `1e-13` **and** a coverage probe confirming the unit is exercised |
| 2 | C++ → Kokkos kernel | [`dev/transformations/cpp-to-kokkos/`](dev/transformations/cpp-to-kokkos/) | [`kokkos-translate.js`](.claude/workflows/kokkos-translate.js) | layered equivalence vs `libmcfm`, doctests passing |

A unit is **verified** only when its bar is met; a unit that builds but is not
exercised is **translated** (unverified) and recorded separately — the operational
form of the paper's principle P1.

## The staged pipeline

The Stage-1 workflow realizes the reference multi-stage translation as ordered phases
(paper §4.2): deterministic steps run as tools, model effort is reserved for
authoring and verification.

```
Index    Doxygen call graph -> dependency ranking + symbol map   dev/tools/index/build_roadmap.py
Resolve  pick the next conflict-free leaf layer (deps==0)        (reads the graph)
Author   per file: Draft then Translate, in parallel            dev/tools/draft/scribe_draft.py + seed_examples.toml
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
and workflow above. When CodeScribe drives this task it reads the same Spec and Plan
under the same verification bar, configured by its own `loop.toml` (which lives with
CodeScribe, not in this artifact); see paper §4.3, Fig. 4.

## Tree

```
.claude/workflows/               coded: staged orchestration (mcfm-translate, kokkos-translate, kokkos-validate-loop)
dev/tools/                       coded: one directory per reusable tool
  index/build_roadmap.py           Doxygen dependency roadmap + symbol map
  draft/scribe_draft.py            draft annotator (+ seed_examples.toml translation template)
  closure/calltree_closure.py      transitive call-tree closure (stage-2 completeness check)
  kokkos/                          Kokkos validation templates + host shim
  assets/                          generated outputs (roadmap, symbol index, …); runtime-only
dev/transformations/             documents: two shared docs per transformation
  fortran-to-cpp/                  desired_spec.md, current_plan.md
  cpp-to-kokkos/                   desired_spec.md, current_plan.md
software/mcfm, software/pepper   per-component folders (Jobfile + setup.sh) for the external clones
tests/                           jobrunner wrappers for the build/benchmark harnesses
environment.sh                   self-locating environment (exports MCFM_HOME, PEPPER_HOME)
config.sh                        site selector (SiteName); sites/<site>/environment.sh holds the toolchain
```

## Running an experiment

1. **Configure the environment.** Edit `config.sh` (`SiteName`) and
   `sites/<site>/environment.sh` for your toolchain (a reference `sites/sedona/` is
   provided), then `source environment.sh`.
2. **Get the codebases.** `git submodule update --init` populates the MCFM and Pepper
   submodules under `software/` (see [`software/README.md`](software/README.md)). For
   Stage 1, also generate the Doxygen XML under `software/mcfm/doxygen_dep/xml`.
3. **Run a transformation.** Launch the workflow on a fixed slice of the Plan:
   - Stage 1: `mcfm-translate` with `args:{projectRoot:"<abs>", resolver:"graph", scope:"ThreeJets"}`.
   - Stage 2: `kokkos-translate` with `args:{projectRoot:"<abs>", amplitude:"qqb_z1jet_v"}`.
   Vary the transformation (which `dev/transformations/<stage>/`), the workflow, or
   the per-phase models to run different experiments over the same documents.
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
