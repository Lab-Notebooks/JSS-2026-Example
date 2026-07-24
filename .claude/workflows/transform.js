// Workflow: transform — run one review group of any dev/transformations/<name> step.
//
// This repo's transformations (mcfm-translate, mcfm-cleanup, pepper-kokkos-port, and any
// future one) each live in dev/transformations/<name>/ as two plain files: a Spec
// (desired_spec.md — the rules and correctness bar) and a Plan (current_plan.md — how to
// run it: log conventions, an approval gate, a tool list, and a "Resolution" section for
// picking the next targets). A third file, agent_log.md, is the running worklist a runner
// writes and keeps current. Human approvals live separately in approvals.toml, recorded
// with dev/tools/approve/approve_group.py — never by editing agent_log.md by hand.
//
// This script is transformation-agnostic on purpose: it never hardcodes a status word, a
// tool name, or a domain rule. Every prompt below tells the agent to read that
// transformation's own Spec/Plan and follow it exactly; the script only supplies the
// structure (what runs in parallel vs. serially, when the approval gate is checked, and
// what happens to a failure). The same file works for any step — point it at a different
// folder. Start it with:
//   Run transform for dev/transformations/<name>
//
// dev/transformations/*/loop.toml belongs to a different orchestrator (CodeScribe) and is
// not used here — do not read it.
//
// One review group per invocation, by design. dev/tools/approve/check_gate.py decides
// whether a new group may open: some transformations allow a small backlog of completed-
// but-unapproved groups (see each Plan's "Approval gate" section for the exact risky-status
// list and batch limit), but a risky completed group always blocks immediately. The
// workflow continues an already-open group, or opens exactly one new group if the gate
// allows, then stops. Re-invoke it (or wrap it in /loop) to keep going across sessions.
//
// Five phases. The two ideas worth noticing are "write the intent down before the work,
// write the group's own outcome after it" and "write in parallel, combine one at a time":
//   Triage     decide what to work on (open group, or a new one if the gate allows),
//              following the Plan's own Resolution rule and tools — no edits yet
//   Bundle     write the group heading + one unchecked line per unit to the log, so the
//              intent is on disk even if a later phase fails
//   Author     IN PARALLEL, one agent per unit, touching only that unit's own files
//   Integrate  ONE AT A TIME: one agent owns the shared build tree, runs the Spec's own
//              correctness-bar command(s), and records each unit's result
//   Fix        a FAILED unit goes to a stronger model, then gets integrated again
//
// Config (args): transformation (required — a folder under dev/transformations/),
//                scope (optional hint, e.g. a src/ subfolder; ignored if the Spec has no
//                notion of scope), maxUnits (safety cap on ready candidates fetched, 40),
//                bundleSize (override the group size; default: use the Plan's own stated
//                size), fixRounds (escalation rounds over FAILED units, 1),
//                model / triageModel / authorModel / integrateModel / fixModel.

export const meta = {
    name: 'transform',
    description: 'Run one review group of a dev/transformations/<name> step: continue an open group or open a new one (subject to the approval gate), author its ready units in parallel, integrate and verify them serially, escalate failures, and record everything in agent_log.md. Transformation-agnostic — every rule comes from that step\'s own desired_spec.md and current_plan.md, never from this script.',
    whenToUse: 'Point it at any folder under dev/transformations/ via args:{transformation:"mcfm-translate"|"mcfm-cleanup"|"pepper-kokkos-port"|...}. Honors the approval gate (dev/tools/approve/check_gate.py) before opening a new review group, and stops after one group so a human can approve via approve_group.py. Optional: scope, maxUnits, bundleSize, fixRounds, model overrides.',
    phases: [{
            title: 'Triage'
        },
        {
            title: 'Bundle'
        },
        {
            title: 'Author'
        },
        {
            title: 'Integrate',
            model: 'opus'
        },
        {
            title: 'Fix',
            model: 'opus'
        },
    ],
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const cfg = typeof args === 'string' ? JSON.parse(args) : args || {}

const TRANSFORMATION = (cfg.transformation || '')
    .replace(/^dev\/transformations\//, '')
    .replace(/\/$/, '')
if (!TRANSFORMATION) {
    throw new Error(
        'args.transformation is required — a folder under dev/transformations/, e.g. "mcfm-translate"'
    )
}

const DIR = `dev/transformations/${TRANSFORMATION}`
const SPEC = `${DIR}/desired_spec.md`
const PLAN = `${DIR}/current_plan.md`
const LOG = `${DIR}/agent_log.md`

const SCOPE = cfg.scope || 'all'
const MAXUNITS = cfg.maxUnits || 40
const BUNDLESIZE = cfg.bundleSize || null // null => let the agent use the Plan's own stated group size
const FIXROUNDS = cfg.fixRounds ?? 1

// Triage/Bundle/Author inherit the session model unless overridden. Integrate is the
// serial verification trust anchor and Fix is failure escalation, so both default to a
// stronger model — override per-phase or globally with args.model.
const TRIAGE_MODEL = cfg.model || cfg.triageModel
const AUTHOR_MODEL = cfg.model || cfg.authorModel
const INTEGRATE_MODEL = cfg.model || cfg.integrateModel || 'opus'
const FIX_MODEL = cfg.model || cfg.fixModel || 'opus'

// Repeated in every prompt below: two things this repo's Plans mention that do not apply
// to us. The Plans were written with CodeScribe (a different, more restricted runner) in
// mind, and loop.toml is CodeScribe's own config — not ours.
const NOTES = `You have normal Bash tool access (cd, pipes, redirects, variables all work) —
ignore any note in the Plan about a restricted shell; that applies to a different runner,
not you. Do not read or follow dev/transformations/*/loop.toml — it belongs to that other
orchestrator (CodeScribe) and has nothing to do with this run.`

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------

const TRIAGE_SCHEMA = {
    type: 'object',
    properties: {
        stop: {
            type: 'boolean',
            description: 'true if there is nothing safe to do this round'
        },
        stopReason: {
            type: 'string',
            description: 'why: gate blocked, gate errored, no ready units, or a real blocker needing a person',
        },
        gateChecked: {
            type: 'boolean',
            description: 'true if check_gate.py was run because a new group needed to be opened',
        },
        gateBlocked: {
            type: 'boolean'
        },
        opened: {
            type: 'boolean',
            description: 'true if this round needs to open a brand-new group (gate allowed it, or no log/groups exist yet)',
        },
        groupId: {
            type: 'string',
            description: 'the existing OPEN group heading to continue, if any (omit/empty if opening a new one)',
        },
        units: {
            type: 'array',
            items: {
                type: 'object',
                properties: {
                    unit: {
                        type: 'string',
                        description: 'path or id of the thing to work on, in the vocabulary the Spec/Plan use'
                    },
                    verify: {
                        type: 'string',
                        description: 'verification handle for this unit (bench/process/oracle), per the Plan/Spec, or "" if none'
                    },
                    notes: {
                        type: 'string'
                    },
                },
                required: ['unit'],
            },
        },
        layerSize: {
            type: 'integer',
            description: 'total ready candidates in scope before the maxUnits cap'
        },
    },
    required: ['stop', 'units'],
}

const BUNDLE_SCHEMA = {
    type: 'object',
    properties: {
        groupId: {
            type: 'string',
            description: 'the heading text now in effect for this round\'s units'
        },
        written: {
            type: 'boolean'
        },
    },
    required: ['written', 'groupId'],
}

const AUTHOR_SCHEMA = {
    type: 'object',
    properties: {
        unit: {
            type: 'string'
        },
        done: {
            type: 'string',
            enum: ['yes', 'deferred', 'failed']
        },
        notes: {
            type: 'string',
            description: 'missing shared symbol, deferral reason, or suspected mistake'
        },
    },
    required: ['unit', 'done'],
}

const INTEGRATE_SCHEMA = {
    type: 'object',
    properties: {
        verifyOk: {
            type: 'boolean',
            description: 'true if the Spec\'s correctness-bar command(s) passed for this round\'s units'
        },
        rows: {
            type: 'array',
            items: {
                type: 'object',
                properties: {
                    unit: {
                        type: 'string'
                    },
                    status: {
                        type: 'string',
                        description: 'the EXACT status word from the Spec\'s own vocabulary — never invented, never a status the Spec reserves for a human',
                    },
                    notes: {
                        type: 'string'
                    },
                },
                required: ['unit', 'status'],
            },
        },
        groupClosed: {
            type: 'boolean',
            description: 'true only if EVERY unit in the full group (not just this round) now has a non-FAILED status',
        },
    },
    required: ['verifyOk', 'rows'],
}

// ---------------------------------------------------------------------------
// Phase 1 — Triage: decide what this round works on. No edits yet.
// ---------------------------------------------------------------------------

phase('Triage')

const triagePrompt = `You are the TRIAGE phase for the "${TRANSFORMATION}" transformation. ${NOTES}

Read, in this order:
1. ${PLAN} — how this step is run: its log conventions, its approval-gate rule, its tool
   list, and its "Resolution" section (which targets are ready and how to group them).
2. ${SPEC} — the rules and correctness bar this step must satisfy.
3. ${LOG} — the running worklist. It may not exist yet; that just means this is the first
   round for this step.

Then decide, in order:

A. Is there an OPEN group in ${LOG} — a heading starting with "Group" that has any line not
   yet checked off, or checked off as FAILED? If so, set groupId to that heading and
   continue filling/fixing it. Do NOT check the approval gate in this case — the gate only
   matters when opening a brand-new group.

B. Otherwise (every existing group is fully settled with a non-FAILED status, or there are
   no groups yet), a new group may be needed, which the gate decides. Run:
     python3 dev/tools/approve/check_gate.py ${DIR}
   - exit 0 means GATE: OK — proceed to open a new group (set opened=true). This covers a
     fresh run with no log yet, every completed group already approved, and a small backlog
     of non-risky completed groups still within this transformation's batch limit (the
     Plan's "Approval gate" section names the exact risky statuses and the limit).
   - exit 1 means GATE: BLOCKED — do not open a new group. Set gateBlocked=true, stop=true,
     and stopReason to the tool's own message (it names the blocking group and the exact
     \`approve_group.py\` command a human should run). Never run approve_group.py or edit
     approvals.toml yourself — recording approval is a human action.
   - exit 2 means a real error (a bad transformation path, or this transformation is not
     yet known to the gate's policy tables). Set stop=true and stopReason to the tool's
     stderr message — do not silently proceed as if the gate passed.

C. When you may proceed (an open group to continue, or the gate allowed a new one), pick
   this round's units by following the Plan's "Resolution" section EXACTLY, including
   whatever tool it names to rank/refresh readiness (do not guess at readiness yourself).
   Restrict to scope ${SCOPE === 'all' ? '(no restriction)' : `"${SCOPE}"`} if the Plan's
   Resolution section supports scoping; ignore the scope hint otherwise. Skip anything
   already recorded with a non-FAILED status in the log. Cap the units you return at
   ${MAXUNITS}, but report the true number of ready candidates in 'layerSize'.

D. If there is genuinely no ready unit and no open group, set units=[], stop=true, and
   stopReason explaining why (e.g. "no ready leaves this run" or "the only ready work
   depends on a file not yet translated").

Return ONLY the structured object. Do not edit any file and do not author/translate/clean
up/port anything yet.`

const triaged = await agent(triagePrompt, {
    label: 'triage',
    phase: 'Triage',
    schema: TRIAGE_SCHEMA,
    model: TRIAGE_MODEL,
})

if (!triaged || triaged.stop || !triaged.units?.length) {
    log(`Triage: ${triaged?.stopReason || 'nothing to do this round'}.`)
    return {
        transformation: TRANSFORMATION,
        triaged,
        bundled: null,
        authored: [],
        integrated: null
    }
}

// ---------------------------------------------------------------------------
// Phase 2 — Bundle: write the group + its unchecked lines before any real work starts.
// ---------------------------------------------------------------------------

phase('Bundle')

const bundlePrompt = `Record this round's work in ${LOG} before any editing starts, so the
group exists on disk even if a later step fails. ${NOTES}
Follow ${PLAN}'s log conventions exactly (heading style, one line per unit, and the
group-sizing/topic rule from its "Resolution" section${
  BUNDLESIZE ? `, capped at ${BUNDLESIZE} units for this round` : ''
}).

${
  triaged.opened
    ? `Open a NEW group heading (must start with "Group", numbered/named after the last
existing group per the Plan's convention) and add one UNCHECKED line per unit below,
grouped/ordered the way the Plan's Resolution section prescribes.`
    : `Add these units to the existing OPEN group "${triaged.groupId}" — do not open a new
heading. If a unit is already listed there, leave its line alone.`
}

Units for this round:
${triaged.units.map((u) => `  - ${u.unit}${u.verify ? ` (verify: ${u.verify})` : ''}`).join('\n')}

Return the heading text now in effect as groupId, and written=true once the log file
reflects these units.`

const bundled = await agent(bundlePrompt, {
    label: 'bundle',
    phase: 'Bundle',
    schema: BUNDLE_SCHEMA,
    model: TRIAGE_MODEL,
})
const GROUP = bundled?.groupId || triaged.groupId || '(unlabeled group)'

log(
    `${triaged.opened ? 'Opened' : 'Continuing'} ${GROUP}: ${triaged.units.length} unit(s) this round` +
    (triaged.layerSize > triaged.units.length ?
        ` (${triaged.layerSize} ready in scope "${SCOPE}" — raise maxUnits to widen)` :
        '') +
    '.'
)

// ---------------------------------------------------------------------------
// Phase 3 — Author: one agent per unit, in parallel. Each writes only its own files.
// ---------------------------------------------------------------------------

phase('Author')

const authorPrompt = (u) => `You are an AUTHOR agent for ONE unit of the "${TRANSFORMATION}"
transformation: \`${u.unit}\`. ${NOTES}

READ ${SPEC} in full and follow it exactly for this one unit — its output shape, rewrite/
cleanup rules, and any named silent traps, do-not-merge conditions, or conservative
fallback. If ${PLAN} names a per-unit scaffold/draft tool, run it first and use its hints.

Hard constraints:
- Touch ONLY this unit's own files (plus, if the Spec calls for it, moving its own obsolete
  source into a sibling deprecated/ directory). Do NOT build, run tests, or edit any
  CMakeLists.txt — even one that looks local to this unit's own directory, since another
  unit running in this same round may share it — or any shared header. The serial
  Integrate step wires every one of this round's units into the build afterward, once.
- Never invent a symbol, call, or interface the source does not already have.
- If a dependency this unit needs is not ready yet, return done="deferred" with why instead
  of guessing.

Verification handle for this unit, if any (per the Plan/Spec): ${u.verify || '(none reported — see Spec)'}
${u.notes ? `Triage notes: ${u.notes}` : ''}

Return ONE structured row. No file contents.`

const authored = await parallel(
    triaged.units.map((u) => () =>
        agent(authorPrompt(u), {
            label: `author:${u.unit}`,
            phase: 'Author',
            schema: AUTHOR_SCHEMA,
            model: AUTHOR_MODEL,
        })
    )
)
const ok = authored.filter(Boolean).filter((r) => r.done === 'yes')
const notOk = authored.filter(Boolean).filter((r) => r.done !== 'yes')
log(`Authored ${ok.length}/${triaged.units.length}.` + (notOk.length ? ` ${notOk.length} deferred/failed.` : ''))

if (!ok.length) {
    log('Nothing authored successfully; skipping integrate.')
    return {
        transformation: TRANSFORMATION,
        triaged,
        bundled,
        authored,
        integrated: null
    }
}

// ---------------------------------------------------------------------------
// Phase 4 — Integrate: one serial agent owns the shared build tree and the log.
// ---------------------------------------------------------------------------

phase('Integrate')

const integratePrompt = (units, notes) => `You are the SERIAL INTEGRATE phase for the
"${TRANSFORMATION}" transformation — you alone own the shared build tree, any shared/
top-level build files, and ${LOG} right now; no other agent is running. ${NOTES}

Units to integrate (already authored, on disk): ${units.join(', ')}
Author notes to resolve once, if any: ${notes.length ? notes.join('; ') : '(none)'}

Do, in order, following ${SPEC} and ${PLAN} exactly:
1. Wire every one of this round's units into the build — add/replace their entries in
   whichever CMakeLists.txt (local or shared) the Plan/Spec says owns them — and apply any
   other shared wiring change they need (e.g. a shared constant), once, here. Authors were
   forbidden from touching build files precisely so this step can do it without conflicts.
2. Run this step's correctness-bar command(s) exactly as ${SPEC} defines them (e.g.
   \`jobrunner submit tests/<suite>\`, a coverage/validate script, a roadmap refresh) — do
   not substitute a different check of your own.
3. Decide each unit's status using the EXACT status vocabulary ${SPEC} defines (its "Status
   meanings" / "Correctness bar" section) — never invent a status word, and never grant a
   status gated on a check the Spec requires (e.g. a coverage probe) without that check
   having actually fired. If the Spec reserves a status for a human to grant (a runner may
   never assign it), use the runner-appropriate status instead and say in notes what a
   human still needs to confirm.
4. Update ${LOG}: check off each unit's line with its status, in the exact line format
   ${PLAN} prescribes. Never call approve_group.py or edit approvals.toml yourself —
   recording approval is a human action.
5. Leave the tree building clean whether or not every unit passed.

Return the compact status table only (one row per unit). Set groupClosed=true only if
EVERY unit currently listed under group "${GROUP}" in ${LOG} (not just this round's units)
now has a non-FAILED status.`

let integrated = await agent(
    integratePrompt(
        ok.map((r) => r.unit),
        authored.map((r) => r?.notes).filter(Boolean)
    ), {
        label: 'integrate',
        phase: 'Integrate',
        schema: INTEGRATE_SCHEMA,
        model: INTEGRATE_MODEL
    }
)

// ---------------------------------------------------------------------------
// Phase 5 — Fix: escalate FAILED units to a stronger model, then integrate again.
// ---------------------------------------------------------------------------

for (let round = 1; round <= FIXROUNDS; round++) {
    const failedRows = (integrated?.rows || []).filter((r) => r.status === 'FAILED')
    if (!failedRows.length) break

    phase('Fix')
    log(`Fix round ${round}/${FIXROUNDS}: escalating ${failedRows.length} FAILED unit(s) to ${FIX_MODEL}.`)

    const fixPrompt = (r) => `Repair the FAILED "${TRANSFORMATION}" unit \`${r.unit}\`. ${NOTES}
Integrate's symptom: ${r.notes || "(diagnose from source and the Spec's silent-traps / conservative-fallback guidance)"}.

READ ${SPEC} first; compare against a verified sibling unit. Edit ONLY this unit's own
outputs — do NOT build, run tests, or touch any CMakeLists.txt (re-integrate does that,
since another unit being fixed in this same round may share the file). If it truly cannot
be fixed without a dependency that is not ready, return done="deferred" with why instead of
guessing.

Return ONE row: unit | done(yes/deferred/failed) | notes (what changed and why).`

    const repaired = (
        await parallel(
            failedRows.map((r) => () =>
                agent(fixPrompt(r), {
                    label: `fix:${r.unit}`,
                    phase: 'Fix',
                    schema: AUTHOR_SCHEMA,
                    model: FIX_MODEL
                })
            )
        )
    ).filter(Boolean)

    const refixUnits = repaired.filter((r) => r.done === 'yes').map((r) => r.unit)
    if (!refixUnits.length) {
        log('Fix produced no repaired units; ending escalation.')
        break
    }

    const reInt = await agent(integratePrompt(refixUnits, []), {
        label: `re-integrate:r${round}`,
        phase: 'Integrate',
        schema: INTEGRATE_SCHEMA,
        model: INTEGRATE_MODEL,
    })

    const byUnit = new Map((integrated?.rows || []).map((r) => [r.unit, r]))
    for (const r of reInt?.rows || []) byUnit.set(r.unit, r)
    integrated = {
        verifyOk: reInt?.verifyOk ?? integrated?.verifyOk,
        rows: [...byUnit.values()],
        groupClosed: reInt?.groupClosed ?? integrated?.groupClosed,
    }
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

const rows = integrated?.rows || []
const failed = rows.filter((r) => r.status === 'FAILED')
const settled = rows.filter((r) => r.status !== 'FAILED')

log(
    `Round complete: ${settled.length} settled, ${failed.length} FAILED in ${GROUP}. ` +
    (integrated?.groupClosed ?
        `Group is complete — needs human approval (approve_group.py) before the next group can open.` :
        'Group still open — the next run continues it.')
)

return {
    transformation: TRANSFORMATION,
    scope: SCOPE,
    group: GROUP,
    triaged,
    bundled,
    authored,
    integrated,
}