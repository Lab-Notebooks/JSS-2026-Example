// Workflow: kokkos-validate-loop — the stage-2 verification loop.
//
// This is the "loop" primitive in its minimal form: a deterministic validate↔fix
// cycle whose only cross-iteration state lives on disk. It validates a
// ported Kokkos kernel against the original MCFM C++ (via libmcfm + the host shim),
// and alternates diagnose-and-fix with re-validate until every check passes or no
// further progress is possible. kokkos-translate calls it; it also runs standalone
// once a kernel header exists and needs to be made equivalent.
//
// Shared state (scratch, under dev/tools/assets/):
//   kokkos-validate-output.md      the check table, written by the validate step
//   kokkos-translate-checklist.md  appended by the fix step
//
// Independent of the transformation: it reads the Spec from the transformation
// directory passed in args (default 'cpp-to-kokkos').
//
// Config (args): amplitude (required), projectRoot (required), transformation
//                (default 'cpp-to-kokkos'), maxFixes (6), tol (1e-10).

export const meta = {
  name: 'kokkos-validate-loop',
  description: 'Validate a ported Kokkos kernel against MCFM and loop diagnose → fix → re-validate until equivalent or stuck. The stage-2 verification bar, driven as a loop.',
  whenToUse: 'args:{amplitude, projectRoot, maxFixes, tol}. Requires the kernel header to exist under $PEPPER_HOME/src/mcfm_analytics.',
  phases: [
    { title: 'Validate', detail: 'build + run the libmcfm vs kernel comparison' },
    { title: 'Fix',      detail: 'diagnose the mismatch, edit the kernel header' },
  ],
}

const cfg = typeof args === 'string' ? JSON.parse(args) : (args || {})
const amplitude   = cfg.amplitude
const projectRoot = cfg.projectRoot
const maxFixes    = cfg.maxFixes || 6
const tol         = cfg.tol || 1e-10
if (!amplitude)   throw new Error('args.amplitude is required')
if (!projectRoot) throw new Error('args.projectRoot is required')

const TRANSFORMATION = (cfg.transformation || 'cpp-to-kokkos').replace(/^dev\/transformations\//, '').replace(/\/$/, '')
const SPEC = `dev/transformations/${TRANSFORMATION}/desired_spec.md`
const ref = `Follow ${SPEC} §4 (build the validator from dev/tools/kokkos/validator_skeleton.cpp and run it
with dev/tools/kokkos/run_validation.sh, which links libmcfm and compiles the kernel through the host shim).
Required tolerance: ${tol}.`

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
    fixed: { type: 'boolean', description: 'true if the kernel header was edited this cycle' },
    change: { type: 'string', description: 'one-line description of the fix' },
  },
  required: ['fixed'],
}

const validate = (n) => agent(
  `${n === 0 ? 'Validate' : 'Re-validate'} the ported Pepper kernel for "${amplitude}" against MCFM.
Project root: ${projectRoot}. ${ref}
Write the check table (ref/got/relErr per check) to dev/tools/assets/kokkos-validate-output.md. Return PASSED
only if every check is within ${tol}; otherwise FAILED with the worst relative error and worst-failing check.`,
  { label: `validate:${n}`, phase: 'Validate', schema: VALIDATE_SCHEMA }
)

phase('Validate')
log(`Validating ${amplitude} against MCFM...`)
let result = await validate(0)
if (!result || result.status === 'PASSED') {
  log(`Validation passed (maxRelErr=${result?.maxRelErr ?? 'n/a'}).`)
  return { status: 'PASSED', maxRelErr: result?.maxRelErr ?? null, fixes: 0 }
}

for (let n = 1; n <= maxFixes; n++) {
  phase('Fix')
  log(`Fix ${n}/${maxFixes} (worst check: ${result.worstCheck || 'n/a'})`)
  const fix = await agent(
    `The Kokkos kernel for "${amplitude}" does not yet match MCFM (fix ${n}/${maxFixes}). Read
dev/tools/assets/kokkos-validate-output.md for the failing checks. A mismatch is almost always an
index-permutation or za↔zb swap, a 0/1-based slip, or a wrong coupling — diff the kernel helper against the
MCFM C++ source in $MCFM_HOME. Edit ONLY the kernel header under ${projectRoot} to fix the single
worst-failing block. Append "- [x] <what you changed>" to dev/tools/assets/kokkos-translate-checklist.md.
Return fixed=false if you cannot identify a change. Do NOT re-run the validator. ${ref}`,
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

log(`Reached cap of ${maxFixes} fix attempt(s); kernel still does not match MCFM.`)
return { status: 'FAILED', reason: 'cap_reached', fixes: maxFixes }
