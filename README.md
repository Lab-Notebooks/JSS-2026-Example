# Collaborative AI-Driven Workflows: a Lab Notebook

This is the demo for the paper *Designing Collaborative AI-Driven Workflows for
Scientific Software Engineering*. It is a "lab notebook": one folder, kept in git, that
holds the code, the AI helpers, and the notes needed to change scientific software with
help from AI agents. The paper explains the ideas. This page only shows how to run the
demo, and assumes you have read the paper.

## What the demo does

The demo rewrites MCFM, a physics code, in two steps. A person checks the result after
each step before the next one starts.

1. **Fortran to C++.** Rewrite MCFM's old Fortran code as C++. Then check it is correct
   by running MCFM's own tests, plus a small extra check that the test really used the new
   code.
2. **C++ to Kokkos.** Rewrite that C++ again as Kokkos code, which can run on GPUs, inside
   a program called Pepper. Then check it again with Pepper's tests.

Each step is described by two plain-text files in `dev/transformations/<step>/`:

- a **Spec** (`desired_spec.md`) — the rules to follow, and how to tell the result is
  correct;
- a **Plan** (`current_plan.md`) — the checklist of what to do and what is done.

A **workflow** in `.claude/workflows/` reads those two files and does the work. The same
workflow works for any step; you just point it at a different folder.

## How to run it

Three steps, once you have read the paper.

1. **Set up your machine.** Put your machine's name in `config.sh`, add a
   `sites/<name>/config.sh` with your compilers (there is an example in `sites/sedona/`),
   then run `source environment.sh`. Get the code with `git submodule update --init`
   (see the table below).
2. **Start Claude Code** in this folder.
3. **Run a workflow on a step.** You point a workflow at a step's folder:
   - Step 1: *"Run `translate` for `dev/transformations/fortran-to-cpp`"* —
     `args:{projectRoot:"<path>", transformation:"fortran-to-cpp"}`. It finds the files
     that are ready, lists them in the Plan in review-sized groups, rewrites them, and
     checks them. Check a run with `jobrunner submit tests/mcfm`.
   - Step 2: *"Run `port` for `dev/transformations/cpp-to-kokkos`"* —
     `args:{projectRoot:"<path>", transformation:"cpp-to-kokkos", from:"fortran-to-cpp"}`
     rewrites the C++ files a person already approved in step 1; or pass `target:"<name>"`
     to do just one. Check with `jobrunner submit tests/pepper`.

Write the result of each file (correct / rewritten / failed) in that step's
`current_plan.md`. You can change the step, the workflow, or the AI models to try
different runs over the same two files.

The workflow is one way to run a step. You can run the same two files with a second
runner, CodeScribe, using the `loop.toml` in each step's folder
(`code-scribe loop -p dev/transformations/<step>/loop.toml -m <model>`). Same input files,
either runner, same correctness check.

## The code you are changing (git submodules)

The physics codes are other people's software, pulled in as git submodules pinned to fixed
versions. `environment.sh` expects them at set paths and sets `$MCFM_HOME`, `$PEPPER_HOME`,
and `$QCDLOOP_HOME`.

| Path | Variable | Submodule | What it is |
|------|----------|-----------|------------|
| `software/mcfm` | `$MCFM_HOME` | `NeuCol/mcfminterface` @ `adhruv/Convert_to_c++` | MCFM: Fortran rewritten as C++ (step 1), then the C++ that step 2 rewrites. |
| `software/pepper` | `$PEPPER_HOME` | `maxkno/pepper-mcfm-amplitudes` @ `43-add-kokkos-mcfm-interface` | Pepper: the GPU program; step-2 code goes in `src/mcfm_analytics`. |
| `software/qcdloop` | `$QCDLOOP_HOME` | `ReetBarik/qcdloop` @ `master` | QCDLoop: a small math library some step-2 code needs. |

```
git submodule update --init            # get all three at their pinned versions
```

## Folder map

```
AGENTS.md              what an AI agent reads first (agents read this, not the README)
.claude/workflows/     the workflows: translate.js, port.js, validate.js (work for any step)
dev/tools/             small helper programs; each one explains itself at the top of its file
dev/transformations/   one folder per step: desired_spec.md (Spec), current_plan.md (Plan), loop.toml (CodeScribe)
dev/tmp/               throwaway scratch files (not kept in git); the real record is the Plan
software/              the physics codes (submodules): mcfm, pepper, qcdloop
tests/                 run the checks: jobrunner submit tests/mcfm (step 1), tests/pepper (step 2)
environment.sh         sets the paths (MCFM_HOME, PEPPER_HOME, QCDLOOP_HOME)
config.sh              picks your machine; sites/<name>/ holds your compilers
```
