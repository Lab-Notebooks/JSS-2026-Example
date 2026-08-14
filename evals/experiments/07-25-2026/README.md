# Experiment Day: 2026-07-25

**Task:** mcfm-translate — Fortran → C++ translation of MCFM physics code  
**Correctness bar:** `jobrunner submit tests/mcfm` 272/272 tests  
**Runs in this directory:** 2 runs with data (one ccworkflow, one csloop variant); one additional csloop variant was planned but never executed.

> **Correction (2026-07-25):** This README originally described two csloop runs — `csloop-sonnet-4-6-without-reasoning` and `csloop-gpt-5-4-without-reasoning` — with detailed configuration sections for each, including specific `_llm.py` line-number citations. Neither directory exists anywhere in `07-25-2028/`. The only csloop run that actually produced data this day is `csloop-sonnet-4-6-with-reasoning` (3 attempts, all cut short by Anthropic API timeouts), which the original README never mentioned. A `csloop-gpt-5-4-effort-high` directory exists but is empty — no GPT-5.4 run was ever carried out. The sections below have been corrected to reflect what actually ran.

---

## Runs

| Directory | Harness | Model | Reasoning |
|---|---|---|---|
| `ccworkflow-sonnet-4-6-effort-high` | Claude Code Workflow (`transform.js`) | sonnet-4-6 (author), opus-4-6 (integrate/fix) | ON — `effortLevel: "high"` in settings.json |
| `csloop-sonnet-4-6-with-reasoning` | CodeScribe loop (`_agent.py` + `_llm.py`) | sonnet-4-6 | Configured ON (`CODESCRIBE_AGENT_REASONING=1`) — but every loop's recorded `[usage].reasoning` value is 0 across all attempts |
| `csloop-gpt-5-4-effort-high` | — | GPT-5.4 (planned, not run) | N/A — directory contains no metadata, transformation files, or logs |

**What changes from 07-24:** The csloop model switches from opus-4-6 to sonnet-4-6, with reasoning nominally kept on (rather than 07-24's on/off comparison). In practice, no attempt recorded any reasoning tokens, and all three were cut short by the same Anthropic API timeout error, so this day does not yield a clean model or reasoning comparison — see "What This Day Actually Tested" below.

---

## Reasoning / Effort Configuration

### ccworkflow-sonnet-4-6-effort-high

Identical configuration to the 07-24 run. Reproduced here for direct comparison.

**Config file:** `~/.claude/settings.json`
```json
{
  "model": "claude-sonnet-4-6",
  "effortLevel": "high"
}
```

**What this does:**  
The harness applies `high` effort to every agent in the workflow. Extended thinking is on for all six phases (triage, bundle, author, integrate, fix, metadata). No per-agent effort override is set in `transform.js`.

**API-level effect:**  
The harness translates `effortLevel: "high"` into the Anthropic extended thinking parameter internally. The exact thinking mode and token budget are not visible to the script.

**Models per phase:**

| Phase | Model | Thinking |
|---|---|---|
| Triage, Bundle, Author, Metadata | claude-sonnet-4-6 | ON (inherits high effort) |
| Integrate, Fix | claude-opus-4-6 | ON (inherits high effort) |

**Token tracking:** Reasoning tokens not reported from within the harness; not present in metadata TOMLs.

---

### csloop-sonnet-4-6-with-reasoning

**Config:** `CODESCRIBE_AGENT_REASONING=1` (per directory name and intended config); model `anthropic-claude-sonnet-4-6`.

**Attempts:** `attempt01-crashed`, `attempt02-resume-crashed`, `attempt03-resume` (this last attempt directory is empty — no metadata, transformation output, or logs).

**What actually happened:** Both non-empty attempts crashed with the same error, per `human_review`:
```
anthropic.APIStatusError: {'type': 'error', 'error': {'type': 'api_error', 'message': 'Request timed out or interrupted. This could be due to a network timeout, dropped connection, or request cancellation.'}}
```
Despite reasoning being configured on, `reasoning = 0` in every `[usage]` block of every `loop_*_author.toml` / `loop_*_review.toml` across both attempts (e.g. `attempt02-resume-crashed/metadata/loop_001_author.toml:654`, `loop_002_author.toml:385`) — no reasoning tokens were ever billed in this run, and no `manifest.toml` in the run contains a cumulative reasoning field.

**Token tracking (`attempt02-resume-crashed`, the only attempt to complete 2 full loops):** cumulative input 283,249 / output 104,681 / cache creation 265,299 / cache read 3,686,349 (`metadata/manifest.toml`), which sums correctly against the per-loop `[usage]` blocks.

**Compared to 07-24 csloop runs:** Same harness, but model is sonnet-4-6 instead of opus-4-6, and reasoning was intended to be on rather than compared on/off. Because every attempt crashed on an infrastructure timeout before completing, and no reasoning tokens were ever recorded, this run does not cleanly isolate either variable (model or reasoning) — it primarily demonstrates harness instability under this model/config combination.

---

### csloop-gpt-5-4-effort-high (planned, not executed)

A directory for this run exists (`csloop-gpt-5-4-effort-high/`) but is empty — no `loop.toml`, `manifest.toml`, `agent_log.md`, or `human_review`. No GPT-5.4 run was carried out on 07-25, and no OpenAI-compatible model appears anywhere in this experiment tree.

---

## What This Day Actually Tested

| Variable | 07-24 | 07-25 |
|---|---|---|
| ccworkflow config | sonnet author, opus integrate, thinking ON | same — held constant |
| csloop reasoning | compared ON vs. OFF (opus-4-6) | intended ON (sonnet-4-6), but recorded as 0 in all usage data |
| csloop model | opus-4-6 (both) | sonnet-4-6 (only model with any run data); GPT-5.4 never run |

07-25 does not deliver the sonnet-vs-GPT-5.4 model comparison it was intended to: the GPT-5.4 run was never executed, and the sonnet-4-6 csloop run crashed on infrastructure timeouts in all attempts without producing usable reasoning-token data. The only clean result from this day is the ccworkflow run (see its `human_review` and `agent_log.md`).

---

## How Reasoning Differs Between the Two Harnesses

This is the key thing to keep in mind when reading results across both days:

**Claude Code Workflow (`effortLevel: "high"`):**
- Thinking is always on for every agent — there is no per-agent toggle in `transform.js`
- The harness controls the thinking mode and token budget opaquely
- Reasoning tokens are not reported back to the workflow script
- The only way to turn thinking off is to change `settings.json` globally or add `effort: 'low'` to individual `agent()` calls in the script

**CodeScribe (`AnthropicModel`):**
- Thinking is controlled per model instance — constructor arg `reasoning=True` or env var `CODESCRIBE_AGENT_REASONING=1`
- When on, uses `{"type": "adaptive"}` — the model decides per-call whether to think; not guaranteed to think on every iteration even when enabled, and across every csloop run recorded to date (07-24 and 07-25, reasoning on or off) it has never produced a non-zero `reasoning` token count
- Turning it on/off is a clean boolean at instantiation time, independent of any global session config
