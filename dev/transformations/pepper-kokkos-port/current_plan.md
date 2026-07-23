# C++ → Kokkos plan

This file says how to run step 2. The kernel contract and correctness bar are in
`desired_spec.md`.

> This Plan is the policy: it selects and orders the work over the ready set (see *When to
> stop*). The correctness contract — objective `f`, invariants `I`, oracle `V`, and status set
> `Σ` — lives in `desired_spec.md`; on conflict the Spec governs.

## Log file

Keep the changing worklist in `agent_log.md` in this folder. Create it if missing and
keep it current. Use it for active amplitudes, review groups, and per-amplitude status. Keep
session prose in the log at the end of this file.

Record each finished amplitude as:

- `- [x] <name> — TRANSLATED (maxRelErr <value>)`
- `- [ ] <name> — FAILED (<what went wrong>)`
- `- [x] <name> — VERIFIED (<doctest>)` only by a person after a doctest lands

Use paths like `software/pepper/src/mcfm_analytics/...`.

## Approval gate

Review groups live under headings starting with `Group` in `agent_log.md`. Humans do not edit
`agent_log.md`. Human approvals live in `approvals.toml` in this folder and should normally be
recorded with:

```
python3 dev/workflow.py approve pepper-kokkos-port --latest-blocking
```

or, to approve the oldest pending completed group,

```
python3 dev/workflow.py approve pepper-kokkos-port --latest
```

or, for an explicit group,

```
python3 dev/workflow.py approve pepper-kokkos-port "Group ..." --by <name>
```

Check with:

```
python3 dev/workflow.py gate pepper-kokkos-port
```

Interpret it this way:

- If a group is still open, you may keep working inside that same group.
- A completed group containing `FAILED` requires approval before the next group starts.
- Otherwise, up to 2 completed groups may accumulate before approval is required.
- The gate checks only whether a group is approved; it does not interpret `approvals.toml`
  `review_note` text.
- After a group is approved, agents should read any matching approval record in
  `approvals.toml` before continuing work related to that group.
- Treat review notes as binding human guidance for that group unless a later human
  instruction supersedes them.
- If a review note changes scope or forbids an action, revise that same approved group
  rather than opening a replacement group just to apply the review note.
- A revision keeps the original approval logic unchanged: the group remains the same group,
  but the agent must update code and `agent_log.md` so the final recorded outcome matches the
  approved human guidance.
- If a review note conflicts with an already-logged result, treat the group as follow-up work
  in place: fix the affected files, update that group's entries, and add a session-log note
  describing the revision before starting unrelated new-group work.

If the gate fails, stop before opening the next group.

## Tools

Run these from the project root. Prefer the unified workflow interface:

- `python3 dev/workflow.py closure <name>`
  - transitive linked closure, stage-1 readiness, and existing reuse
- `python3 dev/workflow.py kokkos draft <input.cpp> [-o draft.h] [-r report.md]`
  - mechanical first draft plus blockers
- `python3 dev/workflow.py kokkos validate <validator.cpp>`
  - compare the ported kernel against `libmcfm`
- `python3 dev/workflow.py gate pepper-kokkos-port`
  - enforce the human approval policy between groups
- `python3 dev/workflow.py approve pepper-kokkos-port --latest-blocking`
  - approve the exact group currently blocking the gate
- `python3 dev/workflow.py approve pepper-kokkos-port --latest`
  - approve the oldest pending completed group
- `python3 dev/workflow.py approve pepper-kokkos-port --list-pending`
  - show pending completed groups waiting for approval
- `python3 dev/workflow.py approve pepper-kokkos-port "Group ..." --by <name>`
  - record a human approval for a specific group in `approvals.toml`
- `python3 dev/workflow.py approvals pepper-kokkos-port --group "Group ..."`
  - show the approval record, including any review note, for a specific group
- `python3 dev/workflow.py approvals pepper-kokkos-port --latest-approved`
  - show the most recent approved group and its review note for revision follow-up
- `jobrunner submit tests/mcfm`
- `jobrunner submit tests/pepper`
  - build and test both codebases

The low-level scripts under `dev/tools/` remain available, but `dev/workflow.py` is the preferred interface.
Build both codebases once before the first round if needed.

## Resolution: which target to do next

- Do Born before virtual when both exist.
- A target is ready only when:
  1. Closure shows its full call tree is in C++.
  2. The needed step-1 files are marked `VERIFIED` in
     `dev/transformations/mcfm-translate/agent_log.md`.
- Size the closure before starting:
  - about 30 linked pieces or fewer: do it directly
  - larger trees: split by function boundary and work bottom-up

## Authoring steps

1. Map the full call tree, globals, blockers, and reusable ported helpers.
2. Use Kokkosify for the mechanical draft.
3. Write the real kernel from the Spec:
   - helpers first
   - then `<name>_me2(p, params)`
   - then the event kernel
   - then the one-line `.cpp`
4. Replace QCDLoop calls with direct formulas where needed.
5. Validate against `libmcfm` layer by layer until the kernel matches.
6. Add the header and `.cpp` to `src/CMakeLists.txt`, then run `jobrunner submit tests/pepper`.
7. Do not add new doctests. Report which doctests a developer should add.

## Splitting a large tree

If the closure is too large for one pass:

1. Split only at function boundaries.
2. Do leaves first, then sub-amplitudes, then the join.
3. Check each piece against its `libmcfm` twin before freezing it.
4. Join frozen pieces into the final kernel. If pieces pass but the final `|M|²` does not, fix
   the join, not the frozen pieces.

The desired split layout is defined in the Spec.

## When to stop

The *ready set* is the set of ready, not-yet-settled amplitudes (closure in C++ and its
step-1 files `VERIFIED`). Each settled amplitude leaves the ready set and the readiness graph
is acyclic, so the pass terminates. Stop only when one of these is true:

- a completed group needs human approval before the next group can start
- the ready set is empty (no ready amplitude to work on)
- a real blocker requires a person

## Shell notes

CodeScribe bash is restricted. In practice:

- use plain relative paths under `software/mcfm/...` and `software/pepper/...`
- no `cd`, pipes, redirects, or `$VARIABLES`

## Notes / session log

- Existing reference kernels live in `software/pepper/src/mcfm_analytics/`: `qqb_z`,
  `qqb_z_v`, `qqb_z1jet`, `qqb_z1jet_v`.
- `qqb_z2jet` is the main split-demo target. `qqb_z2jet_v` is the hard case because of box
  integrals near threshold.
- The stage-2 correctness target is “matches MCFM”, not independent physics validation.
- `Kokkos::complex` division typically limits agreement to about `1e-10` in division-heavy code.
- Add a dated note per session: what you changed, what remains, and any human decision needed.
