// Workflow: translate — write files in parallel, then combine them one at a time.
//
// A small driver for a step whose unit of work is one source file, where some files
// depend on others. It only sets up the structure (the phases below, what runs in
// parallel vs. one at a time, and what to do on a failure). All the real rules and
// commands (which tools to run, which files are ready, how to group them, how to
// rewrite, and how to check the result) live in that step's Spec (desired_spec.md,
// especially its "Resolution" section). It works for any step; the only required input
// is the step's folder. Start it with:
//   "Run translate for dev/transformations/<step>".
//
// Six phases. The two ideas worth noticing are "write in parallel, combine one at a
// time" and the review list for a person:
//   Index      run the Spec's tools to rank files by how ready they are (no AI guessing)
//   Resolve    pick the next batch of ready files, following the Spec's Resolution rule
//   Bundle     group them into review-sized batches; write them in the Plan
//   Author     IN PARALLEL, one file each; a big file gets a stronger model
//   Integrate  ONE AT A TIME: one agent owns the build and runs the check
//   Fix        a failed file goes to a stronger model, then gets combined again
//
// Config (args): projectRoot (required, absolute), transformation (required — a folder
//                under dev/transformations/), scope (limit to a subfolder, default 'all'),
//                maxUnits (files per run, 12), bigLoc (big-file cutoff, 400),
//                bundleSize (files per review batch, 5).

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

// Index — run the Spec's tools to rank files by how ready they are.
// These are plain programs named by the Spec; run them, don't work the ranking out by hand.
phase('Index')
await agent(
  `Run the discovery/index step exactly as ${PROJECT}/${SPEC} describes it: its deterministic tools that build
the dependency graph and rank units by translation readiness (a leaf is a unit whose every dependency is
already converted). Work from ${PROJECT}; prefix env-dependent commands with \`${ENV} &&\`. Report the counts
the tools print (units total / converted / remaining, ready leaves). Do not author or convert anything.`,
  { label: 'index', phase: 'Index', effort: 'low' }
)

// Resolve — pick this run's batch of ready files. The rule (which files are ready, what
// to skip, what order) lives in the Spec's "Resolution" section, not here.
phase('Resolve')
const resolved = await agent(
  `Follow ${PROJECT}/${SPEC} "Resolution" to pick the READY leaf layer${SCOPE === 'all' ? '' : `, restricted to group "${SCOPE}"`}.
Fill the schema for each kept unit (id/path, group, verification handle, size metric). Cap 'ready' to
${MAXUNITS} units but report the true total in 'layerSize'. Work from ${PROJECT}; prefix env commands with
\`${ENV} &&\`. Return only the structured object.`,
  { label: 'resolve', phase: 'Resolve', schema: RESOLVE_SCHEMA }
)
if (!resolved?.ready?.length) {
  log('Resolve found no ready units. Nothing to translate this run.')
  return { resolved, bundles: null, authored: [], integrated: null }
}
log(`Layer: ${resolved.layerSize} ready leaf(s) in "${SCOPE}"; taking ${resolved.ready.length} this run.`)

// Bundle — group the ready files into review-sized batches and write them in the Plan.
// The grouping rule and the Plan's "Review bundles" format both live in the Spec/Plan.
phase('Bundle')
const bundled = await agent(
  `Bundle these ${resolved.ready.length} ready units per ${PROJECT}/${SPEC} "Resolution" (review-sized,
coherent, cap ${BUNDLESIZE}), then refresh the "## Review bundles" section of ${PROJECT}/${PLAN} in the format
that Plan prescribes, preserving any recorded outcomes. Work from ${PROJECT}; prefix env commands with
\`${ENV} &&\`. Units (id · group · verify · size):
${resolved.ready.map((u) => `  ${u.unit} · ${u.group} · ${u.verify || '-'} · ${u.size || '?'}`).join('\n')}
Return the bundles you wrote.`,
  { label: 'bundle', phase: 'Bundle', schema: BUNDLE_SCHEMA }
)
log(`Recorded ${bundled?.bundles?.length ?? 0} review bundle(s) in ${PLAN}.`)

// Author — one agent per file, all at once. Each writes only its own files.
// A big file goes to a stronger model instead of being split up.
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

// Integrate — one agent, on its own, owns the build and runs the check.
// Keeping the check in one place is what makes the result trustworthy.
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

// Fix — try each failed file once more with a stronger model, then combine again.
// Anything still failing goes to a person instead of being retried forever.
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
