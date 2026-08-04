# Collaborative AI-Driven Workflows: a Lab Notebook

This lab notebook demonstrates a collaborative approach to embed AI in scientific software
engineering workflows. It is a small, working example of a few fundamental ideas inspired
from principles of software provenance, reproducibility, and scientific rigor.

- **Human teams stay in charge.** The AI does the repetitive rewriting; a human reads and
  approves the result of each step before the next one starts.
- **Plain files drive the work.** People write two files anyone can read: the rules to
  follow and how to tell the result is correct (the Spec), and how to run the step and what
  happened last time (the Plan). The AI writes a third file (the Log), where it plans
  what it wants to do and ticks off each task as it goes.
- **The record lives in git.** The code, the helpers, the Spec, and the Plan sit together
  under version control, so a run can be read, repeated, or changed later.

The rest of this page shows how to run the demo.

## Streamlined workflow interface

The preferred interface for workflow helpers is through a shared command line:

```
python3 dev/workflow.py <command>
```

Representative commands:

```
python3 dev/workflow.py refresh
python3 dev/workflow.py gate mcfm-translate
python3 dev/workflow.py approve mcfm-translate --latest-blocking
python3 dev/workflow.py draft software/mcfm/src/.../file.f
python3 dev/workflow.py verify software/mcfm/src/.../file.cpp -- u u~ e- e+
python3 dev/workflow.py cleanup report
python3 dev/workflow.py closure qqb_z
python3 dev/workflow.py kokkos draft software/mcfm/src/.../file.cpp
python3 dev/workflow.py kokkos validate dev/tools/kokkos/validator_skeleton.cpp
```

The tooling scripts exist under `dev/tools/`, but `dev/workflow.py` is the preferred human- and agent-facing entrypoint.

Typical happy paths:

```bash
# Step 1: Fortran -> C++
python3 dev/workflow.py refresh
python3 dev/workflow.py status
python3 dev/workflow.py next mcfm-translate
python3 dev/workflow.py draft software/mcfm/src/.../file.f
python3 dev/workflow.py verify software/mcfm/src/.../file.cpp -- u u~ e- e+
python3 dev/workflow.py gate mcfm-translate

# Cleanup pass
python3 dev/workflow.py refresh
python3 dev/workflow.py next mcfm-cleanup
python3 dev/workflow.py cleanup report
python3 dev/workflow.py gate mcfm-cleanup

# Step 2: C++ -> Kokkos
python3 dev/workflow.py next pepper-kokkos-port
python3 dev/workflow.py closure qqb_z
python3 dev/workflow.py kokkos draft software/mcfm/src/.../file.cpp
python3 dev/workflow.py kokkos validate dev/tools/kokkos/validator_skeleton.cpp
python3 dev/workflow.py gate pepper-kokkos-port
```

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
changes any code, it writes down what it wants to do in a third file, `agent_log.md` — the
list of files to rewrite and, as it goes, each one's result. The log is the AI's own
working file. Human approvals live separately in `approvals.toml`, which a person updates
through the approval helper command rather than by editing the agent log. The same runner
works for any step; you just point it at a different folder.

## Mathematical Representation

Each step is an optimization over a repository `R`, advanced by *settling* units `u` — the
atoms of work (a source file, a translated family, an amplitude). Three quantities are
computed or checked, never guessed:

- Readiness `ρ(u)` — a unit is ready once its dependencies are settled (from the dependency
  graph in `dev/tools/index/build_roadmap.py`).
- Oracle `V(u)` — the correctness bar; the only source of truth for "correct."
- Status `σ(u) ∈ Σ` — the outcome recorded for a settled unit. `Σ` is fixed per step (the
  Spec's status contract); each `σ` has a class (good / bad) and a reversibility, and a bad or
  irreversible `σ` is risky.

The runner performs a constrained search over the *ready set* (ready, not-yet-settled units):

> maximize progress `f(R)` — units in a good status — subject to the invariants `I` holding
> after every settled unit, acting only on ready units, until the ready set is empty (the
> fixpoint).

Because each settled unit leaves the ready set and `ρ` is acyclic, the search terminates.
Human review is the gate (the control law): completed groups may accumulate up to a batch
limit before approval, and a risky `σ` requires approval at once.

The three plain files are the three parts of this problem:

| file | role | owner |
|------|------|-------|
| Spec `desired_spec.md` | objective `f`, invariants `I`, oracle `V`, status set `Σ` — the *what* | human |
| Plan `current_plan.md` | the policy: which ready unit to act on, and how to group — the *how* | human |
| Log `agent_log.md` | the state and its certificate: each `σ(u)` with the `V` evidence that earned it — the *record* | AI |

Approvals are the gate's input, recorded in `approvals.toml`.

## How to run it

1. **Set up your machine.** Put your machine's name in `config.sh`, add a
   `sites/<name>/config.sh` with your compilers (there is an example in `sites/sedona/`),
   then run `source environment.sh`. Get the code with `git submodule update --init`
   (see the table below).
2. **Run a transformation.** Point CodeScribe at a step's folder:

   ```
   code-scribe loop dev/transformations/<name>/loop.toml -m <model> --<options>
   ```

   - Step 1: `code-scribe loop dev/transformations/mcfm-translate/loop.toml -m <model>`.
     CodeScribe reads the Plan and Spec, writes its `agent_log.md`, finds the files that
     are ready, rewrites them one at a time, and checks its work. Check a run with
     `jobrunner submit tests/mcfm`.

   - Step 2: `code-scribe loop dev/transformations/pepper-kokkos-port/loop.toml -m <model>`.
     This rewrites the C++ files a person already approved in step 1. Check with
     `jobrunner submit tests/pepper`.

CodeScribe writes the result of each file (correct / rewritten / failed) in that step's
`agent_log.md` and adds a note to the Plan's session log. When a human approval is needed,
record it with either:

```
python3 dev/workflow.py approve <name> --latest-blocking
```

or, to approve the oldest pending completed group regardless of whether it is blocking yet,

```
python3 dev/workflow.py approve <name> --latest
```

or, for an explicit group,

```
python3 dev/workflow.py approve <name> "Group ..." --by <name>
```

You can also inspect pending approvals with:

```
python3 dev/workflow.py approve <name> --list-pending
```

This writes `approvals.toml` for that transformation. You can change the step, the
`loop.toml` options, or the AI model to try different runs over the same Spec and Plan.

## The code you are changing (git submodules)

The physics codes are pulled in as git submodules pinned to fixed
versions. `environment.sh` expects them at set paths and sets `$MCFM_HOME`, `$PEPPER_HOME`,
and `$QCDLOOP_HOME`.

| Path | Variable | Submodule | What it is |
|------|----------|-----------|------------|
| `software/mcfm` | `$MCFM_HOME` | `NeuCol/mcfminterface` | MCFM: Fortran rewritten as C++ (step 1), then the C++ that step 2 rewrites. |
| `software/pepper` | `$PEPPER_HOME` | `maxkno/pepper-mcfm-amplitudes` | Pepper: the GPU program; step-2 code goes in `src/mcfm_analytics`. |
| `software/qcdloop` | `$QCDLOOP_HOME` | `ReetBarik/qcdloop` | QCDLoop: a small math library some step-2 code needs. |

```
git submodule update --init            # get all three at their pinned versions
```
