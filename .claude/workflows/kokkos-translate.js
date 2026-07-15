// ═══════════════════════════════════════════════════════════════════════════════
// Workflow : kokkos-translate  (stage 2: C++ → Kokkos kernel)
// Purpose  : Port an MCFM C++ amplitude (stage-1 output) into a Pepper Kokkos
//            device kernel. Single-pass: it translates and stops.
//
//            Control flow is size-gated (Spec §7):
//              Triage  — deterministic closure-object count (cheap; runs
//                        tools/calltree_closure.py).
//              if objects <= directMax (default 30):
//                Direct port — ONE agent ports the whole small call tree into a
//                              single kernel header + Params, validates the full
//                              ME against the entry oracle, smoke-compiles.
//              else:
//                Split → Author (per DAG level, frozen at tol) → Fix → Assemble.
//              Validate — nested full-ME validate<->fix loop vs libmcfm (both paths).
//              Test     — doctests + CMake wiring + pepper_test (both paths).
//
// Spec     : dev/cpp-to-kokkos/desired_spec.md is the single source of truth for
//            the how; this script is orchestration only.
// Inputs   : args.projectRoot  — absolute path to the lab-notebook root (REQUIRED)
//            args.amplitude    — one amplitude, e.g. "qqb_z2jet_v" or "Z2jet/qqb_z2jet_v.cpp"
//            args.amplitudes   — OR a list [..] ported sequentially in dependency order
//            args.directMax    — closure objects at/under which the direct port is used (30)
//            args.maxChunkLoc  — chunk-size ceiling the Split must break above (400)
//            args.pieceTol     — per-piece isolation tolerance   (default 1e-12)
//            args.tol          — full-ME equivalence tolerance   (default 1e-10)
//            args.maxPieces    — sanity cap on the chunk count    (default 40)
//            args.fixRounds    — piece-level fix escalation rounds (default 1)
//            args.maxFixes     — full-ME validate<->fix cycles     (default 6)
//            args.scopeNote    — binding scope directive injected into prompts
//            args.model / args.{triage,split,author,direct,loop,fix,assemble,test}Model
// Outputs  : { status, kernelName, plan, authored, validation, test, ... } to record in the Plan
// ═══════════════════════════════════════════════════════════════════════════════

export const meta = {
  name: 'kokkos-translate',
  description: 'Port MCFM C++ amplitude(s) to Pepper Kokkos kernels in a single pass. Size-gated per amplitude: small call trees go direct through one agent; large ones use the split protocol (coarse author-sized chunks, frozen bottom-up against libmcfm oracles), then assemble, validate, doctest. A batch runs sequentially in dependency order.',
  whenToUse: 'Stage-2 (C++ -> Kokkos) port of one amplitude (args:{projectRoot, amplitude:"qqb_z2jet_v"}) or a batch (args:{projectRoot, amplitudes:["qqb_z2jet","qqb_z2jet_v"]}). Translates end-to-end. Tune the direct-vs-split boundary with directMax (default 30 closure objects).',
  phases: [
    { title: 'Triage',      detail: 'Closure-object count (cheap); pick direct vs split', model: 'sonnet' },
    { title: 'Direct port', detail: 'Small tree: one agent ports + validates + assembles', model: 'opus' },
    { title: 'Split',       detail: 'Large tree: coarse piece DAG of author-sized chunks', model: 'opus' },
    { title: 'Author',      detail: 'One agent per chunk, level-by-level; freeze at tolerance', model: 'sonnet' },
    { title: 'Fix',         detail: 'Escalate failed chunks', model: 'opus' },
    { title: 'Assemble',    detail: 'Params struct + kernel header + dispatch (serial)', model: 'opus' },
    { title: 'Validate',    detail: 'Nested full-ME validate<->fix loop vs libmcfm' },
    { title: 'Test',        detail: 'Doctests + CMake wiring + pepper_test', model: 'opus' },
  ],
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const cfg = typeof args === 'string' ? JSON.parse(args) : (args || {})
const PROJECT = cfg.projectRoot
if (!PROJECT) {
  throw new Error('args.projectRoot (absolute path to the lab-notebook root) is required')
}
const AMPLITUDES = (Array.isArray(cfg.amplitudes) && cfg.amplitudes.length)
  ? cfg.amplitudes
  : (cfg.amplitude ? [cfg.amplitude] : [])
if (!AMPLITUDES.length) {
  throw new Error('args.amplitude (single, e.g. "qqb_z2jet_v") or args.amplitudes:[...] (batch, dependency order) is required')
}

const DIRECT_MAX   = cfg.directMax   ?? 30      // closure objects <= this → direct single-agent port
const MAXCHUNKLOC  = cfg.maxChunkLoc ?? 400     // Split must break a subtree above this rather than merge it
const PIECETOL     = cfg.pieceTol    || 1e-12
const TOL          = cfg.tol         || 1e-10
const MAXPIECES    = cfg.maxPieces   || 40
const FIXROUNDS    = cfg.fixRounds   ?? 1
const MAXFIXES     = cfg.maxFixes    ?? 6

// Optional scope directive injected verbatim into the phase prompts.
const SCOPENOTE = cfg.scopeNote ? `\nSCOPE DIRECTIVE from the orchestrator (binding): ${cfg.scopeNote}\n` : ''

// Split/Assemble/Direct are the judgment-heavy trust anchors (Opus); chunk authors
// scale N-wide (Sonnet); closed-form scalar-integral chunks (§5) escalate to the
// loop model. Triage is a cheap deterministic sizing agent.
const TRIAGE_MODEL   = cfg.model || cfg.triageModel   || 'sonnet'
const SPLIT_MODEL    = cfg.model || cfg.splitModel    || 'opus'
const AUTHOR_MODEL   = cfg.model || cfg.authorModel   || 'sonnet'
const DIRECT_MODEL   = cfg.model || cfg.directModel   || 'opus'
const LOOP_MODEL     = cfg.model || cfg.loopModel     || 'opus'
const FIX_MODEL      = cfg.model || cfg.fixModel      || 'opus'
const ASSEMBLE_MODEL = cfg.model || cfg.assembleModel || 'opus'
const TEST_MODEL     = cfg.model || cfg.testModel     || 'opus'

const SPEC      = 'dev/cpp-to-kokkos/desired_spec.md'
const SRCENV    = `source ${PROJECT}/environment.sh`
const TEMPLATES = `tools/kokkos`

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------
const TRIAGE_SCHEMA = {
  type: 'object',
  properties: {
    objects:    { type: 'integer', description: 'closure object count from tools/calltree_closure.py (the "N/N objects" line)' },
    ready:      { type: 'boolean', description: 'true if every closure object is C++ (stage-1 READY); false = plain-Fortran blocker present' },
    kernelName: { type: 'string', description: 'kernel base name, e.g. qqb_z2jet_v' },
    entry:      { type: 'string', description: 'entry source relative to $MCFM_HOME/src, e.g. Z2jet/qqb_z2jet_v.cpp' },
    entryOracle:{ type: 'string', description: 'libmcfm extern "C" symbol for the whole amplitude, e.g. qqb_z2jet_v_wrapper' },
    nParticles: { type: 'integer', description: 'N in the kernel p[N][4] momentum array' },
    hasQcdloop: { type: 'boolean', description: 'true if any closure object calls loopI2/3/4 / qlI* (needs §5 closed forms)' },
    reuseHints: { type: 'string', description: 'brief note of already-ported mcfm_analytics reuse (from the "kokkos" column), or ""' },
    note:       { type: 'string' },
  },
  required: ['objects', 'kernelName', 'entry', 'entryOracle'],
}

const SPLIT_SCHEMA = {
  type: 'object',
  properties: {
    kernelName: { type: 'string', description: 'kernel base name' },
    entry:      { type: 'string', description: 'entry source relative to $MCFM_HOME/src' },
    nParticles: { type: 'integer', description: 'N in the kernel p[N][4] momentum array' },
    pieces: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id:      { type: 'string', description: 'short slug, becomes <id>.h in <name>_parts/' },
          title:   { type: 'string' },
          sources: { type: 'array', items: { type: 'string' }, description: 'stage-1 .cpp files (the whole merged subtree) relative to $MCFM_HOME/src' },
          level:   { type: 'integer', description: 'DAG level; 0 = leaf (no fragment deps)' },
          needs:   { type: 'array', items: { type: 'string' }, description: 'ids of lower-level fragments this chunk includes' },
          oracle:  { type: 'string', description: 'libmcfm symbol(s) to validate the chunk against' },
          qcdloop: { type: 'boolean', description: 'true if the chunk calls loopI2/3/4 / qlI* → §5 closed forms' },
          globals: { type: 'array', items: { type: 'string' }, description: 'module globals read → Params fields at assembly' },
          reuse:   { type: 'string', description: 'existing mcfm_analytics header to include instead of porting, or ""' },
          loc:     { type: 'integer', description: 'approx source lines of the whole chunk' },
        },
        required: ['id', 'sources', 'level', 'oracle'],
      },
    },
    paramsFields: { type: 'array', items: { type: 'string' }, description: 'proposed *_Params fields (union of globals + §2.5 couplings)' },
    blockers: {
      type: 'array',
      description: 'anything that stops the port: callee with no stage-1 .cpp, missing libmcfm, unresolvable device-portability issue',
      items: { type: 'object', properties: { piece: { type: 'string' }, reason: { type: 'string' } }, required: ['reason'] },
    },
    levels: { type: 'integer' },
    note:   { type: 'string' },
  },
  required: ['kernelName', 'entry', 'pieces', 'levels'],
}

const PIECE_SCHEMA = {
  type: 'object',
  properties: {
    piece:       { type: 'string' },
    authored:    { type: 'string', enum: ['yes', 'failed', 'deferred'] },
    fragment:    { type: 'string', description: 'path of the fragment header written' },
    worstRelErr: { type: 'string', description: 'worst relative error vs the libmcfm twin, e.g. 3e-15' },
    globals:     { type: 'array', items: { type: 'string' }, description: 'globals the fragment ACTUALLY needs (Params fields)' },
    notes:       { type: 'string', description: 'tolerance budget rationale (§5), stability option chosen, failure symptom' },
  },
  required: ['piece', 'authored'],
}

const ASSEMBLE_SCHEMA = {
  type: 'object',
  properties: {
    written:     { type: 'boolean' },
    files:       { type: 'array', items: { type: 'string' } },
    params:      { type: 'string', description: 'the *_Params struct fields as written' },
    worstRelErr: { type: 'string', description: 'worst full-ME relative error the agent itself observed vs the entry oracle (direct path), or "" ' },
    notes:       { type: 'string' },
  },
  required: ['written'],
}

const TEST_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['PASSED', 'FAILED'] },
    files:  { type: 'array', items: { type: 'string' } },
    notes:  { type: 'string', description: 'doctest cases added, tolerances, pepper_test tail' },
  },
  required: ['status'],
}

// ---------------------------------------------------------------------------
// portOne — the full per-amplitude pipeline (Triage → direct|split → Validate → Test).
// ---------------------------------------------------------------------------
async function portOne(AMPLITUDE) {

// ---------------------------------------------------------------------------
// Split phase (used by the large-tree path)
// ---------------------------------------------------------------------------
const runSplit = () => agent(
  `You are the SPLIT phase of the stage-2 (MCFM C++ → Kokkos) translation workflow. Work from ${PROJECT};
prefix every env-dependent command with \`${SRCENV} && <cmd>\` (the Bash tool resets env between calls).

Amplitude to port: "${AMPLITUDE}". READ ${PROJECT}/${SPEC} first — especially §4 (dependency audit),
§7 (splitting protocol), §5 (QCDLoop), §2.4/§2.5 (Params conventions).
${SCOPENOTE}

Build a COARSE piece DAG per §7. The goal is the FEWEST author-sized chunks that still each have a libmcfm
oracle — NOT one piece per function.
1. Locate the stage-1 entry .cpp under \$MCFM_HOME/src and follow EVERY call transitively (a device kernel
   absorbs its whole call tree). Grep, do not guess; callees may live in other src/ dirs (Need/, W2jet/, ...)
   or OUTSIDE src/ in \$MCFM_HOME/lib/ — search both before declaring a function missing.
2. CHUNKING (coarse by default). Start each chunk at a function that has a callable extern "C" twin in
   \$MCFM_HOME/install/lib/libmcfm.* (check with nm; record the exact symbol as 'oracle'), then MERGE that
   caller's whole callee subtree INTO THE SAME CHUNK and validate the chunk as a unit against the caller's
   oracle. Break a callee out into its own lower-level piece ONLY when: (a) REUSE — an equivalent is already
   ported in \$PEPPER_HOME/src/mcfm_analytics (include it), (b) SIZE — merging would push the chunk over
   ~${MAXCHUNKLOC} source lines, (c) QCDLOOP — it calls loopI2/3/4 / qlI* and must become a §5 closed-form
   piece grid-validated in isolation, or (d) SHARING — the same subtree is called by two or more chunks.
   Aim for chunks of roughly 150–${MAXCHUNKLOC} lines. A leaf with no extern "C" twin gets merged upward.
3. Assign DAG levels: level 0 = chunks with no fragment dependencies; a chunk's level = 1 + max(level of
   needs). 'needs' lists piece ids. 'sources' lists ALL stage-1 .cpp files merged into the chunk.
4. Per chunk record: stage-1 sources, module globals read (→ Params fields), qcdloop, approx total lines, and
   'reuse' if an already-ported equivalent exists — determine this from the 'kokkos' column of the closure
   tool below (it reads the '// MCFM sources:' provenance line every mcfm_analytics header carries). 'partial'
   means only some functions are ported — check the ones you need are among them. Reused pieces are included,
   never re-derived.
5. Blockers: any callee with NO stage-1 .cpp on disk (stage 1 must translate it first — name the .f), a
   missing \$MCFM_HOME/install/lib/libmcfm.*, or a portability problem §3/§5 cannot handle.
6. COMPLETENESS CROSS-CHECK (MANDATORY): run
   \`python3 ${PROJECT}/tools/calltree_closure.py <entry-base-name>\` — the symbol-level transitive closure
   from libmcfm's actual linked objects (authoritative; symbols do not lie). Every closure object must be
   (a) covered by some chunk's sources, (b) a *_mod.cpp module-data object (→ Params fields), or (c) explicitly
   listed in the plan note as dead/off-path WITH the gating reason. Any plain-FORTRAN object in the closure is
   an automatic blocker. Do NOT use the Doxygen roadmap (tools/build_roadmap.py) as a completeness authority
   for stage 2 — many of its per-file XMLs are empty stubs.
7. Propose the *_Params field list (union of globals + §2.5 couplings; virtual kernels nest the Born struct).

Write the human-readable plan to tools/assets/kokkos-split-${AMPLITUDE}.md (chunk table + DAG + blockers) and
return the structured object. Do NOT write any kernel code.`,
  { label: 'split', phase: 'Split', schema: SPLIT_SCHEMA, model: SPLIT_MODEL }
)

// ---------------------------------------------------------------------------
// Phase 1 — Triage: cheap, deterministic size gate (no dependency audit).
// ---------------------------------------------------------------------------
phase('Triage')
log(`Triage: sizing the ${AMPLITUDE} call tree (closure objects) to pick direct vs split...`)

const tri = await agent(
  `You are the TRIAGE phase of the stage-2 (MCFM C++ → Kokkos) translation workflow — a CHEAP sizing pass,
NOT a full dependency audit. Work from ${PROJECT}; prefix env-dependent commands with \`${SRCENV} && <cmd>\`.

Amplitude: "${AMPLITUDE}". Do only this:
1. Run \`python3 ${PROJECT}/tools/calltree_closure.py <entry-base-name>\` and read its footer lines: the
   "N/N objects are C++ -> READY" count is 'objects' and whether all are C++ is 'ready'. If any object is
   plain Fortran, set ready=false (a stage-1 blocker the split path will surface).
2. Locate the entry .cpp under \$MCFM_HOME/src (grep for the amplitude name) → 'entry' (path relative to
   \$MCFM_HOME/src). Read ONLY its signature/header to get 'nParticles' (N in p[N][4]) and the kernel base
   name → 'kernelName' (follow the qqb_z / qqb_z1jet / qqb_z2jet precedent).
3. Find the entry's extern "C" twin in \$MCFM_HOME/install/lib/libmcfm.* with nm → 'entryOracle'.
4. Set hasQcdloop=true if the closure output or a quick grep shows any loopI2/3/4 / qlI* call.
5. reuseHints: one line naming any already-ported mcfm_analytics headers the closure 'kokkos' column flags
   as reuse, or "".

Do NOT build the piece DAG, do NOT audit portability, do NOT write anything. Return the structured object.`,
  { label: 'triage', phase: 'Triage', schema: TRIAGE_SCHEMA, model: TRIAGE_MODEL, effort: 'low' }
)

if (!tri || typeof tri.objects !== 'number') {
  log('Triage failed to size the amplitude; aborting.')
  return { status: 'FAILED', stage: 'triage', amplitude: AMPLITUDE, triage: tri }
}
if (tri.ready === false) {
  log('Triage: closure contains plain-Fortran objects → stage-1 must translate them first. Aborting.')
  return { status: 'BLOCKED', stage: 'triage', amplitude: AMPLITUDE, triage: tri }
}

const DIRECT = tri.objects <= DIRECT_MAX
log(`Triage: ${tri.objects} closure objects → ${DIRECT ? `DIRECT single-agent port (<= ${DIRECT_MAX})` : `SPLIT protocol (> ${DIRECT_MAX})`}.`)

// Shared state populated by whichever path runs.
let NAME, asm, plan
let authoredRows = []

if (DIRECT) {
  // -------------------------------------------------------------------------
  // Direct port — one agent does Author + Assemble for a small call tree.
  // -------------------------------------------------------------------------
  phase('Direct port')
  NAME = tri.kernelName || AMPLITUDE
  log(`Direct port of ${NAME}: one agent ports the whole tree, validates the full ME, assembles the kernel...`)

  const direct = await agent(
    `You are the DIRECT-PORT agent for the stage-2 Kokkos port of "${NAME}" — a SMALL amplitude
(${tri.objects} closure objects), so you port the WHOLE call tree yourself into one kernel, in one pass.
You own the kernel files. Work from ${PROJECT}; prefix env-dependent commands with \`${SRCENV} && <cmd>\`.
READ ${PROJECT}/${SPEC} FIRST — §2 (conventions + kernel signatures), §3 (rules incl. the Kokkos::complex
division caveat), §4 (author + validate), §7, §8 (gotchas)${tri.hasQcdloop ? ', and §5 (closed-form scalar integrals) — this amplitude calls QCDLoop' : ''}.
${SCOPENOTE}

Entry: \$MCFM_HOME/src/${tri.entry}  (${tri.nParticles || 'N'} partons)
libmcfm oracle for the FULL ME: ${tri.entryOracle}
Reuse already-ported fragments where the closure flags them: ${tri.reuseHints || '(none reported — verify)'}

Do, in order:
1. Follow the entry's whole call tree (grep transitively; callees may live in other src/ dirs or in
   \$MCFM_HOME/lib/). Port every function into ONE kernel header
   \$PEPPER_HOME/src/mcfm_analytics/${NAME}_kernel.h: include guard; the provenance line
   \`// MCFM sources: <all stage-1 sources you ported, objlib-relative>\`; \`#include "../math.h"\`; reuse
   existing mcfm_analytics fragments via #include where the closure flags them; every helper
   KOKKOS_INLINE_FUNCTION inside \`namespace mcfm_${NAME}\`. Pure functions only — module globals become
   Params fields (POD struct, §2.4/§2.5 couplings; nest the Born struct if this is a virtual), no event-data
   types (G9), no STL/heap/QCDLoop calls (§3).${tri.hasQcdloop ? `
   For any loopI2/3/4 call, substitute a §5 analytic closed form and grid-validate it in isolation against
   the real QCDLoop through libmcfm (~1e-12) BEFORE using it; state the §5 stability option in notes.` : ''}
2. Provide the pure \`double ${NAME}_me2(double p[${tri.nParticles || 'N'}][4], const ...Params&)\` preserving
   the MCFM assembly structure, plus the \`template <typename event_data>\` dispatch kernel reading
   evt.e/px/py/pz(i,part) directly (NO sign flip, G1), dead-event guard (G8), writing evt.me2(i). Write the
   one-line TU \$PEPPER_HOME/src/mcfm_analytics/${NAME}_kernel.cpp.
3. VALIDATE the full ME against the oracle \`${tri.entryOracle}\` (§4 + §6): write a validator from
   ${TEMPLATES}/validator_skeleton.cpp feeding IDENTICAL fixture momenta (incoming legs negated when building
   arrays, §2.2; §2.5 canonical couplings) to both your ${NAME}_me2 and the libmcfm oracle. Run
   \`${TEMPLATES}/run_validation.sh <scratch>/validate.cpp\`. Iterate until worst relative error ≤ ${TOL}.
   Test BOTH energy conventions where they differ (§2.2). Do NOT loosen the tolerance silently.

Do NOT wire CMake or doctests (the Test phase does). Return written=true, the files, the Params fields as
written, and worstRelErr = the worst full-ME relative error you observed.`,
    { label: `direct:${NAME}`, phase: 'Direct port', schema: ASSEMBLE_SCHEMA, model: DIRECT_MODEL }
  )

  if (!direct || !direct.written) {
    log('Direct port failed; aborting.')
    return { status: 'FAILED', stage: 'direct', amplitude: AMPLITUDE, triage: tri, direct }
  }
  asm = direct
  plan = { kernelName: NAME, entry: tri.entry, nParticles: tri.nParticles, pieces: [], levels: 0, direct: true, note: tri.note }
  log(`Direct port wrote ${NAME}_kernel.h (self-validated worst rel err: ${direct.worstRelErr || 'n/a'}).`)

} else {
  // -------------------------------------------------------------------------
  // Split path — coarse piece DAG → author chunks → assemble.
  // -------------------------------------------------------------------------
  phase('Split')
  log(`Splitting the ${AMPLITUDE} call tree into coarse author-sized chunks...`)
  plan = await runSplit()

  if (!plan || !plan.pieces || plan.pieces.length === 0) {
    log('Split produced no chunks; aborting.')
    return { status: 'FAILED', stage: 'split', amplitude: AMPLITUDE, triage: tri, plan }
  }

  NAME = plan.kernelName || AMPLITUDE
  const PARTSDIR = `$PEPPER_HOME/src/mcfm_analytics/${NAME}_parts`
  const toPort = plan.pieces.filter((p) => !p.reuse)
  const reused = plan.pieces.filter((p) => p.reuse)
  const nLoop = toPort.filter((p) => p.qcdloop).length
  log(`Plan: ${plan.pieces.length} chunk(s) over ${plan.levels} level(s) — ${toPort.length} to port` +
      (reused.length ? `, ${reused.length} reused` : '') +
      (nLoop ? `, ${nLoop} with QCDLoop closed forms (§5)` : '') +
      ((plan.blockers || []).length ? `. BLOCKERS: ${plan.blockers.map((b) => b.reason).join('; ')}` : '.'))

  if ((plan.blockers || []).length) {
    log('Blockers must be cleared first (usually: run the stage-1 mcfm-translate workflow on the missing files).')
    return { status: 'BLOCKED', stage: 'split', amplitude: AMPLITUDE, triage: tri, plan }
  }
  if (toPort.length > MAXPIECES) {
    log(`Chunk count ${toPort.length} exceeds maxPieces=${MAXPIECES} — refusing; raise maxPieces or coarsen the split.`)
    return { status: 'TOO_LARGE', stage: 'split', amplitude: AMPLITUDE, triage: tri, plan }
  }

  // Author chunks level-by-level; Fix escalates failures per level. The level
  // barrier is genuine: a level-N chunk #includes the FROZEN level-<N fragments.
  const results = new Map()   // id → PIECE_SCHEMA row

  const authorPrompt = (p, symptom) => `You are a chunk AUTHOR of the stage-2 Kokkos port of "${NAME}"
(${symptom ? 'FIX attempt — a previous attempt failed' : 'first attempt'}). Work from ${PROJECT}; prefix
env-dependent commands with \`${SRCENV} && <cmd>\`.

Your chunk: id="${p.id}"${p.title ? ` (${p.title})` : ''}
  stage-1 sources (the whole merged subtree — port ALL into this one fragment): ${p.sources.map((s) => `\$MCFM_HOME/src/${s}`).join(', ')}
  libmcfm oracle symbol(s) to validate the chunk against: ${p.oracle}
  fragment dependencies (already FROZEN — include, never edit): ${(p.needs || []).length ? (p.needs || []).map((n) => `${PARTSDIR}/${n}.h`).join(', ') : '(none)'}
  reused prior kernels to include if useful: ${reused.length ? reused.map((r) => r.reuse).join(', ') : '(none)'}
  expected globals (verify against the source): ${(p.globals || []).join(', ') || '(none reported)'}
${symptom ? `  PREVIOUS FAILURE SYMPTOM: ${symptom}\n` : ''}${SCOPENOTE}
READ ${PROJECT}/${SPEC} FIRST — §2 (conventions), §3 (rules incl. the Kokkos::complex division caveat),
§4 (author), §8 (gotchas)${p.qcdloop ? ', and §5 (closed-form scalar integrals) — your chunk calls QCDLoop' : ''}.

Do, in order:
1. Deterministic pre-pass per §4 (scratch dir tools/assets/tmp/kokkos-${NAME}/${p.id}/), for EACH source:
   \`python3 ${TEMPLATES}/kokkosify.py \$MCFM_HOME/src/<source> -o <scratch>/draft.h -r <scratch>/report.md\`
   Resolve every KOKKOSIFY-TODO by hand; the report is your blocker/Params audit.
2. Write ONE fragment ${PARTSDIR}/${p.id}.h covering the whole chunk: include guard, then the machine-readable
   provenance line \`// MCFM sources: <all your stage-1 sources, objlib-relative, " (partial)" on any file you
   port only part of>\` (the closure reuse tracking reads it), then \`#include "../../math.h"\`, needed frozen
   fragments via \`#include "<dep>.h"\`, every helper KOKKOS_INLINE_FUNCTION inside \`namespace mcfm_${NAME}\`.
   Pure functions only — module globals become plain function parameters; no event-data types (G9), no
   STL/heap/QCDLoop calls (§3).
${p.qcdloop ? `3. §5: replace each loopI2/3/4 call with an analytic closed form (Ellis-Zanderighi 0712.1851 /
   QCDLoop-2.0 1605.03181 basis). Validate EACH closed form in isolation against the real QCDLoop through
   libmcfm over a threshold-spanning grid (~1e-12) BEFORE using it. State which §5 stability option you chose.
4.` : '3.'} Validate the chunk in isolation (§4 + §7): write <scratch>/validate_${p.id}.cpp (start from
   ${TEMPLATES}/validator_skeleton.cpp) calling your fragment AND the libmcfm oracle \`${p.oracle}\` on
   IDENTICAL inputs — fixture momenta pushed through spinoru for momentum-dependent chunks (incoming legs
   negated when building arrays, §2.2), random points for pure algebra; §2.5 canonical couplings. Run:
   \`${TEMPLATES}/run_validation.sh <scratch>/validate_${p.id}.cpp\`. Iterate until worst relative error
   ≤ ${PIECETOL}. A cancellation-prone combination may instead be budgeted by absolute contribution (§5) —
   if you do that, justify it in notes.

Hard constraints:
- Write ONLY ${PARTSDIR}/${p.id}.h and your own scratch files. Never edit other fragments, the kernel header,
  any CMakeLists, doctests, or shared headers.
- Do NOT loosen the tolerance silently; a chunk that cannot meet it returns authored="failed" with the
  symptom and the worst check name in notes.
Return ONE structured row (globals = what the fragment ACTUALLY needs). No file contents.`

  const maxLevel = Math.max(...toPort.map((p) => p.level))
  for (let L = 0; L <= maxLevel; L++) {
    const levelPieces = toPort.filter((p) => p.level === L)
    if (levelPieces.length === 0) continue
    log(`Author level ${L}/${maxLevel}: ${levelPieces.length} chunk(s) in parallel — ${levelPieces.map((p) => p.id).join(', ')}`)

    const rows = await parallel(levelPieces.map((p) => () =>
      agent(authorPrompt(p), {
        label: `author:${p.id}`, phase: 'Author', schema: PIECE_SCHEMA,
        model: p.qcdloop ? LOOP_MODEL : AUTHOR_MODEL,
      })
    ))
    rows.filter(Boolean).forEach((r) => results.set(r.piece, r))

    // Piece-level Fix escalation: each failed chunk still has its own oracle.
    for (let round = 1; round <= FIXROUNDS; round++) {
      const failed = levelPieces.filter((p) => (results.get(p.id) || {}).authored !== 'yes')
      if (failed.length === 0) break
      log(`Fix round ${round} (level ${L}): escalating ${failed.map((p) => p.id).join(', ')} to ${FIX_MODEL}.`)
      const fixRows = await parallel(failed.map((p) => () =>
        agent(authorPrompt(p, (results.get(p.id) || {}).notes || 'no row returned'), {
          label: `fix:${p.id}`, phase: 'Fix', schema: PIECE_SCHEMA, model: FIX_MODEL,
        })
      ))
      fixRows.filter(Boolean).forEach((r) => results.set(r.piece, r))
    }

    const stillFailed = levelPieces.filter((p) => (results.get(p.id) || {}).authored !== 'yes')
    if (stillFailed.length) {
      log(`Level ${L} has unfixable chunk(s): ${stillFailed.map((p) => p.id).join(', ')} — aborting before dependents author against broken fragments.`)
      return {
        status: 'FAILED', stage: 'author', level: L, amplitude: AMPLITUDE, triage: tri,
        failedPieces: stillFailed.map((p) => ({ id: p.id, notes: (results.get(p.id) || {}).notes })),
        plan, authored: [...results.values()],
      }
    }
    log(`Level ${L} frozen (worst chunk error: ${levelPieces.map((p) => (results.get(p.id) || {}).worstRelErr).filter(Boolean).join(', ') || 'n/a'}).`)
  }

  // Assemble: Params + kernel header + dispatch (serial)
  phase('Assemble')
  log('Assembling the kernel header from the frozen fragments...')

  const allGlobals = [...new Set([...results.values()].flatMap((r) => r.globals || []).concat(plan.paramsFields || []))]

  asm = await agent(
    `You are the serial ASSEMBLE phase of the stage-2 Kokkos port of "${NAME}" — you alone own the shared
kernel files. Work from ${PROJECT}; prefix env-dependent commands with \`${SRCENV} && <cmd>\`.
READ ${PROJECT}/${SPEC} first — §2.3/§2.4 (kernel infrastructure + signatures), §3, §7, §8.
${SCOPENOTE}

The frozen, individually-validated fragments are in ${PARTSDIR}/ :
${toPort.map((p) => `  - ${p.id}.h (oracle ${p.oracle}${(results.get(p.id) || {}).worstRelErr ? `, frozen at ${(results.get(p.id) || {}).worstRelErr}` : ''})`).join('\n')}
${reused.length ? `Reused prior kernels: ${reused.map((r) => r.reuse).join(', ')}\n` : ''}
Globals reported by the chunks (union) → Params fields: ${allGlobals.join(', ') || '(none)'}

Write, per §2.4:
1. \$PEPPER_HOME/src/mcfm_analytics/${NAME}_kernel.h — header comment includes the provenance line
   \`// MCFM sources: <the assembly file(s) this header itself ports>\` (fragments carry their own); includes
   the fragments; the POD Params struct (nest the Born struct if this is a virtual; fields from the union
   above + §2.5 couplings); the pure \`double ${NAME}_me2(double p[${plan.nParticles || 'N'}][4], const ...Params&)\`
   preserving the MCFM assembly structure (§3 last rule); the \`template <typename event_data>\` dispatch
   kernel reading evt.e/px/py/pz(i,part) directly (NO sign flip, G1), dead-event guard (G8), writing evt.me2(i).
2. The one-line TU \$PEPPER_HOME/src/mcfm_analytics/${NAME}_kernel.cpp.
3. Smoke-compile through the shim: a minimal main() calling ${NAME}_me2 once, built with
   \`${TEMPLATES}/run_validation.sh <scratch>.cpp\` — fix compile errors in the ASSEMBLY layer only
   (fragments are frozen; if a fragment itself cannot compile, report it in notes instead of editing it).

Do NOT wire CMake or doctests (Test phase does), and do NOT run the numerical validation loop (next phase).
Return written=true, the files, and the Params fields as written.`,
    { label: 'assemble', phase: 'Assemble', schema: ASSEMBLE_SCHEMA, model: ASSEMBLE_MODEL }
  )

  if (!asm || !asm.written) {
    log('Assembly failed; aborting.')
    return { status: 'FAILED', stage: 'assemble', amplitude: AMPLITUDE, triage: tri, plan, authored: [...results.values()], assemble: asm }
  }
  authoredRows = [...results.values()]
}

// ---------------------------------------------------------------------------
// Validate — nested full-ME validate↔fix loop (Spec §4). Shared by both paths.
// If pieces pass but the full ME disagrees, the bug is in the assembly layer (§7).
// ---------------------------------------------------------------------------
phase('Validate')
log('Full-ME equivalence vs libmcfm (nested validate↔fix loop)...')

const val = await workflow('kokkos-validate-loop', {
  amplitude: NAME, projectRoot: PROJECT, maxFixes: MAXFIXES, tol: TOL, scopeNote: cfg.scopeNote || '',
})

if (!val || val.status !== 'PASSED') {
  log(`Full-ME validation did not converge (${val ? val.reason : 'no result'}). Pieces are frozen/validated — the defect is in the assembly layer or a piece-boundary contract.`)
  return {
    status: 'FAILED', stage: 'validate', amplitude: AMPLITUDE, triage: tri,
    plan, authored: authoredRows, assemble: asm, validation: val,
  }
}
log(`Kernel matches libmcfm (maxRelErr=${val.maxRelErr}, fixes=${val.fixes}).`)

// ---------------------------------------------------------------------------
// Test — doctests + CMake + pepper_test (shared by both paths)
// ---------------------------------------------------------------------------
phase('Test')
log('Adding doctests, wiring CMake, building pepper_test...')

const test = await agent(
  `The Kokkos kernel for "${NAME}" now matches libmcfm (maxRelErr=${val.maxRelErr}). Finish the port per
${PROJECT}/${SPEC} §4 (step 5). Work from ${PROJECT}; prefix env-dependent commands with \`${SRCENV} && <cmd>\`.
${SCOPENOTE}

1. Add layered DOCTEST_TEST_CASEs to \$PEPPER_HOME/tests/unit_tests/matrix_elements.cpp mirroring the
   existing "MCFM-analytics" cases: loop functions / key sub-amplitude pieces first (tol 1e-10), then the
   full ${NAME}_me2 on the fixed point against the hardcoded MCFM reference printed by the validator
   (tol 1e-10 for 4-particle, 1e-9 for 5-particle finals; §5-budgeted pieces keep their justified tolerance).
   Test BOTH energy conventions for the full ME where they differ (§2.2).
2. Register ${NAME}_kernel.h + ${NAME}_kernel.cpp in \$PEPPER_HOME/src/CMakeLists.txt (PEPPER_LIB_SOURCES).
   Fragments in ${NAME}_parts/ (if any) are plain headers — do NOT register them.
3. Build and run: \`cmake --build \$PEPPER_HOME/build --target pepper_test -j\` then
   \`\$PEPPER_HOME/build/tests/unit_tests/pepper_test --dt-test-case="*${NAME}*"\` (and re-run the full
   "*MCFM*" filter to prove no regression in the existing kernels).

Return status PASSED only if the new doctests AND the pre-existing MCFM cases all pass.`,
  { label: 'test', phase: 'Test', schema: TEST_SCHEMA, model: TEST_MODEL }
)

const status = test && test.status === 'PASSED' ? 'VERIFIED' : 'FAILED'
log(`Run complete: ${status} — path=${DIRECT ? 'direct' : 'split'}, full ME at ${val.maxRelErr}, doctests ${test ? test.status : 'n/a'}.`)

return {
  status, amplitude: AMPLITUDE, kernelName: NAME, path: DIRECT ? 'direct' : 'split',
  models: { triage: TRIAGE_MODEL, split: SPLIT_MODEL, author: AUTHOR_MODEL, direct: DIRECT_MODEL, loop: LOOP_MODEL, fix: FIX_MODEL, assemble: ASSEMBLE_MODEL, test: TEST_MODEL },
  triage: tri, plan, authored: authoredRows, assemble: asm,
  validation: { maxRelErr: val.maxRelErr, fixes: val.fixes },
  test,
}

} // end portOne

// ---------------------------------------------------------------------------
// Driver — single amplitude, or a sequential batch (dependency order so an
// earlier amplitude's frozen fragments are on disk for a later one to reuse).
// ---------------------------------------------------------------------------
if (AMPLITUDES.length === 1) {
  return await portOne(AMPLITUDES[0])
}

log(`Batch: ${AMPLITUDES.length} amplitude(s), sequential in dependency order — ${AMPLITUDES.join(', ')}.`)
const results = []
let idx = 0
for (const amp of AMPLITUDES) {
  idx++
  log(`── Amplitude ${idx}/${AMPLITUDES.length}: ${amp} ──`)
  const r = await portOne(amp)
  results.push(r)
  if (!r || r.status !== 'VERIFIED') {
    log(`WARNING: ${amp} ended ${r ? r.status : 'no-result'} — later amplitudes that reuse its fragments may fail.`)
  }
}
const nVerified = results.filter((r) => r && r.status === 'VERIFIED').length
log(`Batch complete: ${nVerified}/${results.length} verified.`)
return { batch: true, amplitudes: AMPLITUDES, verified: nVerified, results }
