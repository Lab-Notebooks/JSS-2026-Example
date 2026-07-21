# Collaborative AI-Driven Workflows: a Lab Notebook

This lab notebook demonstrates a collaborative approach to embed AI in scientific software
engineering workflows. It is a small, working example of a few fundamental ideas inspired
from principles of software provenance, reproducibility, and scientific rigor.

- **Human teams stay in charge.** The AI does the repetitive rewriting; a human reads and
  approves the result of each step before the next one starts.
- **Plain files drive the work.** People write two files anyone can read: the rules to
  follow and how to tell the result is correct (the Spec), and how to run the step and what
  happened last time (the Plan). The AI writes a third file (the Checklist), where it plans
  what it wants to do and ticks off each task as it goes.
- **The record lives in git.** The code, the helpers, the Spec, and the Plan sit together
  under version control, so a run can be read, repeated, or changed later.

The rest of this page shows how to run the demo.

## What the demo does

The demo rewrites MCFM, a physics code, in two steps. A person checks the result after
each step before the next one starts.

1. **Fortran to C++.** Rewrite MCFM's old Fortran code as C++. Then check it is correct
   by running MCFM's own tests, plus a small extra check that the test really used the new
   code.
2. **C++ to Kokkos.** Rewrite that C++ again as Kokkos code, which can run on GPUs, inside
   a program called Pepper. Then check it again with Pepper's tests.

Each step lives in its own folder under `dev/transformations/<step>/`. People write two
plain-text files there:

- a **Spec** (`desired_spec.md`) — the rules to follow, and how to tell the result is
  correct;
- a **Plan** (`current_plan.md`) — how to run the step (the helper programs, the
  running-command rules, which files to do next) and the notes across sessions.

A runner called **CodeScribe** reads the Plan and the Spec and does the work. Before it
changes any code, it writes down what it wants to do in a third file, `agent_checklist.md` — the
list of files to rewrite and, as it goes, each one's result. The checklist is the AI's own
working file: it is not tracked in git, so a fresh clone starts with only the Spec and the
Plan. The same runner works for any step; you just point it at a different folder.

## How to run it

1. **Set up your machine.** Put your machine's name in `config.sh`, add a
   `sites/<name>/config.sh` with your compilers (there is an example in `sites/sedona/`),
   then run `source environment.sh`. Get the code with `git submodule update --init`
   (see the table below).
2. **Run a transformation.** Point CodeScribe at a step's folder:

   ```
   code-scribe loop dev/transformations/<name>/loop.toml -m <model> --<options>
   ```

   - Step 1: `code-scribe loop dev/transformations/fortran-to-cpp/loop.toml -m <model>`.
     CodeScribe reads the Plan and Spec, writes its `agent_checklist.md`, finds the files that
     are ready, rewrites them one at a time, and checks its work. Check a run with
     `jobrunner submit tests/mcfm`.

   - Step 2: `code-scribe loop dev/transformations/cpp-to-kokkos/loop.toml -m <model>`.
     This rewrites the C++ files a person already approved in step 1. Check with
     `jobrunner submit tests/pepper`.

CodeScribe writes the result of each file (correct / rewritten / failed) in that step's
`agent_checklist.md` and adds a note to the Plan's session log. You can change the step, the
`loop.toml` options, or the AI model to try different runs over the same Spec and Plan.

## The code you are changing (git submodules)

The physics codes are pulled in as git submodules pinned to fixed
versions. `environment.sh` expects them at set paths and sets `$MCFM_HOME`, `$PEPPER_HOME`,
and `$QCDLOOP_HOME`.

| Path | Variable | Submodule | What it is |
|------|----------|-----------|------------|
| `software/mcfm` | `$MCFM_HOME` | `NeuCol/mcfminterface` | MCFM: Fortran rewritten as C++ (step 1), then the C++ that step 2 rewrites. |
| `software/pepper` | `$PEPPER_HOME` | `maxkno/pepper-mcfm-amplitudes` | Pepper: the GPU program; step-2 code goes in `src/mcfm_analytics`. |
| `software/qcdloop` | `$QCDLOOP_HOME` | `ReetBarik/qcdloop` @ `master` | QCDLoop: a small math library some step-2 code needs. |

```
git submodule update --init            # get all three at their pinned versions
```
