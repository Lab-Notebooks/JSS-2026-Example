// ═══════════════════════════════════════════════════════════════════════════════
// Workflow : mcfm-translate  (stage 1: Fortran → C++)
// Purpose  : Translate one dependency-graph leaf layer of MCFM Fortran files to
//            C++ — author in parallel, build + verify serially — guided by the
//            shared Spec dev/fortran-to-cpp/desired_spec.md. Single-pass: it
//            translates the layer end-to-end (resolve → author → integrate → fix)
//            and stops; there is no preview mode.
//
//            This is the Claude Code orchestrator of the paper's head-to-head
//            (§4.3, Fig. 4). It reads the SAME shared inputs as the CodeScribe
//            loop (dev/fortran-to-cpp/) and answers to the SAME verification bar
//            (desired_spec.md §6, the coverage probe).
//
//   Two structural choices realize the paper's §5.5:
//     - Authoring is PARALLEL, integration is SERIAL. Many author subagents each
//       write only their own outputs; a single serial integrator owns the shared
//       build state and is the verification trust anchor.
//     - Authoring is SIZE-GATED. Ordinary files go to a lighter model in parallel;
//       a big file (> bigLoc) is escalated to a stronger author model.
//
// Inputs   : args.projectRoot — absolute path to the lab-notebook root (REQUIRED;
//                               the agents source <root>/environment.sh by abs path)
//            args.resolver    — 'graph' (dependency-graph driven) | 'list' (portable)
//            args.scope       — a top-level src/ dir (e.g. 'ThreeJets') or 'all'
//            args.files       — list mode: explicit src-relative paths
//            args.maxFiles    — cap one run (default 12; remainder logged, deferred)
//            args.bigLoc      — a .f over this many lines uses the stronger model (400)
//            args.fixRounds   — Opus re-author rounds over FAILED files (default 1)
//            args.model / args.{resolve,author,authorBig,integrate,fix}Model
// Outputs  : { toRecord: { verified, translated, failed }, ... } to record in the Plan
// ═══════════════════════════════════════════════════════════════════════════════

export const meta = {
  name: 'mcfm-translate',
  description: 'Translate one dependency-graph leaf layer of MCFM Fortran files to C++ (author in parallel, build+verify serially), guided by dev/fortran-to-cpp/desired_spec.md. The Claude Code orchestrator for the stage-1 head-to-head.',
  whenToUse: 'Batch Fortran->C++ translation of MCFM. Pass {projectRoot, resolver, scope, ...} as args and it translates end-to-end (resolve -> author in parallel -> integrate+benchmark -> fix). graph mode picks the next conflict-free leaf layer; list mode translates an explicit file list. Big files (>bigLoc) route to a stronger author model.',
  phases: [
    { title: 'Index', model: 'haiku' },
    { title: 'Resolve', model: 'haiku' },
    { title: 'Author', model: 'sonnet' },
    { title: 'Integrate', model: 'opus' },
    { title: 'Fix', model: 'opus' },
  ],
}

// Staged pipeline (paper §4.2), realizing the reference multi-stage translation:
//   Index    — Doxygen call graph -> dependency ranking + symbol map (tools/build_roadmap.py)
//   Resolve  — pick the next conflict-free leaf layer from the graph
//   Author   — per file: Draft (tools/scribe_draft.py) then Translate against the
//              Spec + the few-shot seed examples; author-parallel
//   Integrate— serial: rewire CMake, build once, verify + coverage-probe
//   Fix      — escalate FAILED files to a stronger model

// ---------------------------------------------------------------------------
// Config (all overridable via the Workflow `args` object)
// ---------------------------------------------------------------------------
const cfg = typeof args === 'string' ? JSON.parse(args) : (args || {})
const PROJECT = cfg.projectRoot
if (!PROJECT) {
  throw new Error('args.projectRoot (absolute path to the lab-notebook root) is required — the agents source <root>/environment.sh by absolute path')
}
const RESOLVER = cfg.resolver || 'graph'        // 'graph' (dependency-graph driven) | 'list' (portable)
const SCOPE    = cfg.scope || 'all'             // a top-level src/ dir (e.g. 'ThreeJets') or 'all'
const MAXFILES = cfg.maxFiles || 12             // bound one run; layer remainder is logged, never silently dropped
const FILES    = cfg.files || []                // list mode: explicit src-relative paths
const BIGLOC   = cfg.bigLoc ?? 400              // a .f over this many lines is authored by the stronger model
const FIXROUNDS = cfg.fixRounds ?? 1            // Opus re-author rounds over FAILED files before giving up

// Per-phase models. Resolve is mechanical (Haiku); Author scales N-wide so small
// files sit at Sonnet with the coverage probe as the safety net, while a BIG file
// (> BIGLOC loc) is routed to the stronger author model; Integrate is one serial
// agent and the verification trust anchor, so it runs on Opus; Fix escalates
// FAILED files to Opus. `args.model` forces all phases to one model.
const INDEX_MODEL      = cfg.model || cfg.indexModel      || 'haiku'
const RESOLVE_MODEL    = cfg.model || cfg.resolveModel    || 'haiku'
const AUTHOR_MODEL     = cfg.model || cfg.authorModel     || 'sonnet'
const AUTHOR_BIG_MODEL = cfg.model || cfg.authorBigModel  || 'opus'
const INTEGRATE_MODEL  = cfg.model || cfg.integrateModel  || 'opus'
const FIX_MODEL        = cfg.model || cfg.fixModel        || 'opus'

const SPEC = 'dev/fortran-to-cpp/desired_spec.md'      // the Spec (translation rules + verification bar)
const SEED = 'dev/fortran-to-cpp/seed_examples.toml'   // few-shot chat-template worked examples
const SRCENV = `source ${PROJECT}/environment.sh`

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------
const RESOLVE_SCHEMA = {
  type: 'object',
  properties: {
    ready: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file:  { type: 'string', description: 'path relative to $MCFM_HOME/src, e.g. ThreeJets/A5gfill.f' },
          dir:   { type: 'string', description: 'top-level src/ directory' },
          bench: { type: 'string', description: "./test -b process for that dir, or '' if none" },
          fanin: { type: 'integer', description: 'how many untranslated files call this one (translate-early signal)' },
          loc:   { type: 'integer', description: 'line count of the .f (wc -l); drives the big-file model bump' },
          subs:  { type: 'integer', description: 'number of subroutine/function definitions in the file (>1 on a big file = split candidate)' },
        },
        required: ['file', 'dir', 'bench'],
      },
    },
    blind: {
      type: 'array',
      description: 'deps==0 but graph-blind (unknown edges) — excluded from auto-translation, surfaced for manual review',
      items: { type: 'object', properties: { file: { type: 'string' }, dir: { type: 'string' } }, required: ['file'] },
    },
    layerSize: { type: 'integer', description: 'total ready leaves in scope BEFORE the MAXFILES cap' },
    note: { type: 'string' },
  },
  required: ['ready', 'layerSize'],
}

const AUTHOR_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    authored: { type: 'string', enum: ['yes', 'deferred', 'failed'] },
    deps_ok: { type: 'boolean' },
    notes: { type: 'string', description: 'missing shared constant, deferral/failure reason, or suspected mistranslation' },
  },
  required: ['file', 'authored'],
}

const INTEGRATE_SCHEMA = {
  type: 'object',
  properties: {
    buildOk: { type: 'boolean' },
    rows: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          built: { type: 'boolean' },
          linked: { type: 'boolean' },
          benchmark: { type: 'string', description: 'PASSED / FAILED / n-a, with the process' },
          probe: { type: 'string', description: 'exercised / unchanged / n-a' },
          status: { type: 'string', enum: ['VERIFIED', 'TRANSLATED', 'FAILED'] },
          maxdev: { type: 'string', description: 'largest ratio deviation, e.g. 3e-16' },
          escalated: { type: 'boolean', description: 'true if this file needs human adjudication (P2 / human-effort metric)' },
          notes: { type: 'string' },
        },
        required: ['file', 'status'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['buildOk', 'rows'],
}

// ---------------------------------------------------------------------------
// Phase 1 — Index: Doxygen call graph -> dependency ranking + symbol map.
// Indexing is Doxygen-based (the reference collaborator used Doxygen, not a regex
// symbol scan). One command emits both the leaf-ranking TSV and the symbol->file
// map the Draft step consumes.
// ---------------------------------------------------------------------------
if (RESOLVER === 'graph') {
  phase('Index')
  await agent(
    `You are the INDEX phase of the MCFM translation workflow. Work from ${PROJECT}; prefix env-dependent
commands with \`${SRCENV} && <cmd>\`. Run the Doxygen-based index once:
  \`${SRCENV} && cd ${PROJECT} && python3 tools/build_roadmap.py\`
This re-reads the Doxygen XML call graph (software/mcfm/doxygen_dep/xml) and writes
tools/assets/roadmap_metrics.tsv (per-file deps/blind/fanin/bench), tools/assets/roadmap.md, and
tools/assets/symbol_index.json (symbol -> defining file, used by the Draft step). Confirm the three files
exist and report the counts printed. Do not author or translate anything.`,
    { label: 'index', phase: 'Index', model: INDEX_MODEL, effort: 'low' }
  )
}

// ---------------------------------------------------------------------------
// Phase 2 — Resolve: pick this run's leaf layer
// ---------------------------------------------------------------------------
phase('Resolve')

const resolvePrompt = RESOLVER === 'graph'
  ? `You are the RESOLVE phase of an MCFM translation workflow. Work from the project root (${PROJECT}).
The Bash tool persists cwd but resets env between calls, so prefix env-dependent commands with: \`${SRCENV} && <cmd>\`.

The dependency graph was just refreshed by the Index phase — read it, do not reason about dependencies yourself.

1. The Index phase already ran \`python3 tools/build_roadmap.py\`, so tools/assets/roadmap_metrics.tsv is
   current ('deps' = number of still-untranslated callees; 'translated' = a .cpp OR .hpp sibling exists).

2. Emit the ready leaf layer from tools/assets/roadmap_metrics.tsv with a single awk (columns include blind, deps, bench).
   A READY leaf = deps==0 AND blind==0 (no untranslated callees, edges known). Restrict to scope ${SCOPE === 'all' ? '(no dir filter — all dirs)' : `(top == "${SCOPE}")`}.
   Example:
   \`awk -F'\\t' 'NR==1{for(i=1;i<=NF;i++)h[$i]=i;next} $(h["deps"])==0 && $(h["blind"])==0 ${SCOPE === 'all' ? '' : `&& $(h["top"])=="${SCOPE}"`} {print $(h["rel"])"\\t"$(h["top"])"\\t"$(h["fanin"])"\\t"$(h["bench"])}' tools/assets/roadmap_metrics.tsv | sort -t$'\\t' -k3,3nr\`
   (sorted by fanin descending so high-leverage files come first).

3. Also collect blind leaves (deps==0 && blind==1) in scope — these have UNKNOWN edges so deps==0 is not trustworthy; report them for manual handling, do NOT include them in 'ready'.

4. Skip any file whose .cpp already exists under \$MCFM_HOME/src (already translated). Cap 'ready' to the first ${MAXFILES} rows but report the true total in 'layerSize'.

5. For each row you keep in 'ready', set 'loc' to its line count (\`wc -l \$MCFM_HOME/src/<file>\`) and 'subs'
   to its subroutine/function definition count, netting out the END statements:
   \`f=\$MCFM_HOME/src/<file>; echo \$(( \$(grep -icE '^[[:space:]]*([a-z0-9_*() ]+ )?(subroutine|function) ' "\$f") - \$(grep -icE '^[[:space:]]*end (subroutine|function)' "\$f") ))\`
   'loc' drives a model bump for big files downstream; 'subs' flags whether a big file could be split by subroutine.

Return ONLY the structured object. Do not author or build anything.`
  : `You are the RESOLVE phase (LIST mode — no dependency graph) of an MCFM translation workflow. Work from ${PROJECT}; prefix env-dependent commands with \`${SRCENV} && <cmd>\`.

The caller passed an explicit file list (relative to \$MCFM_HOME/src): ${JSON.stringify(FILES)}.
For each: confirm the .f exists and its .cpp does NOT already exist; derive 'dir' (top-level src/ subdir) and 'bench' from the directory->benchmark table in ${SPEC} §5, set 'loc' to \`wc -l\` of the .f, and set 'subs' to its subroutine/function definition count netting out the ENDs (\`echo \$(( \$(grep -icE '^[[:space:]]*([a-z0-9_*() ]+ )?(subroutine|function) ' "\$f") - \$(grep -icE '^[[:space:]]*end (subroutine|function)' "\$f") ))\`). Drop any already-translated or missing file (note it). Cap to ${MAXFILES}; set layerSize to the count you were given. Return ONLY the structured object.`

const resolved = await agent(resolvePrompt, { label: 'resolve', phase: 'Resolve', schema: RESOLVE_SCHEMA, model: RESOLVE_MODEL })

if (!resolved || !resolved.ready || resolved.ready.length === 0) {
  log('Resolve found no ready files. Nothing to translate this run.')
  return { resolved, ready: [], authored: [], integrated: null }
}

log(`Layer: ${resolved.layerSize} ready leaf(s) in scope "${SCOPE}"; taking ${resolved.ready.length} this run` +
    (resolved.layerSize > resolved.ready.length ? ` (${resolved.layerSize - resolved.ready.length} deferred to next run — raise maxFiles to widen).` : '.') +
    (resolved.blind && resolved.blind.length ? ` ${resolved.blind.length} graph-blind file(s) skipped for manual review.` : ''))

// ---------------------------------------------------------------------------
// Phase 2 — Author: translate each file in parallel (writes ONLY its own outputs).
// A file over BIGLOC lines is routed to the stronger author model instead of being
// chunked (in this tree every big file is a single monolithic subroutine).
// ---------------------------------------------------------------------------
phase('Author')

const bigFiles = resolved.ready.filter((f) => (f.loc || 0) > BIGLOC)
if (bigFiles.length) {
  log(`${bigFiles.length} big file(s) (>${BIGLOC} loc) routed to ${AUTHOR_BIG_MODEL}: ${bigFiles.map((f) => `${f.file}(${f.loc}L,${f.subs ?? '?'}sub)`).join(', ')}.`)
  // Split-candidate signal: a big file with >1 subroutine could be split by
  // subroutine (clean boundaries) instead of the model bump. Logged, not built.
  const splitCandidates = bigFiles.filter((f) => (f.subs || 0) > 1)
  if (splitCandidates.length) {
    log(`SPLIT CANDIDATE: ${splitCandidates.map((f) => `${f.file} (${f.subs} subroutines, ${f.loc} loc)`).join('; ')} — big AND multi-subroutine, so a per-subroutine split is worth building. Handled by the ${AUTHOR_BIG_MODEL} bump for this run.`)
  }
}

const authorPrompt = (f) => `You are an AUTHOR-ONLY agent translating one MCFM Fortran file to C++. Work inside \$MCFM_HOME.
Prefix every env-dependent command with \`${SRCENV} && <cmd>\` (the Bash tool resets env between calls).

Your file: \`${f.file}\` (directory ${f.dir}).

TRANSLATE MECHANISM (Draft -> Translate, replicated from the reference multi-stage path):
- First generate the machine draft:
  \`${SRCENV} && cd ${PROJECT} && python3 tools/scribe_draft.py \$MCFM_HOME/src/${f.file} --force\`
  This writes \`\$MCFM_HOME/src/${f.file.replace(/\.[^.]+$/, '')}.scribe\`: scribe-prompt hints (which called
  constructs are external functions, which are array/statement functions) plus a mechanical first-cut
  conversion. It is SCAFFOLDING, not the answer — read it for the hints, then write the real translation.
- Consult ${PROJECT}/${SEED} for the worked-example format (the <cheader>/<csource>/<fsource> shape, FArray and
  wrapper conventions). The final files you write are real C++/Fortran, not the tagged chat format.

READ ${PROJECT}/${SPEC} FIRST and follow it. In particular:
- §1 picks which output files to produce (general convention: <base>.cpp + <base>.hpp + <base>_fi.F90;
  the src/gghgg_dep precision-split convention is different — <base>.cpp + fixed-form <base>_fi.f, no .hpp).
- §2 + §3 are the translation rules and worked examples. Translate the body line-by-line; do NOT invent any
  symbol the source does not define (§2 rule 9a — keep every \`call\`, fabricate nothing).
- §4 is the self-review checklist — apply EVERY item before you finish (self-header includes B1, Need.hpp B2,
  dimension(*) in the bind(C) block A1, cross-file call ABI 9a, the silent dropped-call trap C and
  precedence E1 traps, the gghgg_dep recipe I). Model structure on a verified sibling in ${f.dir}.

Hard constraints (you are author-only):
- Write ONLY this file's translation outputs. Do NOT build, NOT run cmake/make, NOT edit any CMakeLists.txt,
  and NOT edit any shared header. The serial integrator does all of that.
- If a dependency you call is NOT yet a .cpp on disk, do NOT author against it — set authored="deferred" with
  the reason (the graph should have prevented this, but guard anyway).
- If a needed shared constant is missing, report it in notes (the integrator adds it once); use an inline
  literal meanwhile. Do NOT create/modify the shared header.

Return ONE structured row. Do NOT paste file contents.`

const authored = await parallel(
  resolved.ready.map((f) => () =>
    agent(authorPrompt(f), {
      label: `author:${f.file}`, phase: 'Author', schema: AUTHOR_SCHEMA,
      model: (f.loc || 0) > BIGLOC ? AUTHOR_BIG_MODEL : AUTHOR_MODEL,
    })
  )
)

const ok = authored.filter(Boolean).filter((r) => r.authored === 'yes')
const notOk = authored.filter(Boolean).filter((r) => r.authored !== 'yes')
log(`Authored ${ok.length}/${resolved.ready.length}.` + (notOk.length ? ` ${notOk.length} deferred/failed.` : ''))

if (ok.length === 0) {
  log('No files authored successfully; skipping integrate.')
  return { resolved, authored, integrated: null }
}

// ---------------------------------------------------------------------------
// Phase 3 — Integrate: rewire CMake, ONE build, verify + coverage-probe (serial)
// ---------------------------------------------------------------------------
phase('Integrate')

const okFiles = ok.map((r) => r.file)
const benchesFor = (files) => [...new Set(resolved.ready.filter((f) => files.includes(f.file) && f.bench).map((f) => f.bench))]
const missingConsts = authored.filter(Boolean).map((r) => r.notes).filter(Boolean)

const integratePrompt = (files, benchList, consts) => `You are the SERIAL INTEGRATE phase. You alone own the
shared build tree, the CMakeLists files, and the shared headers — no other agent is running. Work inside
\$MCFM_HOME; prefix env-dependent commands with \`${SRCENV} && <cmd>\`. Follow ${PROJECT}/${SPEC} §4 (fixups),
§5 (benchmarks), and §6 (verification + the MANDATORY coverage probe). §6 is the verification bar —
apply it exactly; never grant VERIFIED without the coverage probe firing.

Files to integrate (already written to disk):
${files.map((f) => `  - ${f}`).join('\n')}

Benchmark processes to run (distinct): ${benchList.length ? benchList.map((b) => `\`${b}\``).join(', ') : '(none — infrastructure files, mark TRANSLATED)'}
Shared constants reported missing (add once): ${consts.length ? JSON.stringify(consts) : '(none)'}

Do, in order:
1. Add any reported missing shared constants to the shared header (e.g. gghgg_consts.hpp) — once, here.
2. For each file, rewire <dir>/CMakeLists.txt: replace the <name>.f (or .f90) line in target_sources with the
   interface+impl lines (<name>_fi.F90 + <name>.cpp; for gghgg_dep, <name>_fi.f + <name>.cpp). Remove any stale
   object \$MCFM_HOME/Bin/CMakeFiles/objlib.dir/src/<dir>/<name>.f.o.
3. Build ONCE: \`${SRCENV} && cd \$MCFM_HOME/Bin && cmake . >/dev/null && make install 2>&1 | tail -40\`. Fix
   obvious compile issues (missing include, namespace, B3 cross-dir include path). If the amplitude algebra
   itself looks mistranslated, do NOT guess — mark that ONE file FAILED with the symptom and set escalated=true;
   one bad file must not block the batch.
4. Verify: per distinct benchmark process, \`./test -b <process>\`; record the four ratios (Finite/IR/IR2/Born)
   and PASSED/FAILED. Confirm linkage with \`nm libmcfm.* | grep -i <name>\` (expect _<name>_wrapper).
5. Coverage probe (MANDATORY, §6) — the check that the benchmark ACTUALLY exercises the file, so do it
   rigorously and make it auditable. For each file whose dir has a benchmark: scale its main amplitude output
   by 1.5, single-file relink, re-run, and RECORD the actual ratio movement in the row's 'probe' field, e.g.
   "exercised (Finite 1.0->0.37)" or "unchanged (all 4 ratios identical)".
   - Ratios BREAK far beyond 1e-13 -> file is exercised -> revert the 1.5x, rebuild to confirm PASS, status
     VERIFIED. You may ONLY mark VERIFIED when you observed the probe move a ratio.
   - Ratios UNCHANGED -> status TRANSLATED (it may read off-path until its caller lands, §4.H).
   ALWAYS revert every probe edit; leave the tree building clean and passing. Files with no benchmark are
   TRANSLATED (unverified).

Return the compact status table only (one row per file), with the probe movement in 'probe', the largest
ratio deviation in 'maxdev', and escalated=true on any file that needs human adjudication. No file contents,
no full build logs.`

let integrated = await agent(
  integratePrompt(okFiles, benchesFor(okFiles), missingConsts),
  { label: 'integrate', phase: 'Integrate', schema: INTEGRATE_SCHEMA, model: INTEGRATE_MODEL }
)

// ---------------------------------------------------------------------------
// Phase 4 — Fix: escalate FAILED files to a stronger model, then re-integrate (serial)
// ---------------------------------------------------------------------------
const fixAuthored = []
for (let round = 1; round <= FIXROUNDS; round++) {
  const failedRows = (integrated?.rows || []).filter((r) => r.status === 'FAILED')
  if (failedRows.length === 0) break
  phase('Fix')
  log(`Fix round ${round}: escalating ${failedRows.length} FAILED file(s) to ${FIX_MODEL}.`)

  const fixPrompt = (r) => `You are a FIX agent repairing ONE MCFM translation the integrate phase marked
FAILED. File: \`${r.file}\`. Integrate's symptom: ${r.notes || r.benchmark || '(compile/link or benchmark failure — diagnose from the source)'}.
Work inside \$MCFM_HOME; prefix env-dependent commands with \`${SRCENV} && <cmd>\`. READ ${PROJECT}/${SPEC} first.

Diagnose and repair this file's translation outputs (its .cpp / .hpp / _fi shim — you MAY edit them). Focus on
the §4 traps most likely behind the symptom: dropped call (§4.C), operator precedence (§4.E1), FArray layout
(§4.D2) / 0-based loop over 1-based FArray (§4.F2b), missing/Need includes (§4.B1/B2), the bind(C) dimension(*)
rule (§4.A1). Compare against a verified sibling in the same directory.

Constraints (preserve the build-serial invariant):
- Do NOT run cmake / make / make install and do NOT edit any CMakeLists.txt or shared header — the re-integrate
  step rebuilds and verifies serially. Reason from the symptom, the source, and sibling files.
- If the file genuinely cannot be translated yet (it needs an untranslated dependency), set authored="deferred"
  with the reason rather than guessing.

Return ONE row: file | authored(yes/deferred/failed) | deps_ok | notes (what you changed and why).`

  const repaired = (await parallel(
    failedRows.map((r) => () => agent(fixPrompt(r), { label: `fix:${r.file}`, phase: 'Fix', schema: AUTHOR_SCHEMA, model: FIX_MODEL }))
  )).filter(Boolean)
  fixAuthored.push(...repaired)

  const refixFiles = repaired.filter((a) => a.authored === 'yes').map((a) => a.file)
  if (refixFiles.length === 0) { log('Fix produced no repaired files; ending escalation.'); break }

  const reInt = await agent(
    integratePrompt(refixFiles, benchesFor(refixFiles), []),
    { label: `re-integrate:r${round}`, phase: 'Integrate', schema: INTEGRATE_SCHEMA, model: INTEGRATE_MODEL }
  )
  // Merge: re-integrated rows overwrite the prior (FAILED) rows for those files.
  const byFile = new Map((integrated?.rows || []).map((r) => [r.file, r]))
  for (const r of (reInt?.rows || [])) byFile.set(r.file, r)
  integrated = {
    buildOk: reInt?.buildOk ?? integrated?.buildOk,
    rows: [...byFile.values()],
    summary: `${integrated?.summary || ''} | fix r${round}: ${reInt?.summary || ''}`,
  }
}

// ---------------------------------------------------------------------------
// Return everything for the main loop to record into the Plan (current_plan.md)
// ---------------------------------------------------------------------------
const verified = (integrated?.rows || []).filter((r) => r.status === 'VERIFIED')
const translated = (integrated?.rows || []).filter((r) => r.status === 'TRANSLATED')
const failed = (integrated?.rows || []).filter((r) => r.status === 'FAILED')
log(`Run complete: ${verified.length} verified, ${translated.length} translated, ${failed.length} failed. Build ${integrated?.buildOk ? 'clean' : 'NOT clean'}.`)

return {
  resolver: RESOLVER,
  scope: SCOPE,
  models: { resolve: RESOLVE_MODEL, author: AUTHOR_MODEL, authorBig: AUTHOR_BIG_MODEL, integrate: INTEGRATE_MODEL, fix: FIX_MODEL },
  layerSize: resolved.layerSize,
  blind: resolved.blind || [],
  authored,
  fixAuthored,
  integrated,
  toRecord: { verified, translated, failed },
}
