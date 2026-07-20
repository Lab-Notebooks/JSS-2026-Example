// Workflow: port — turn everything a target calls into one self-contained piece of code.
//
// A small driver for a step where the unit of work is not one file but the whole tree of
// things a target calls, rewritten into one self-contained output (nothing calls out of
// it). It only sets up the structure (the phases below, the small-vs-big branch, doing
// levels in order, and what to do on a failure). All the real rules and commands (which
// target to do, small vs. big, the closure tool, the first-draft tool, the reference to
// check against, the compare harness, and the final test) live in that step's Spec
// (especially its "Resolution" section). It works for any step; the only required input
// is the step's folder. Start it with:
//   "Run port for dev/transformations/<step>".
//
// The main idea is the SIZE CHECK: a quick Triage counts how big the tree is, and the
// workflow picks a path —
//   small tree  → Direct: one agent rewrites + checks + assembles in a single pass.
//   large tree  → Split: break it into pieces (each with its own reference), do them
//                 bottom-up level by level, then Assemble them one at a time.
// Both paths end at the same loop and final test:
//   … → Validate (the `validate` loop) → Test (the Spec's correctness check).
//
// With no target given, a Select phase reads an earlier step's Plan (args.from) and does
// the files a person already approved there whose call tree is now fully rewritten.
//
// Config (args): projectRoot (required), transformation (required — a folder under
//                dev/transformations/), target OR targets:[...] (a batch, in order of
//                need; leave both out to auto-pick from an earlier Plan), from (the
//                earlier step's folder, only needed for auto-pick),
//                directMax (small-vs-big cutoff, 30), tol (1e-10), maxFixes (6).

export const meta = {
  name: 'port',
  description: 'Port the call-tree closure of a target into one self-contained artifact. Size-gated: small trees go direct through one agent; large ones split into oracle-validated pieces, then assemble, validate, and test. Transformation-agnostic — driven by the Spec it is pointed at. Auto-selects from a predecessor Plan when no target is given.',
  whenToUse: 'Run port for dev/transformations/<transformation>. args:{projectRoot, transformation, target:"..."} for one, {targets:[...]} for a batch, or omit both with {from:"<predecessor>"} to port that stage\'s human-approved units.',
  phases: [
    { title: 'Select',      detail: 'no target given: pick human-approved units from a predecessor Plan', model: 'sonnet' },
    { title: 'Triage',      detail: 'closure-object count; pick direct vs split', model: 'sonnet' },
    { title: 'Direct port', detail: 'small tree: one agent ports + validates + assembles', model: 'opus' },
    { title: 'Split',       detail: 'large tree: coarse oracle-validated piece DAG', model: 'opus' },
    { title: 'Author',      detail: 'one agent per piece, bottom-up; freeze at tolerance', model: 'sonnet' },
    { title: 'Assemble',    detail: 'params + artifact + dispatch (serial)', model: 'opus' },
    { title: 'Validate',    detail: 'nested full-target validate↔fix loop vs the oracle' },
    { title: 'Test',        detail: 'the Spec\'s final verification criteria', model: 'opus' },
  ],
}

const cfg = typeof args === 'string' ? JSON.parse(args) : (args || {})
const PROJECT = cfg.projectRoot
if (!PROJECT) throw new Error('args.projectRoot (absolute path to the lab-notebook root) is required')
const REQUESTED  = cfg.targets?.length ? cfg.targets : (cfg.target ? [cfg.target] : [])
const DIRECT_MAX = cfg.directMax ?? 30
const TOL        = cfg.tol       || 1e-10
const MAXFIXES   = cfg.maxFixes  ?? 6

// The transformation is the only binding to a concrete task; there is no default.
const TRANSFORMATION = (cfg.transformation || '').replace(/^dev\/transformations\//, '').replace(/\/$/, '')
if (!TRANSFORMATION) throw new Error('args.transformation (a dir under dev/transformations/) is required')
// The predecessor stage (for auto-select) is also a parameter, never assumed.
const FROM = (cfg.from || '').replace(/^dev\/transformations\//, '').replace(/\/$/, '')
const SPEC = `dev/transformations/${TRANSFORMATION}/desired_spec.md`
const PLAN = `dev/transformations/${TRANSFORMATION}/current_plan.md`
const FROM_PLAN = FROM ? `dev/transformations/${FROM}/current_plan.md` : null
const ENV  = `source ${PROJECT}/environment.sh`

const TRIAGE_SCHEMA = {
  type: 'object',
  properties: {
    objects:      { type: 'integer', description: 'closure object count from the Spec\'s closure tool' },
    ready:        { type: 'boolean', description: 'true if every closure object was produced by the predecessor stage (ready to port)' },
    artifactName: { type: 'string', description: 'name of the single output artifact to produce, per the Spec' },
    entry:        { type: 'string', description: 'entry source of the target, per the Spec' },
    oracle:       { type: 'string', description: 'the reference symbol/oracle the Spec names for the whole target' },
  },
  required: ['objects', 'artifactName', 'entry', 'oracle'],
}
const PIECE_SCHEMA = {
  type: 'object',
  properties: {
    piece: { type: 'string' },
    authored: { type: 'string', enum: ['yes', 'failed'] },
    level: { type: 'integer' },
    globals: { type: 'array', items: { type: 'string' }, description: 'globals the piece needs → Params fields' },
    notes: { type: 'string' },
  },
  required: ['piece', 'authored'],
}
const SPLIT_SCHEMA = {
  type: 'object',
  properties: {
    artifactName: { type: 'string' },
    pieces: { type: 'array', items: {
      type: 'object',
      properties: {
        id: { type: 'string' }, level: { type: 'integer', description: '0 = leaf' },
        sources: { type: 'array', items: { type: 'string' } },
        oracle: { type: 'string', description: 'the oracle symbol to validate this piece against, per the Spec' },
      }, required: ['id', 'level', 'oracle'],
    } },
    blockers: { type: 'array', items: { type: 'string' } },
  },
  required: ['artifactName', 'pieces'],
}
const WRITTEN_SCHEMA = {
  type: 'object',
  properties: { written: { type: 'boolean' }, worstRelErr: { type: 'string' }, notes: { type: 'string' } },
  required: ['written'],
}
const TEST_SCHEMA = {
  type: 'object',
  properties: { status: { type: 'string', enum: ['PASSED', 'FAILED'] }, notes: { type: 'string' } },
  required: ['status'],
}
const SELECT_SCHEMA = {
  type: 'object',
  properties: {
    targets: { type: 'array', items: { type: 'string' },
      description: 'targets to port, in dependency order (a prerequisite before what depends on it)' },
    skipped: { type: 'array', items: { type: 'object', properties: {
      target: { type: 'string' },
      reason: { type: 'string', description: 'already ported / not yet verified in the predecessor stage / closure not all-ready' },
    }, required: ['target', 'reason'] } },
  },
  required: ['targets'],
}

async function portOne(TARGET) {
  // Triage — a quick size check (just count the tree, not a full review).
  phase('Triage')
  const tri = await agent(
    `Size the "${TARGET}" call tree to pick direct vs split — a cheap pass, not a full audit.
Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. Run the closure tool the Spec names
(${PROJECT}/${SPEC}) over the target and read its footer: the object count → 'objects', and whether every
object was produced by the predecessor stage → 'ready'. Find the entry source of the target → 'entry' and the
reference oracle the Spec names for the whole target → 'oracle'; derive 'artifactName' per the Spec. Return
only the structured object.`,
    { label: 'triage', phase: 'Triage', schema: TRIAGE_SCHEMA, effort: 'low' }
  )
  if (!tri || typeof tri.objects !== 'number') return { status: 'FAILED', stage: 'triage', target: TARGET }
  if (tri.ready === false) {
    log('Triage: closure has objects not yet produced by the predecessor stage → finish those first.')
    return { status: 'BLOCKED', stage: 'triage', target: TARGET }
  }

  const NAME = tri.artifactName || TARGET
  const direct = tri.objects <= DIRECT_MAX
  log(`Triage: ${tri.objects} objects → ${direct ? `DIRECT (≤ ${DIRECT_MAX})` : `SPLIT (> ${DIRECT_MAX})`}.`)

  if (direct) {
    // Direct — one agent rewrites the whole small tree, checks it, and assembles the output.
    phase('Direct port')
    const d = await agent(
      `Port the SMALL target "${NAME}" (${tri.objects} objects) — the whole call tree — into one artifact, in
one pass. Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC} and follow its
authoring rules. Write the single output artifact the Spec specifies (helpers, the pure entry, the dispatch
wrapper) plus its provenance line. Validate the whole target against oracle ${tri.oracle} using the validation
harness the Spec names; iterate to ≤ ${TOL}. Do NOT wire the build or the final test (the Test phase does).
Return written + worstRelErr.`,
      { label: `direct:${NAME}`, phase: 'Direct port', schema: WRITTEN_SCHEMA }
    )
    if (!d?.written) return { status: 'FAILED', stage: 'direct', target: TARGET }
    log(`Direct port wrote artifact ${NAME} (self-validated ${d.worstRelErr || 'n/a'}).`)
  } else {
    // Split — break the tree into pieces; each piece has its own reference, so it can be
    // written and frozen on its own, bottom-up, then assembled one at a time.
    phase('Split')
    const plan = await agent(
      `Split the "${TARGET}" call tree into the FEWEST author-sized pieces that each still have an oracle (not
one piece per function). Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC}
(its splitting rules). Cross-check completeness with the closure tool the Spec names. For each piece record id,
DAG level (0 = leaf), its predecessor-stage sources, and the oracle symbol. List any blocker (a callee the
predecessor stage has not produced). Return the structured object.`,
      { label: 'split', phase: 'Split', schema: SPLIT_SCHEMA }
    )
    if (!plan?.pieces?.length) return { status: 'FAILED', stage: 'split', target: TARGET }
    if (plan.blockers?.length) {
      log(`Blockers must be cleared first: ${plan.blockers.join('; ')}`)
      return { status: 'BLOCKED', stage: 'split', target: TARGET, plan }
    }

    // Do each level in parallel; the order matters — a piece at level N includes the
    // frozen pieces from lower levels. If a piece fails, stop before the ones that depend
    // on it get built on top of a broken piece.
    const done = new Map()
    const maxLevel = Math.max(...plan.pieces.map((p) => p.level))
    for (let L = 0; L <= maxLevel; L++) {
      const level = plan.pieces.filter((p) => p.level === L)
      if (!level.length) continue
      log(`Author level ${L}/${maxLevel}: ${level.map((p) => p.id).join(', ')}`)
      const rows = await parallel(level.map((p) => () =>
        agent(
          `Author fragment "${p.id}" of "${NAME}". Work from ${PROJECT}; prefix env commands with
\`${ENV} &&\`. READ ${PROJECT}/${SPEC} (its authoring rules). Predecessor-stage sources: ${p.sources?.join(', ') || '(see plan)'}.
Run the authoring pre-pass tool the Spec names over each source and resolve every TODO it flags. Write one
frozen fragment per the Spec's fragment convention (its provenance line included; frozen deps included, never
edited). Validate the fragment in isolation against oracle ${p.oracle} to ≤ ${TOL}. Write only your fragment;
a piece that cannot meet tolerance returns authored="failed" with the symptom.`,
          { label: `author:${p.id}`, phase: 'Author', schema: PIECE_SCHEMA })
      ))
      rows.filter(Boolean).forEach((r) => done.set(r.piece, r))
      const stuck = level.filter((p) => done.get(p.id)?.authored !== 'yes')
      if (stuck.length) {
        log(`Level ${L} has unfixable piece(s): ${stuck.map((p) => p.id).join(', ')} — aborting.`)
        return { status: 'FAILED', stage: 'author', target: TARGET, plan }
      }
    }

    // Assemble — one agent, on its own, owns the shared output files.
    phase('Assemble')
    const globals = [...new Set([...done.values()].flatMap((r) => r.globals || []))]
    const asm = await agent(
      `Serial ASSEMBLE of "${NAME}" — you alone own the shared artifact files. Work from ${PROJECT}; prefix env
commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC} (its assembly rules). The frozen fragments are already on
disk. Globals reported by the pieces (→ Params fields): ${globals.join(', ') || '(none)'}. Write the single
output artifact the Spec specifies (include the fragments, the POD Params struct, the pure entry, the dispatch
wrapper) with its provenance line. Smoke-compile it. Fragments are frozen — if one cannot compile, report it in
notes instead of editing it. Do NOT wire the build or run the validation loop. Return written.`,
      { label: 'assemble', phase: 'Assemble', schema: WRITTEN_SCHEMA }
    )
    if (!asm?.written) return { status: 'FAILED', stage: 'assemble', target: TARGET, plan }
  }

  // Validate — the shared loop (both paths use it). If the pieces pass but the whole
  // target doesn't match, the bug is in how they were joined.
  phase('Validate')
  const val = await workflow('validate', { target: NAME, projectRoot: PROJECT, transformation: TRANSFORMATION, maxFixes: MAXFIXES, tol: TOL })
  if (val?.status !== 'PASSED') {
    log(`Full-target validation did not converge (${val?.reason || 'no result'}).`)
    return { status: 'FAILED', stage: 'validate', target: TARGET, validation: val }
  }
  log(`Artifact matches the oracle (maxRelErr=${val.maxRelErr}, fixes=${val.fixes}).`)

  // Test — the Spec's final correctness check.
  phase('Test')
  const test = await agent(
    `The "${NAME}" artifact now matches the oracle (maxRelErr=${val.maxRelErr}). Finish per the Spec's final
verification criteria. Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC}:
add the layered tests it prescribes (mirroring the existing cases), register the artifact in the build, then
build and run the Spec's test target for this artifact and re-run the pre-existing cases to prove no
regression. Return PASSED only if the new tests and the pre-existing cases all pass.`,
    { label: 'test', phase: 'Test', schema: TEST_SCHEMA }
  )
  const status = test?.status === 'PASSED' ? 'VERIFIED' : 'FAILED'
  log(`Run complete: ${status} — path=${direct ? 'direct' : 'split'}, full target at ${val.maxRelErr}. Record the outcome in ${PLAN}.`)
  return { status, target: TARGET, artifactName: NAME, path: direct ? 'direct' : 'split', validation: val, test }
}

// Select — when no target was named, do what the earlier step already finished and a
// person approved. Read the earlier Plan for files tagged VERIFIED, then confirm each
// one's call tree is fully rewritten.
async function selectFromPredecessor() {
  if (!FROM_PLAN) {
    log('No target given and no args.from predecessor set — nothing to select.')
    return []
  }
  phase('Select')
  log(`No target given; selecting human-approved units from ${FROM_PLAN}.`)
  const sel = await agent(
    `Select the targets to port per ${PROJECT}/${SPEC} "Resolution" (selection), reading the predecessor Plan
${PROJECT}/${FROM_PLAN} and dropping any already ported (see ${PROJECT}/${PLAN}). Work from ${PROJECT}; prefix
env commands with \`${ENV} &&\`. Return 'targets' in dependency order and 'skipped' with a one-line reason each.`,
    { label: 'select', phase: 'Select', schema: SELECT_SCHEMA }
  )
  if (sel?.skipped?.length) log(`Skipped: ${sel.skipped.map((s) => `${s.target} (${s.reason})`).join('; ')}`)
  return sel?.targets || []
}

// Driver — if a target was given, use it as-is; otherwise Select builds the list from
// the earlier Plan named by args.from.
const TARGETS = REQUESTED.length ? REQUESTED : await selectFromPredecessor()
if (!TARGETS.length) {
  log('Nothing to port: no target given and no human-approved predecessor unit is ready.')
  return { batch: true, targets: [], verified: 0, results: [] }
}
if (TARGETS.length === 1) return await portOne(TARGETS[0])

log(`Batch: ${TARGETS.length} target(s), sequential — ${TARGETS.join(', ')}.`)
const results = []
for (const t of TARGETS) {
  log(`── ${t} ──`)
  const r = await portOne(t)
  results.push(r)
  if (r?.status !== 'VERIFIED') log(`WARNING: ${t} ended ${r?.status || 'no-result'} — later reuses may fail.`)
}
const nVerified = results.filter((r) => r?.status === 'VERIFIED').length
log(`Batch complete: ${nVerified}/${results.length} verified.`)
return { batch: true, targets: TARGETS, verified: nVerified, results }
