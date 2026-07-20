// Workflow: validate — the oracle validate↔fix loop.
//
// This is the Loop primitive in its minimal form: a deterministic validate↔fix cycle
// whose only cross-iteration state lives on disk. It validates a produced artifact
// against the reference oracle the Spec names, and alternates diagnose-and-fix with
// re-validate until every check passes or no further progress is possible. The `port`
// workflow calls it as its verification criteria; it also runs standalone once an
// artifact exists and needs to be made equivalent.
//
// It is transformation-agnostic: the transformation directory is a required argument
// and the Spec is read from there, so any transformation whose Spec defines a per-block
// oracle and a validation harness can drive the same loop.
//
// The only cross-step scratch is the check table dev/tmp/assets/validate-output.md: the
// validate step writes it (ref/got/relErr per check) and the fix step reads it. It is
// transient and regenerated each cycle. Durable notes (what was changed, the per-target
// outcome) belong in the transformation's Plan, not in scratch.
//
// Config (args): target (required), projectRoot (required), transformation (required —
//                a dir under dev/transformations/), maxFixes (6), tol (1e-10).

export const meta = {
  name: 'validate',
  description: 'Validate a produced artifact against the oracle its Spec names, and loop diagnose → fix → re-validate until equivalent or stuck. A transformation-agnostic verification Loop.',
  whenToUse: 'args:{target, projectRoot, transformation, maxFixes, tol}. Requires the artifact to already exist where the Spec places it.',
  phases: [
    { title: 'Validate', detail: 'build + run the artifact-vs-oracle comparison the Spec names' },
    { title: 'Fix',      detail: 'diagnose the mismatch, edit the artifact' },
  ],
}

const cfg = typeof args === 'string' ? JSON.parse(args) : (args || {})
// Accept `target` (preferred) or `amplitude` (alias) for the thing under validation.
const target      = cfg.target || cfg.amplitude
const projectRoot = cfg.projectRoot
const maxFixes    = cfg.maxFixes || 6
const tol         = cfg.tol || 1e-10
if (!target)      throw new Error('args.target is required')
if (!projectRoot) throw new Error('args.projectRoot is required')

const TRANSFORMATION = (cfg.transformation || '').replace(/^dev\/transformations\//, '').replace(/\/$/, '')
if (!TRANSFORMATION) throw new Error('args.transformation (a dir under dev/transformations/) is required')
const SPEC = `dev/transformations/${TRANSFORMATION}/desired_spec.md`
const TABLE = 'dev/tmp/assets/validate-output.md'
const ref = `Follow the validation criteria in ${SPEC}: build and run the comparison harness the Spec names,
which checks the produced artifact against its reference oracle layer by layer. Required tolerance: ${tol}.`

const VALIDATE_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['PASSED', 'FAILED'] },
    maxRelErr: { type: 'number', description: 'worst relative error across all checks' },
    worstCheck: { type: 'string', description: 'name of the worst-failing check, or ""' },
  },
  required: ['status', 'maxRelErr'],
}
const FIX_SCHEMA = {
  type: 'object',
  properties: {
    fixed: { type: 'boolean', description: 'true if the artifact was edited this cycle' },
    change: { type: 'string', description: 'one-line description of the fix' },
  },
  required: ['fixed'],
}

const validate = (n) => agent(
  `${n === 0 ? 'Validate' : 'Re-validate'} the produced artifact for "${target}" against its oracle.
Project root: ${projectRoot}. ${ref}
Write the check table (ref/got/relErr per check) to ${TABLE}. Return PASSED only if every check is within
${tol}; otherwise FAILED with the worst relative error and worst-failing check.`,
  { label: `validate:${n}`, phase: 'Validate', schema: VALIDATE_SCHEMA }
)

phase('Validate')
log(`Validating ${target} against its oracle...`)
let result = await validate(0)
if (!result || result.status === 'PASSED') {
  log(`Validation passed (maxRelErr=${result?.maxRelErr ?? 'n/a'}).`)
  return { status: 'PASSED', maxRelErr: result?.maxRelErr ?? null, fixes: 0 }
}

for (let n = 1; n <= maxFixes; n++) {
  phase('Fix')
  log(`Fix ${n}/${maxFixes} (worst check: ${result.worstCheck || 'n/a'})`)
  const fix = await agent(
    `The artifact for "${target}" does not yet match its oracle (fix ${n}/${maxFixes}). Read ${TABLE} for the
failing checks. A mismatch is usually a small, local slip (an index permutation, an argument swap, a 0/1-based
offset, a wrong constant). Diff the artifact against its source per the Spec. Edit ONLY the artifact under
${projectRoot} to fix the single worst-failing block, and return a one-line 'change' describing the edit (the
caller records it in the Plan). Return fixed=false if you cannot identify a change. Do NOT re-run the validator.
${ref}`,
    { label: `fix:${n}`, phase: 'Fix', schema: FIX_SCHEMA }
  )
  if (!fix?.fixed) {
    log(`Fix ${n} made no change — loop is stuck.`)
    return { status: 'FAILED', reason: 'stuck', fixes: n - 1 }
  }

  phase('Validate')
  result = await validate(n)
  if (!result) break
  if (result.status === 'PASSED') {
    log(`Passed after ${n} fix cycle(s) (maxRelErr=${result.maxRelErr}).`)
    return { status: 'PASSED', maxRelErr: result.maxRelErr, fixes: n }
  }
}

log(`Reached cap of ${maxFixes} fix attempt(s); artifact still does not match its oracle.`)
return { status: 'FAILED', reason: 'cap_reached', fixes: maxFixes }
