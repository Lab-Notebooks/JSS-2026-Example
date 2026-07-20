// Workflow: validate — the check-and-fix loop.
//
// The simplest kind of loop: check, fix, check again, and repeat until every check
// passes or it stops making progress. Its only memory between rounds is a file on disk.
// It compares a finished output against the reference the Spec names, and takes turns
// between finding-and-fixing one problem and re-checking. The `port` workflow calls this
// as its correctness check; it also runs on its own once an output exists and needs to be
// made to match.
//
// It works for any step: the step's folder is a required input and the Spec is read from
// there, so any step whose Spec names a per-block reference and a compare harness can use
// this same loop.
//
// The only file passed between steps is the check table dev/tmp/assets/validate-output.md:
// the check step writes it (reference / got / relative error per check) and the fix step
// reads it. It is throwaway and rebuilt each round. What to keep (what changed, the result
// per target) goes in the step's Plan, not in this scratch file.
//
// Config (args): target (required), projectRoot (required), transformation (required —
//                a folder under dev/transformations/), maxFixes (6), tol (1e-10).

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
