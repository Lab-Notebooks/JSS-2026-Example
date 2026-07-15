// ═══════════════════════════════════════════════════════════════════════════════
// Workflow : kokkos-validate-loop  (stage-2 verification loop)
// Purpose  : Validate a ported Pepper Kokkos kernel against the original MCFM C++
//            (via the standalone host shim + libmcfm), and alternate
//            diagnose-and-fix → re-validate until every check passes or no further
//            progress can be made. This is the stage-2 verification bar
//            (dev/cpp-to-kokkos/desired_spec.md §4-6) driven as a loop.
// Invoked  : by kokkos-translate.js, or directly once a kernel header exists and
//            needs to be made equivalent to MCFM.
// Inputs   : args.amplitude    — amplitude / kernel name (e.g. "qqb_z1jet_v")
//            args.projectRoot  — absolute path to the lab-notebook root
//            args.maxFixes     — max fix cycles before giving up (default 6)
//            args.tol          — required max relative error (default 1e-10)
//            args.scopeNote    — binding scope directive
// Outputs  : { status:'PASSED', maxRelErr, fixes } | { status:'FAILED', reason, fixes }
//
// State shared between isolated agents (scratch, gitignored under tools/assets/):
//   tools/assets/kokkos-validate-output.md      — written by the validate agent
//   tools/assets/kokkos-translate-checklist.md  — appended by the fix agent
// ═══════════════════════════════════════════════════════════════════════════════

export const meta = {
  name: 'kokkos-validate-loop',
  description: 'Validate a ported Kokkos kernel against MCFM and loop diagnose→fix→re-validate until it is equivalent or stuck. The stage-2 verification bar, driven as a loop.',
  whenToUse: 'Pass args: { amplitude:"qqb_z1jet_v", projectRoot:"/abs/path", maxFixes:6, tol:1e-10 }. Requires the kernel header to already exist under $PEPPER_HOME/src/mcfm_analytics. Each cycle runs as an isolated agent; state is shared via tools/assets/kokkos-*.md.',
  phases: [
    { title: 'Validate', detail: 'Build+run the libmcfm vs kernel comparison, write kokkos-validate-output.md' },
    { title: 'Fix',      detail: 'Diagnose the mismatching block, edit the kernel header, append to the checklist' },
  ],
}

// ── Arguments ────────────────────────────────────────────────────────────────
const cfg = typeof args === 'string' ? JSON.parse(args) : (args || {})
const amplitude   = cfg.amplitude   || null
const projectRoot = cfg.projectRoot || null
const maxFixes    = cfg.maxFixes    || 6
const tol         = cfg.tol         || 1e-10
const scopeNote   = cfg.scopeNote   || ''

if (!amplitude)   throw new Error('args.amplitude is required')
if (!projectRoot) throw new Error('args.projectRoot is required')

const skillRef =
  `Follow dev/cpp-to-kokkos/desired_spec.md §4-6 (build the standalone validator from ` +
  `tools/kokkos/validator_skeleton.cpp and build/run it with tools/kokkos/run_validation.sh, ` +
  `which links libmcfm and compiles the real kernel headers via the Kokkos shim). ` +
  `Required tolerance: ${tol}.` +
  (scopeNote ? `\nSCOPE DIRECTIVE from the orchestrator (binding — configure the MCFM reference side ` +
  `consistently with it): ${scopeNote}` : '')

// ── Schemas ──────────────────────────────────────────────────────────────────
const VALIDATE_SCHEMA = {
  type: 'object',
  properties: {
    status:     { type: 'string', enum: ['PASSED', 'FAILED'] },
    maxRelErr:  { type: 'number', description: 'Worst relative error across all checks' },
    worstCheck: { type: 'string', description: 'Name of the worst-failing check, or "" if all pass' },
  },
  required: ['status', 'maxRelErr'],
}

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    fixed:  { type: 'boolean', description: 'true if the kernel header was edited this cycle' },
    change: { type: 'string',  description: 'One-line description of the fix applied' },
  },
  required: ['fixed'],
}

// ── Initial validation ───────────────────────────────────────────────────────
phase('Validate')
log(`Validating ${amplitude} kernel against MCFM...`)

const first = await agent(
  `Validate the ported Pepper kernel for "${amplitude}" against the original MCFM C++.
Project root: ${projectRoot}.
${skillRef}
Write the full check table (each check's ref/got/relErr) to tools/assets/kokkos-validate-output.md. Return
status PASSED only if every check is within ${tol}; otherwise FAILED with the worst relative error and the
name of the worst-failing check.`,
  { label: 'validate:0', phase: 'Validate', schema: VALIDATE_SCHEMA }
)

if (!first || first.status === 'PASSED') {
  log(`Validation passed (maxRelErr=${first ? first.maxRelErr : 'n/a'}).`)
  return { status: 'PASSED', maxRelErr: first ? first.maxRelErr : null, fixes: 0 }
}

// ── Fix → re-validate loop ───────────────────────────────────────────────────
let fixes = 0

while (fixes < maxFixes) {
  fixes++
  log(`Fix attempt ${fixes} / ${maxFixes} (worst check: ${first.worstCheck || 'n/a'})`)

  phase('Fix')
  const fix = await agent(
    `The Kokkos kernel for "${amplitude}" does not yet match MCFM. This is fix attempt ${fixes} of ${maxFixes}.
Read tools/assets/kokkos-validate-output.md for the failing checks. A mismatch in a translated amplitude is
almost always an index-permutation or za<->zb-swap slip, a 0-based/1-based index error, or a wrong
coupling/normalisation — diff the kernel helper against the corresponding MCFM C++ source line in $MCFM_HOME.
Edit ONLY the kernel header under ${projectRoot} to fix the single worst-failing block. Append a
"- [x] <what you changed>" line to tools/assets/kokkos-translate-checklist.md. Return fixed=false if you could
not identify a change to make. Do NOT re-run the validator — a separate step will.
${skillRef}`,
    { label: `fix:${fixes}`, phase: 'Fix', schema: FIX_SCHEMA }
  )

  if (!fix) break
  if (!fix.fixed) {
    log(`Fix ${fixes} made no change — loop is stuck.`)
    return { status: 'FAILED', reason: 'stuck', fixes }
  }

  phase('Validate')
  log(`Re-validating after fix ${fixes}...`)
  const reval = await agent(
    `Re-validate the ported Pepper kernel for "${amplitude}" against MCFM.
Project root: ${projectRoot}.
${skillRef}
Overwrite tools/assets/kokkos-validate-output.md with the new check table. Return status PASSED only if every
check is within ${tol}; otherwise FAILED with the worst relative error and worst-failing check name.`,
    { label: `validate:${fixes}`, phase: 'Validate', schema: VALIDATE_SCHEMA }
  )

  if (!reval) break
  if (reval.status === 'PASSED') {
    log(`Validation passed after ${fixes} fix cycle(s) (maxRelErr=${reval.maxRelErr}).`)
    return { status: 'PASSED', maxRelErr: reval.maxRelErr, fixes }
  }
  first.worstCheck = reval.worstCheck
}

log(`Reached cap of ${maxFixes} fix attempt(s); kernel still does not match MCFM.`)
return { status: 'FAILED', reason: 'cap_reached', fixes: maxFixes }
