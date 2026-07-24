# MCFM test failure fix plan

This file says how to run the fix pass. The contract and correctness bar are in `desired_spec.md`.

> This Plan is the policy: it selects and orders the work over the ready set (see *When to stop*).
> The correctness contract — objective `f`, invariants `I`, oracle `V`, and status set `Σ` — lives
> in `desired_spec.md`; on conflict the Spec governs.
>
> Authority: the AI may modify only `agent_log.md`; `current_plan.md` and `desired_spec.md` are
> human-owned.

## Each round

1. Run `jobrunner submit tests/mcfm` and identify all processes where any test case does not
   explicitly show `passed`.
2. Continue the open group if one exists. Otherwise check the gate (see Approval gate) before
   opening a new group.
3. For each failing process, diagnose the root cause (see Spec §Diagnosis).
4. Fix the root-cause source file(s). Rebuild; run the specific failing process; confirm all
   cases show `passed`. Then run the full suite to confirm no regression.
5. Record each result in `agent_log.md` (see Log file).
6. Stop per When to stop; otherwise keep going.

## Log file

Keep the changing worklist in `agent_log.md` in this folder. Create it if missing and keep it
current. Use it for failing processes, review groups, and per-process status.

Record each finished process as:

- `- [x] \`<process>\` — FIXED (all cases passed; worst Δrel <value>)`
- `- [x] \`<process>\` — SKIPPED (<reason: upstream not translated / out of scope>)`
- `- [x] \`<process>\` — FAILED (<symptom after fix attempts>)`

Use the process args as the identifier, e.g. `` `u d~ ve e+` ``.

## Approval gate

Review groups live under headings starting with `Group` in `agent_log.md`. Humans do not edit
`agent_log.md`. Human approvals live in `approvals.toml` in this folder and should normally be
recorded with:

```
python3 dev/workflow.py approve mcfm-fix-failures --latest-blocking
```

or, to approve the oldest pending completed group,

```
python3 dev/workflow.py approve mcfm-fix-failures --latest
```

or, for an explicit group,

```
python3 dev/workflow.py approve mcfm-fix-failures "Group ..." --by <name>
```

Use the gate only when deciding whether to start a new group:

```
python3 dev/workflow.py gate mcfm-fix-failures
```

Interpret it this way:

- If a group is still open, you may keep working inside that same group.
- A completed group containing `FAILED` requires approval before the next group starts.
- Otherwise, up to 3 completed groups may accumulate before approval is required.
- A gate failure blocks new-group creation, not diagnosis, fixes, or verification inside the
  current open group.
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

Stop for human review only when the gate blocks the next group.

## Tools

Run these from the project root:

- `jobrunner submit tests/mcfm`
  - full MCFM build + benchmark run; the primary oracle
- `python3 dev/workflow.py gate mcfm-fix-failures`
  - enforce the human approval policy between completed groups
- `python3 dev/workflow.py approve mcfm-fix-failures --latest-blocking`
  - approve the exact group currently blocking the gate
- `python3 dev/workflow.py approve mcfm-fix-failures --latest`
  - approve the oldest pending completed group
- `python3 dev/workflow.py approve mcfm-fix-failures --list-pending`
  - show pending completed groups waiting for approval
- `python3 dev/workflow.py approve mcfm-fix-failures "Group ..." --by <name>`
  - record a human approval for a specific group in `approvals.toml`
- `python3 dev/workflow.py approvals mcfm-fix-failures --group "Group ..."`
  - show the approval record, including any review note, for a specific group
- `python3 dev/workflow.py approvals mcfm-fix-failures --latest-approved`
  - show the most recent approved group and its review note for revision follow-up

## Resolution: which processes to fix next

1. Run `jobrunner submit tests/mcfm` to get the current list of failing or silent processes.
2. Group failing processes by root-cause source file when identifiable — fixing one file fixes
   all processes that exercise it.
3. Fix deepest-dependency files first to avoid fixing the same symptom in multiple processes.
4. Group ~3–5 failing processes per review group; headings must start with `Group`.
5. If there is already an open group, keep fixing that group before opening another.
6. After completing a group, check the gate before opening the next one.
7. After any required approval, read the approval record for that group before continuing.

## Shell notes

CodeScribe bash is restricted. In practice:

- use plain relative paths like `software/mcfm/src/...`
- no `cd`, pipes, redirects, or `$VARIABLES`

## Verify

After applying a fix:

1. Rebuild and run the full suite: `jobrunner submit tests/mcfm`.
2. Confirm every test case in the fixed process explicitly shows `passed`.
3. Confirm no previously-passing process has regressed (all cases still show `passed`).

A process is only settled FIXED when every test case explicitly shows `passed`.

## When to stop

Stop only when one of these is true:

- a completed group needs human approval before the next group can start
- no failing processes remain (every test case in every process shows `passed`)
- a real blocker requires a person (untranslated upstream dependency, build system issue)

Otherwise continue diagnosing, fixing, and verifying.

## Notes / session log

- Fix only root-cause files; do not introduce cleanup or refactoring in this pass.
- When a fix in one process causes a regression, revert and investigate before trying again.
- If a process cannot be fixed because its root-cause file is not yet translated, mark SKIPPED
  and note the upstream dependency.
- Add a dated note per session: which processes are now fixed, what remains, and any blockers.
