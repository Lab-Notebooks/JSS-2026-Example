// Workflow: mcfm-translate — stage 1, Fortran → C++.
//
// A Claude Code orchestrator. It reads the shared Spec
// (dev/transformations/fortran-to-cpp/desired_spec.md) and answers to its
// verification bar. The prompts stay short and point at the Spec rather than
// restating it.
//
// The pipeline is five phases; two of them carry the structural lessons worth study:
//   Index      deterministic — build the dependency graph (a tool, not a model call)
//   Resolve    deterministic — pick the next leaf layer (files with no untranslated deps)
//   Author     PARALLEL, and SIZE-GATED: a big file goes to a stronger model
//   Integrate  SERIAL — one agent owns the build and is the verification trust anchor
//   Fix        escalate FAILED files to a stronger model, then re-integrate
//
// The workflow is independent of the transformation it drives: it takes the
// transformation directory as an argument and reads the Spec from there, so it is
// invoked as "Run mcfm-translate for dev/transformations/<transformation>". The
// default matches its stage; any directory following the same stage-1 contract works.
//
// Config (args): projectRoot (required, absolute), transformation (dir under
//                dev/transformations/, default 'fortran-to-cpp'), scope (a src/ dir,
//                default 'all'), maxFiles (cap one run, 12), bigLoc (model gate, 400).

export const meta = {
  name: 'mcfm-translate',
  description: 'Stage-1 Fortran → C++ translation of one dependency-graph leaf layer: author in parallel, build and verify serially, guided by the shared Spec.',
  whenToUse: 'Run mcfm-translate for dev/transformations/<transformation>. args:{projectRoot, transformation, scope}. Resolves the next conflict-free leaf layer and translates it end-to-end.',
  phases: [
    { title: 'Index',     model: 'haiku'  },
    { title: 'Resolve',   model: 'haiku'  },
    { title: 'Author',    model: 'sonnet' },
    { title: 'Integrate', model: 'opus'   },
    { title: 'Fix',       model: 'opus'   },
  ],
}

const cfg = typeof args === 'string' ? JSON.parse(args) : (args || {})
const PROJECT = cfg.projectRoot
if (!PROJECT) throw new Error('args.projectRoot (absolute path to the lab-notebook root) is required')
const SCOPE    = cfg.scope    || 'all'
const MAXFILES = cfg.maxFiles || 12
const BIGLOC   = cfg.bigLoc   ?? 400

// The transformation is a parameter, not a hard-coded path. Accept either a bare
// name ('fortran-to-cpp') or a full 'dev/transformations/<name>' directory.
const TRANSFORMATION = (cfg.transformation || 'fortran-to-cpp').replace(/^dev\/transformations\//, '').replace(/\/$/, '')
const SPEC = `dev/transformations/${TRANSFORMATION}/desired_spec.md`
const ENV  = `source ${PROJECT}/environment.sh`   // Bash resets env between calls; prefix env-dependent commands

const RESOLVE_SCHEMA = {
  type: 'object',
  properties: {
    ready: { type: 'array', items: { type: 'object', properties: {
      file:  { type: 'string', description: 'path relative to $MCFM_HOME/src' },
      dir:   { type: 'string', description: 'top-level src/ directory' },
      bench: { type: 'string', description: './test -b process for that dir, or ""' },
      loc:   { type: 'integer', description: 'line count; drives the big-file model gate' },
    }, required: ['file', 'dir', 'bench'] } },
    layerSize: { type: 'integer', description: 'total ready leaves before the maxFiles cap' },
  },
  required: ['ready', 'layerSize'],
}
const AUTHOR_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    authored: { type: 'string', enum: ['yes', 'deferred', 'failed'] },
    notes: { type: 'string', description: 'missing shared constant, deferral reason, or suspected mistranslation' },
  },
  required: ['file', 'authored'],
}
const INTEGRATE_SCHEMA = {
  type: 'object',
  properties: {
    buildOk: { type: 'boolean' },
    rows: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' },
      status: { type: 'string', enum: ['VERIFIED', 'TRANSLATED', 'FAILED'] },
      probe: { type: 'string', description: 'exercised / unchanged / n-a (the coverage probe result)' },
      escalated: { type: 'boolean', description: 'true if this file needs human adjudication' },
      notes: { type: 'string' },
    }, required: ['file', 'status'] } },
  },
  required: ['buildOk', 'rows'],
}

// Index — build the dependency graph. Deterministic: a tool, not a model call.
phase('Index')
await agent(
  `Run the Index tool once, then confirm its outputs exist:
   \`${ENV} && cd ${PROJECT} && python3 dev/tools/index/build_roadmap.py\`
It writes dev/tools/assets/roadmap_metrics.tsv (per-file deps + bench) and symbol_index.json.
Report the counts printed. Do not translate anything.`,
  { label: 'index', phase: 'Index', effort: 'low' }
)

// Resolve — pick this run's leaf layer from the graph the Index just built.
phase('Resolve')
const resolved = await agent(
  `From dev/tools/assets/roadmap_metrics.tsv pick the READY leaf layer: rows with deps==0 and blind==0
${SCOPE === 'all' ? '(all dirs)' : `restricted to top=="${SCOPE}"`}. Skip any file whose .cpp already exists.
For each kept row record file, dir, its benchmark (Spec §4), and loc (\`wc -l\`). Cap 'ready' to ${MAXFILES}
rows but report the true total in 'layerSize'. Work from ${PROJECT}; prefix env commands with \`${ENV} &&\`.
Return only the structured object.`,
  { label: 'resolve', phase: 'Resolve', schema: RESOLVE_SCHEMA }
)
if (!resolved?.ready?.length) {
  log('Resolve found no ready files. Nothing to translate this run.')
  return { resolved, authored: [], integrated: null }
}
log(`Layer: ${resolved.layerSize} ready leaf(s) in "${SCOPE}"; taking ${resolved.ready.length} this run.`)

// Author — one agent per file, in parallel. Each writes ONLY its own outputs.
// Size-gate: a big file is escalated to a stronger model instead of being chunked.
phase('Author')
const authorPrompt = (f) => `Translate one MCFM Fortran file to C++: \`${f.file}\` (${f.dir}).
Work inside $MCFM_HOME; prefix env commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC} and follow it —
especially §2 (rules; never fabricate a called symbol) and §3 (silent traps). First generate the draft
scaffold for hints: \`${ENV} && cd ${PROJECT} && python3 dev/tools/draft/scribe_draft.py $MCFM_HOME/src/${f.file} --force\`;
consult dev/tools/draft/seed_examples.toml for the worked-example shape.
Write only this file's outputs (.cpp/.hpp/_fi.F90). Do NOT build, edit CMake, or touch shared headers —
the serial integrator does that. If a callee is not yet C++, set authored="deferred"; if a shared constant
is missing, note it and use an inline literal. Return one structured row.`

const authored = await parallel(resolved.ready.map((f) => () =>
  agent(authorPrompt(f), {
    label: `author:${f.file}`, phase: 'Author', schema: AUTHOR_SCHEMA,
    model: (f.loc || 0) > BIGLOC ? 'opus' : 'sonnet',   // size-gate
  })
))
const ok = authored.filter((r) => r?.authored === 'yes')
log(`Authored ${ok.length}/${resolved.ready.length}.`)
if (!ok.length) return { resolved, authored, integrated: null }

// Integrate — ONE serial agent owns the build and applies the verification bar.
// This concentrates the correctness check in a single place: the trust anchor.
const benchesFor = (files) => [...new Set(resolved.ready.filter((f) => files.includes(f.file) && f.bench).map((f) => f.bench))]
const integratePrompt = (files, benches, consts) => `You are the SERIAL integrator — you alone own the build
tree, CMakeLists, and shared headers. Work inside $MCFM_HOME; prefix env commands with \`${ENV} &&\`.
Follow ${PROJECT}/${SPEC} §5 exactly — never grant VERIFIED without the coverage probe firing.

Files to integrate: ${files.join(', ')}
Benchmarks to run: ${benches.length ? benches.join(', ') : '(none — infrastructure, mark TRANSLATED)'}
Missing shared constants to add once: ${consts.length ? consts.join('; ') : '(none)'}

Rewire each file's CMakeLists, build once, run the benchmark(s), then run the mandatory coverage probe
(scale the output by 1.5×, confirm the ratios move, revert). VERIFIED only when the probe moved a ratio;
unchanged → TRANSLATED. If the amplitude algebra looks mistranslated, mark that one file FAILED with the
symptom and escalated=true rather than guessing. Leave the tree building clean. Return the status table only.`

let integrated = await agent(
  integratePrompt(ok.map((r) => r.file), benchesFor(ok.map((r) => r.file)), authored.map((r) => r?.notes).filter(Boolean)),
  { label: 'integrate', phase: 'Integrate', schema: INTEGRATE_SCHEMA }
)

// Fix — bounded escalation: re-author FAILED files with a stronger model, re-integrate once.
// Failures that survive are surfaced for a human, not retried indefinitely.
const failed = (integrated?.rows || []).filter((r) => r.status === 'FAILED')
if (failed.length) {
  phase('Fix')
  log(`Escalating ${failed.length} FAILED file(s) to a stronger model.`)
  const repaired = (await parallel(failed.map((r) => () =>
    agent(`Repair the FAILED translation of \`${r.file}\`. Symptom: ${r.notes || '(diagnose from source)'}.
Work inside $MCFM_HOME; prefix env commands with \`${ENV} &&\`. READ ${PROJECT}/${SPEC} §2–§3 and compare
against a verified sibling. Edit only this file's outputs; do NOT build or edit CMake (re-integrate does that).
Return one row.`,
      { label: `fix:${r.file}`, phase: 'Fix', schema: AUTHOR_SCHEMA, model: 'opus' })
  ))).filter((r) => r?.authored === 'yes').map((r) => r.file)

  if (repaired.length) {
    const reInt = await agent(integratePrompt(repaired, benchesFor(repaired), []),
      { label: 're-integrate', phase: 'Integrate', schema: INTEGRATE_SCHEMA })
    const byFile = new Map((integrated?.rows || []).map((r) => [r.file, r]))
    for (const r of (reInt?.rows || [])) byFile.set(r.file, r)
    integrated = { buildOk: reInt?.buildOk ?? integrated?.buildOk, rows: [...byFile.values()] }
  }
}

const by = (s) => (integrated?.rows || []).filter((r) => r.status === s)
log(`Run complete: ${by('VERIFIED').length} verified, ${by('TRANSLATED').length} translated, ${by('FAILED').length} failed.`)
return {
  scope: SCOPE,
  layerSize: resolved.layerSize,
  authored,
  integrated,
  toRecord: { verified: by('VERIFIED'), translated: by('TRANSLATED'), failed: by('FAILED') },
}
