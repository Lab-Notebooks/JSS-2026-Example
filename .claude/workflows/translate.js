// Workflow: translate — parallel-author, serial-integrate over a discovered worklist.
//
// A Claude Code orchestrator for a transformation whose unit of work is a single
// source file with a dependency graph over the units. It is transformation-agnostic:
// the transformation directory is the only required input, and every concrete step
// (which discovery tool to run, how to author a unit, and the verification criteria)
// is read from that transformation's Spec (desired_spec.md). The workflow supplies
// the structure; the Spec supplies the commands. Invoke it as
//   "Run translate for dev/transformations/<transformation>".
//
// The pipeline is six phases; the structural lessons worth study are the parallel
// author / serial integrate split and the human review checklist:
//   Index      deterministic — run the Spec's discovery tools to rank units by readiness
//   Resolve    deterministic — pick the next leaf layer (units with no unconverted deps)
//   Bundle     group the ready layer into review-sized bundles; record them in the Plan
//   Author     PARALLEL, and SIZE-GATED: a large unit goes to a stronger model
//   Integrate  SERIAL — one agent owns the build and is the verification trust anchor
//   Fix        escalate FAILED units to a stronger model, then re-integrate
//
// Config (args): projectRoot (required, absolute), transformation (required — a dir
//                under dev/transformations/), scope (a subtree filter, default 'all'),
//                maxUnits (cap one run, 12), bigLoc (model gate, 400),
//                bundleSize (units per human-review bundle, 5).

export const meta = {
  name: 'translate',
  description: 'Translate one dependency-graph leaf layer of a transformation: discover the ready units, bundle them into human-review units, author in parallel, then build and verify serially. Transformation-agnostic — driven entirely by the Spec it is pointed at.',
  whenToUse: 'Run translate for dev/transformations/<transformation>. args:{projectRoot, transformation, scope}. Resolves the next conflict-free leaf layer, records review bundles in the Plan, and translates it end-to-end.',
  phases: [
    { title: 'Index',     model: 'haiku'  },
    { title: 'Resolve',   model: 'haiku'  },
    { title: 'Bundle',    model: 'haiku'  },
    { title: 'Author',    model: 'sonnet' },
    { title: 'Integrate', model: 'opus'   },
    { title: 'Fix',       model: 'opus'   },
  ],
}

const cfg = typeof args === 'string' ? JSON.parse(args) : (args || {})
const PROJECT = cfg.projectRoot
if (!PROJECT) throw new Error('args.projectRoot (absolute path to the lab-notebook root) is required')
const SCOPE      = cfg.scope      || 'all'
const MAXUNITS   = cfg.maxUnits   || 12
const BIGLOC     = cfg.bigLoc     ?? 400
const BUNDLESIZE = cfg.bundleSize ?? 5

// The transformation is the only binding to a concrete task. Accept either a bare
// name or a full 'dev/transformations/<name>' directory; there is no default, so the
// workflow never assumes a particular transformation.
const TRANSFORMATION = (cfg.transformation || '').replace(/^dev\/transformations\//, '').replace(/\/$/, '')
if (!TRANSFORMATION) throw new Error('args.transformation (a dir under dev/transformations/) is required')
const SPEC = `dev/transformations/${TRANSFORMATION}/desired_spec.md`
const PLAN = `dev/transformations/${TRANSFORMATION}/current_plan.md`
const ENV  = `source ${PROJECT}/environment.sh`   // Bash resets env between calls; prefix env-dependent commands

const RESOLVE_SCHEMA = {
  type: 'object',
  properties: {
    ready: { type: 'array', items: { type: 'object', properties: {
      unit:   { type: 'string', description: 'path or id of the unit to convert, per the Spec' },
      group:  { type: 'string', description: 'the group the unit belongs to (e.g. its directory) — used for bundling and to choose its verification' },
      verify: { type: 'string', description: 'the verification handle for this unit per the Spec, or "" if none applies' },
      size:   { type: 'integer', description: 'size metric (e.g. line count) that drives the big-unit model gate' },
    }, required: ['unit', 'group', 'verify'] } },
    layerSize: { type: 'integer', description: 'total ready leaves before the maxUnits cap' },
  },
  required: ['ready', 'layerSize'],
}
const BUNDLE_SCHEMA = {
  type: 'object',
  properties: {
    bundles: { type: 'array', items: { type: 'object', properties: {
      id:     { type: 'string', description: 'short label, e.g. the shared group + index' },
      group:  { type: 'string' },
      verify: { type: 'string' },
      units:  { type: 'array', items: { type: 'string' } },
    }, required: ['id', 'units'] } },
  },
  required: ['bundles'],
}
const AUTHOR_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' },
    authored: { type: 'string', enum: ['yes', 'deferred', 'failed'] },
    notes: { type: 'string', description: 'missing shared symbol, deferral reason, or suspected mistranslation' },
  },
  required: ['unit', 'authored'],
}
const INTEGRATE_SCHEMA = {
  type: 'object',
  properties: {
    buildOk: { type: 'boolean' },
    rows: { type: 'array', items: { type: 'object', properties: {
      unit: { type: 'string' },
      status: { type: 'string', enum: ['VERIFIED', 'TRANSLATED', 'FAILED'] },
      probe: { type: 'string', description: 'the exercise/coverage-check result the Spec requires: exercised / unchanged / n-a' },
      escalated: { type: 'boolean', description: 'true if this unit needs human adjudication' },
      notes: { type: 'string' },
    }, required: ['unit', 'status'] } },
  },
  required: ['buildOk', 'rows'],
}

// Index — run the transformation's discovery tools to rank units by readiness.
// Deterministic: the Spec names these tools; they are run, not reasoned about.
phase('Index')
await agent(
  `Run the discovery/index step exactly as ${PROJECT}/${SPEC} describes it: its deterministic tools that build
the dependency graph and rank units by translation readiness (a leaf is a unit whose every dependency is
already converted). Work from ${PROJECT}; prefix env-dependent commands with \`${ENV} &&\`. Report the counts
the tools print (units total / converted / remaining, ready leaves). Do not author or convert anything.`,
  { label: 'index', phase: 'Index', effort: 'low' }
)

// Resolve — pick this run's leaf layer from the readiness ranking the Index produced.
phase('Resolve')
const resolved = await agent(
  `Read the readiness ranking the Index step produced (the Spec names where it is written) and pick the READY
leaf layer: units with no unconverted dependency${SCOPE === 'all' ? ' (any group)' : `, restricted to group "${SCOPE}"`}.
Skip any unit already converted. For each kept unit record its id/path, its group, its verification handle
(per the Spec, or ""), and a size metric (e.g. \`wc -l\`). Cap 'ready' to ${MAXUNITS} units but report the true
total in 'layerSize'. Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. Return only the structured object.`,
  { label: 'resolve', phase: 'Resolve', schema: RESOLVE_SCHEMA }
)
if (!resolved?.ready?.length) {
  log('Resolve found no ready units. Nothing to translate this run.')
  return { resolved, bundles: null, authored: [], integrated: null }
}
log(`Layer: ${resolved.layerSize} ready leaf(s) in "${SCOPE}"; taking ${resolved.ready.length} this run.`)

// Bundle — group the ready layer into review-sized units and record them in the Plan.
// This is the human-facing output of the run: a reviewer accepts one coherent bundle at
// a time, so bundling balances throughput (fewer, larger bundles) against the reviewer's
// technical debt (smaller, coherent bundles). The Plan is the durable record; dev/tmp is not.
phase('Bundle')
const bundled = await agent(
  `Group these ${resolved.ready.length} ready units into review-sized bundles for a human reviewer, balancing
throughput against reviewer technical debt: keep each bundle coherent (same group and same verification handle
so it can be accepted as a unit), and cap each at ${BUNDLESIZE} units. Then refresh the "## Review bundles"
section of ${PROJECT}/${PLAN}: one "### <id> — <group> (<k> units, verify: <handle>)" heading per bundle with
a "- [ ] <unit>" line per unit (leave any existing recorded outcomes intact). Work from ${PROJECT}; prefix env
commands with \`${ENV} &&\`. Units (id · group · verify · size):
${resolved.ready.map((u) => `  ${u.unit} · ${u.group} · ${u.verify || '-'} · ${u.size || '?'}`).join('\n')}
Return the bundles you wrote.`,
  { label: 'bundle', phase: 'Bundle', schema: BUNDLE_SCHEMA }
)
log(`Recorded ${bundled?.bundles?.length ?? 0} review bundle(s) in ${PLAN}.`)

// Author — one agent per unit, in parallel. Each writes ONLY its own outputs.
// Size-gate: a large unit is escalated to a stronger model instead of being chunked.
phase('Author')
const authorPrompt = (u) => `Convert one unit of this transformation: \`${u.unit}\` (group ${u.group}).
Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC} and follow it end to end,
including any draft/scaffold pre-pass tool the Spec names (run it first for its hints) and its rules for never
fabricating a called symbol. Write only this unit's own outputs. Do NOT build, edit shared build files, or
touch shared headers — the serial integrator does that. If a dependency is not yet converted, set
authored="deferred"; if a shared symbol is missing, note it. Return one structured row.`

const authored = await parallel(resolved.ready.map((u) => () =>
  agent(authorPrompt(u), {
    label: `author:${u.unit}`, phase: 'Author', schema: AUTHOR_SCHEMA,
    model: (u.size || 0) > BIGLOC ? 'opus' : 'sonnet',   // size-gate
  })
))
const ok = authored.filter((r) => r?.authored === 'yes')
log(`Authored ${ok.length}/${resolved.ready.length}.`)
if (!ok.length) return { resolved, bundles: bundled?.bundles ?? null, authored, integrated: null }

// Integrate — ONE serial agent owns the build and applies the verification criteria.
// This concentrates the correctness check in a single place: the trust anchor.
const verifyFor = (units) => [...new Set(resolved.ready.filter((u) => units.includes(u.unit) && u.verify).map((u) => u.verify))]
const integratePrompt = (units, verify, notes) => `You are the SERIAL integrator — you alone own the build tree
and shared build files. Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. Apply the verification
criteria in ${PROJECT}/${SPEC} exactly — never grant VERIFIED without the Spec's exercise/coverage check firing.

Units to integrate: ${units.join(', ')}
Verification handles to run: ${verify.length ? verify.join(', ') : '(none — infrastructure, mark TRANSLATED)'}
Author notes to resolve once: ${notes.length ? notes.join('; ') : '(none)'}

Wire each unit into the build, build once, run its verification handle, then run the Spec's mandatory
exercise/coverage check. VERIFIED only when that check confirms the unit was exercised; a unit off the
check's path is TRANSLATED (unverified). If a unit looks mistranslated, mark it FAILED with the symptom and
escalated=true rather than guessing. Leave the tree building clean. Return the status table only.`

let integrated = await agent(
  integratePrompt(ok.map((r) => r.unit), verifyFor(ok.map((r) => r.unit)), authored.map((r) => r?.notes).filter(Boolean)),
  { label: 'integrate', phase: 'Integrate', schema: INTEGRATE_SCHEMA }
)

// Fix — bounded escalation: re-author FAILED units with a stronger model, re-integrate once.
// Failures that survive are surfaced for a human, not retried indefinitely.
const failed = (integrated?.rows || []).filter((r) => r.status === 'FAILED')
if (failed.length) {
  phase('Fix')
  log(`Escalating ${failed.length} FAILED unit(s) to a stronger model.`)
  const repaired = (await parallel(failed.map((r) => () =>
    agent(`Repair the FAILED conversion of \`${r.unit}\`. Symptom: ${r.notes || '(diagnose from source)'}.
Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC} (its rules and silent
traps) and compare against a verified sibling. Edit only this unit's outputs; do NOT build or edit shared
build files (re-integrate does that). Return one row.`,
      { label: `fix:${r.unit}`, phase: 'Fix', schema: AUTHOR_SCHEMA, model: 'opus' })
  ))).filter((r) => r?.authored === 'yes').map((r) => r.unit)

  if (repaired.length) {
    const reInt = await agent(integratePrompt(repaired, verifyFor(repaired), []),
      { label: 're-integrate', phase: 'Integrate', schema: INTEGRATE_SCHEMA })
    const byUnit = new Map((integrated?.rows || []).map((r) => [r.unit, r]))
    for (const r of (reInt?.rows || [])) byUnit.set(r.unit, r)
    integrated = { buildOk: reInt?.buildOk ?? integrated?.buildOk, rows: [...byUnit.values()] }
  }
}

const by = (s) => (integrated?.rows || []).filter((r) => r.status === s)
log(`Run complete: ${by('VERIFIED').length} verified, ${by('TRANSLATED').length} translated, ${by('FAILED').length} failed. Record outcomes in ${PLAN}.`)
return {
  scope: SCOPE,
  layerSize: resolved.layerSize,
  bundles: bundled?.bundles ?? null,
  authored,
  integrated,
  toRecord: { verified: by('VERIFIED'), translated: by('TRANSLATED'), failed: by('FAILED') },
}
