// Workflow: kokkos-translate — stage 2, C++ → Kokkos kernel.
//
// Ports an MCFM C++ amplitude (stage-1 output) into a Pepper device kernel, guided
// by the shared Spec (dev/transformations/cpp-to-kokkos/desired_spec.md). Prompts
// point at the Spec rather than restating it.
//
// The headline pattern here is the SIZE-GATE: a cheap deterministic Triage counts the
// call tree, and the workflow routes accordingly —
//   small tree  → Direct: one agent ports + validates + assembles in a single pass.
//   large tree  → Split: a coarse piece DAG (each piece has its own libmcfm oracle),
//                 authored bottom-up level by level, then a serial Assemble.
// Both paths converge on the shared verification loop and doctests:
//   … → Validate (the nested kokkos-validate-loop) → Test (doctests + pepper_test).
//
// Like the stage-1 workflow, this one is independent of the transformation it drives:
// it reads the Spec from the transformation directory passed in args, so it is invoked
// as "Run kokkos-translate for dev/transformations/<transformation>".
//
// Config (args): projectRoot (required), transformation (dir under dev/transformations/,
//                default 'cpp-to-kokkos'), amplitude OR amplitudes:[...] (batch, in
//                dependency order), directMax (size gate, 30), tol (1e-10), maxFixes (6).

export const meta = {
  name: 'kokkos-translate',
  description: 'Port MCFM C++ amplitude(s) to Pepper Kokkos kernels. Size-gated: small call trees go direct through one agent; large ones split into oracle-validated pieces, then assemble, validate, doctest.',
  whenToUse: 'Run kokkos-translate for dev/transformations/<transformation>. args:{projectRoot, transformation, amplitude:"qqb_z2jet_v"} for one, or {amplitudes:[...]} for a batch.',
  phases: [
    { title: 'Triage',      detail: 'closure-object count; pick direct vs split', model: 'sonnet' },
    { title: 'Direct port', detail: 'small tree: one agent ports + validates + assembles', model: 'opus' },
    { title: 'Split',       detail: 'large tree: coarse oracle-validated piece DAG', model: 'opus' },
    { title: 'Author',      detail: 'one agent per piece, bottom-up; freeze at tolerance', model: 'sonnet' },
    { title: 'Assemble',    detail: 'Params + kernel header + dispatch (serial)', model: 'opus' },
    { title: 'Validate',    detail: 'nested full-ME validate↔fix loop vs libmcfm' },
    { title: 'Test',        detail: 'doctests + CMake + pepper_test', model: 'opus' },
  ],
}

const cfg = typeof args === 'string' ? JSON.parse(args) : (args || {})
const PROJECT = cfg.projectRoot
if (!PROJECT) throw new Error('args.projectRoot (absolute path to the lab-notebook root) is required')
const AMPLITUDES = cfg.amplitudes?.length ? cfg.amplitudes : (cfg.amplitude ? [cfg.amplitude] : [])
if (!AMPLITUDES.length) throw new Error('args.amplitude or args.amplitudes:[...] is required')
const DIRECT_MAX = cfg.directMax ?? 30
const TOL        = cfg.tol       || 1e-10
const MAXFIXES   = cfg.maxFixes  ?? 6

// The transformation is a parameter; accept a bare name or a full directory path.
const TRANSFORMATION = (cfg.transformation || 'cpp-to-kokkos').replace(/^dev\/transformations\//, '').replace(/\/$/, '')
const SPEC = `dev/transformations/${TRANSFORMATION}/desired_spec.md`
const ENV  = `source ${PROJECT}/environment.sh`

const TRIAGE_SCHEMA = {
  type: 'object',
  properties: {
    objects:    { type: 'integer', description: 'closure object count from calltree_closure.py' },
    ready:      { type: 'boolean', description: 'true if every closure object is C++ (stage-1 ready)' },
    kernelName: { type: 'string' },
    entry:      { type: 'string', description: 'entry source relative to $MCFM_HOME/src' },
    oracle:     { type: 'string', description: 'libmcfm extern "C" symbol for the whole amplitude' },
  },
  required: ['objects', 'kernelName', 'entry', 'oracle'],
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
    kernelName: { type: 'string' },
    pieces: { type: 'array', items: {
      type: 'object',
      properties: {
        id: { type: 'string' }, level: { type: 'integer', description: '0 = leaf' },
        sources: { type: 'array', items: { type: 'string' } },
        oracle: { type: 'string', description: 'libmcfm symbol to validate this piece against' },
      }, required: ['id', 'level', 'oracle'],
    } },
    blockers: { type: 'array', items: { type: 'string' } },
  },
  required: ['kernelName', 'pieces'],
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

async function portOne(AMP) {
  // Triage — cheap, deterministic size gate (a closure count, not a full audit).
  phase('Triage')
  const tri = await agent(
    `Size the "${AMP}" call tree to pick direct vs split — a cheap pass, not a full audit.
Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`.
Run \`python3 ${PROJECT}/dev/tools/closure/calltree_closure.py <entry-base-name>\` and read its footer: the
object count → 'objects', all-C++ → 'ready'. Find the entry .cpp under $MCFM_HOME/src → 'entry' and its
extern "C" twin in libmcfm → 'oracle'; derive 'kernelName'. Return only the structured object.`,
    { label: 'triage', phase: 'Triage', schema: TRIAGE_SCHEMA, effort: 'low' }
  )
  if (!tri || typeof tri.objects !== 'number') return { status: 'FAILED', stage: 'triage', amplitude: AMP }
  if (tri.ready === false) {
    log('Triage: closure has plain-Fortran objects → stage-1 must translate them first.')
    return { status: 'BLOCKED', stage: 'triage', amplitude: AMP }
  }

  const NAME = tri.kernelName || AMP
  const direct = tri.objects <= DIRECT_MAX
  log(`Triage: ${tri.objects} objects → ${direct ? `DIRECT (≤ ${DIRECT_MAX})` : `SPLIT (> ${DIRECT_MAX})`}.`)

  if (direct) {
    // Direct — one agent ports the whole small tree, validates it, assembles the kernel.
    phase('Direct port')
    const d = await agent(
      `Port the SMALL amplitude "${NAME}" (${tri.objects} objects) — the whole call tree — into one kernel,
in one pass. Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC} and follow
§2–§4 (and §5 if it calls QCDLoop). Write $PEPPER_HOME/src/mcfm_analytics/${NAME}_kernel.h (helpers, the pure
${NAME}_me2, the templated dispatch kernel) + the one-line .cpp TU, with the // MCFM sources: provenance line.
Validate the full ME against oracle ${tri.oracle} using dev/tools/kokkos/run_validation.sh; iterate to ≤ ${TOL}.
Do NOT wire CMake or doctests (the Test phase does). Return written + worstRelErr.`,
      { label: `direct:${NAME}`, phase: 'Direct port', schema: WRITTEN_SCHEMA }
    )
    if (!d?.written) return { status: 'FAILED', stage: 'direct', amplitude: AMP }
    log(`Direct port wrote ${NAME}_kernel.h (self-validated ${d.worstRelErr || 'n/a'}).`)
  } else {
    // Split — a coarse piece DAG; each piece has its own libmcfm oracle, so it can be
    // authored and frozen independently, bottom-up, then assembled serially.
    phase('Split')
    const plan = await agent(
      `Split the "${AMP}" call tree into the FEWEST author-sized pieces that each still have a libmcfm oracle
(not one piece per function). Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC}
§7 (splitting) and §5 (QCDLoop). Cross-check completeness with
\`python3 ${PROJECT}/dev/tools/closure/calltree_closure.py <entry-base-name>\`. For each piece record id, DAG
level (0 = leaf), its stage-1 sources, and the libmcfm oracle symbol. List any blocker (a callee with no
stage-1 .cpp). Return the structured object.`,
      { label: 'split', phase: 'Split', schema: SPLIT_SCHEMA }
    )
    if (!plan?.pieces?.length) return { status: 'FAILED', stage: 'split', amplitude: AMP }
    if (plan.blockers?.length) {
      log(`Blockers must be cleared first: ${plan.blockers.join('; ')}`)
      return { status: 'BLOCKED', stage: 'split', amplitude: AMP, plan }
    }

    // Author each level in parallel; a level barrier is real — a level-N piece
    // includes the FROZEN level-<N fragments. A failed piece aborts before its
    // dependents author against a broken fragment.
    const done = new Map()
    const maxLevel = Math.max(...plan.pieces.map((p) => p.level))
    for (let L = 0; L <= maxLevel; L++) {
      const level = plan.pieces.filter((p) => p.level === L)
      if (!level.length) continue
      log(`Author level ${L}/${maxLevel}: ${level.map((p) => p.id).join(', ')}`)
      const rows = await parallel(level.map((p) => () =>
        agent(
          `Author kernel fragment "${p.id}" of "${NAME}". Work from ${PROJECT}; prefix env commands with
\`${ENV} &&\`. READ ${PROJECT}/${SPEC} §2–§5. Stage-1 sources: ${p.sources?.join(', ') || '(see plan)'}.
Pre-pass each with \`python3 dev/tools/kokkos/kokkosify.py\` and resolve every KOKKOSIFY-TODO. Write one
fragment $PEPPER_HOME/src/mcfm_analytics/${NAME}_parts/${p.id}.h (namespace mcfm_${NAME}, the // MCFM sources:
line, frozen deps included never edited). Validate in isolation against oracle ${p.oracle} to ≤ ${TOL}. Write
only your fragment; a piece that cannot meet tolerance returns authored="failed" with the symptom.`,
          { label: `author:${p.id}`, phase: 'Author', schema: PIECE_SCHEMA })
      ))
      rows.filter(Boolean).forEach((r) => done.set(r.piece, r))
      const stuck = level.filter((p) => done.get(p.id)?.authored !== 'yes')
      if (stuck.length) {
        log(`Level ${L} has unfixable piece(s): ${stuck.map((p) => p.id).join(', ')} — aborting.`)
        return { status: 'FAILED', stage: 'author', amplitude: AMP, plan }
      }
    }

    // Assemble — serial: the trust anchor that owns the shared kernel files.
    phase('Assemble')
    const globals = [...new Set([...done.values()].flatMap((r) => r.globals || []))]
    const asm = await agent(
      `Serial ASSEMBLE of "${NAME}" — you alone own the shared kernel files. Work from ${PROJECT}; prefix env
commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC} §2, §7. The frozen fragments are in ${NAME}_parts/.
Globals reported by the pieces (→ Params fields): ${globals.join(', ') || '(none)'}. Write ${NAME}_kernel.h
(include the fragments, the POD Params struct, the pure ${NAME}_me2, the templated dispatch kernel) + the
one-line .cpp TU, with the // MCFM sources: line. Smoke-compile through the shim. Fragments are frozen — if
one cannot compile, report it in notes instead of editing it. Do NOT wire CMake or run the validation loop.
Return written.`,
      { label: 'assemble', phase: 'Assemble', schema: WRITTEN_SCHEMA }
    )
    if (!asm?.written) return { status: 'FAILED', stage: 'assemble', amplitude: AMP, plan }
  }

  // Validate — the nested loop (shared by both paths). If pieces pass but the full ME
  // disagrees, the bug is in the assembly layer (§7).
  phase('Validate')
  const val = await workflow('kokkos-validate-loop', { amplitude: NAME, projectRoot: PROJECT, transformation: TRANSFORMATION, maxFixes: MAXFIXES, tol: TOL })
  if (val?.status !== 'PASSED') {
    log(`Full-ME validation did not converge (${val?.reason || 'no result'}).`)
    return { status: 'FAILED', stage: 'validate', amplitude: AMP, validation: val }
  }
  log(`Kernel matches libmcfm (maxRelErr=${val.maxRelErr}, fixes=${val.fixes}).`)

  // Test — doctests + CMake + pepper_test.
  phase('Test')
  const test = await agent(
    `The "${NAME}" kernel now matches libmcfm (maxRelErr=${val.maxRelErr}). Finish per ${PROJECT}/${SPEC} §4
step 5. Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`. Add layered DOCTEST_TEST_CASEs to
$PEPPER_HOME/tests/unit_tests/matrix_elements.cpp mirroring the existing MCFM-analytics cases; register
${NAME}_kernel.h + .cpp in src/CMakeLists.txt; build and run
\`pepper_test --dt-test-case="*${NAME}*"\` and re-run "*MCFM*" to prove no regression. Return PASSED only if
the new doctests and the pre-existing cases all pass.`,
    { label: 'test', phase: 'Test', schema: TEST_SCHEMA }
  )
  const status = test?.status === 'PASSED' ? 'VERIFIED' : 'FAILED'
  log(`Run complete: ${status} — path=${direct ? 'direct' : 'split'}, full ME at ${val.maxRelErr}.`)
  return { status, amplitude: AMP, kernelName: NAME, path: direct ? 'direct' : 'split', validation: val, test }
}

// Driver — one amplitude, or a batch run sequentially in dependency order so an
// earlier amplitude's frozen fragments are on disk for a later one to reuse.
if (AMPLITUDES.length === 1) return await portOne(AMPLITUDES[0])

log(`Batch: ${AMPLITUDES.length} amplitude(s), sequential — ${AMPLITUDES.join(', ')}.`)
const results = []
for (const amp of AMPLITUDES) {
  log(`── ${amp} ──`)
  const r = await portOne(amp)
  results.push(r)
  if (r?.status !== 'VERIFIED') log(`WARNING: ${amp} ended ${r?.status || 'no-result'} — later reuses may fail.`)
}
const nVerified = results.filter((r) => r?.status === 'VERIFIED').length
log(`Batch complete: ${nVerified}/${results.length} verified.`)
return { batch: true, amplitudes: AMPLITUDES, verified: nVerified, results }
