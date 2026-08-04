# Experiment Day: 2026-07-24

**Task:** mcfm-translate — Fortran → C++ translation of MCFM physics code  
**Correctness bar:** `jobrunner submit tests/mcfm` 272/272 tests  
**Runs in this directory:** 3 (one ccworkflow, two csloop variants)

---

## Runs

| Directory | Harness | Model | Reasoning |
|---|---|---|---|
| `ccworkflow-sonnet-4-6-effort-high` | Claude Code Workflow (`transform.js`) | sonnet-4-6 (author), opus-4-6 (integrate/fix) | ON — `effortLevel: "high"` in settings.json |
| `csloop-opus-4-6-with-reasoning` | CodeScribe loop (`_agent.py` + `_llm.py`) | opus-4-6 | ON — `CODESCRIBE_AGENT_REASONING=1` |
| `csloop-opus-4-6-without-reasoning` | CodeScribe loop (`_agent.py` + `_llm.py`) | opus-4-6 | OFF — default (`reasoning=False`) |


---

## Reasoning / Effort Configuration

### ccworkflow-sonnet-4-6-effort-high

**Config file:** `~/.claude/settings.json`
```json
{
  "model": "claude-sonnet-4-6",
  "effortLevel": "high"
}
```

**What this does:**  
The Claude Code Workflow harness reads `effortLevel` at session start and applies it to every `agent()` call in `transform.js` that does not set its own `effort` override. Since `transform.js` sets no `effort` on any of its six agent types (triage, bundle, author, integrate, fix, metadata), all agents run at `high` effort.

**API-level effect:**  
The harness translates `effortLevel: "high"` into Claude's extended thinking API parameter internally. The exact thinking mode (adaptive vs. enabled) and token budget are managed by the harness; the workflow script has no visibility into them.

**Scope:**  
Global and persistent — applies to every workflow run launched in this session, not just this experiment.

**Per-agent override:**  
`transform.js` supports per-agent effort via the `effort` option on each `agent()` call (e.g. `agent(prompt, { effort: 'low' })`), but none are set. All agents inherit the session effort.

**Models per phase:**

| Phase | Model | Notes |
|---|---|---|
| Triage | claude-sonnet-4-6 | session default, inherits `high` effort |
| Bundle | claude-sonnet-4-6 | session default |
| Author (parallel) | claude-sonnet-4-6 | session default; thinking fires on each parallel author agent |
| Integrate | claude-opus-4-6 | hardcoded in `transform.js`; inherits `high` effort |
| Fix | claude-opus-4-6 | hardcoded; inherits `high` effort |
| Metadata | claude-sonnet-4-6 | session default |

**Token tracking:** Reasoning token counts are not available from within the workflow harness. The metadata TOMLs written by the Metadata phase do not include a reasoning_tokens field.

---

### csloop-opus-4-6-with-reasoning

**Config:** `CODESCRIBE_AGENT_REASONING=1` environment variable (or `AnthropicModel(reasoning=True)`)

**What this does (`_llm.py:167–184`):**
```python
env_reasoning = os.getenv("CODESCRIBE_AGENT_REASONING", "").lower() in ("1", "true", "yes")
self.reasoning_enabled = reasoning or env_reasoning
self.thinking = (
    {"type": "adaptive", "display": "summarized"}
    if self.reasoning_enabled
    else None
)
```

**API-level effect:**  
When `reasoning_enabled` is true, every call to `chat_with_tools()` includes:
```python
kwargs["thinking"] = {"type": "adaptive", "display": "summarized"}
```
The mode is `adaptive` — the model decides on each individual API call whether to produce a thinking block. It will sometimes skip thinking even with this flag set, depending on the query complexity it perceives.

**Scope:**  
Per `AnthropicModel` instance. All iterations of a single `Agent.run()` use the same instance, so reasoning is either on or off for the full run. Different agent runs (author loop, review loop) are separate instances and each would need the same env var.

**Thinking block continuity:**  
When the model does produce a thinking block, `_normalize_anthropic_tool_response()` extracts it with its `signature` field (`_llm.py:596–606`). The `format_tool_result_messages()` method echoes these blocks back verbatim in the next assistant turn (`_llm.py:351–353`). This is required by the Anthropic API for multi-turn tool use with thinking active.

**Token tracking:** The mechanism is implemented to track reasoning tokens separately (`_normalize_anthropic_usage()` maps `thinking_tokens → reasoning_tokens` in `_llm.py:573`), but it did not fire in this run: `reasoning = 0` in every `[usage]` block of every `loop_*_author.toml` / `loop_*_review.toml` in this directory, and `manifest.toml` contains no cumulative reasoning field at all. Despite `CODESCRIBE_AGENT_REASONING=1` being set, no reasoning tokens were actually recorded for this run.

**Model:** anthropic-claude-opus-4-6 (all loops — author and review)  
**Max tokens:** 32768 (default `CODESCRIBE_MAX_TOKENS`)

---

### csloop-opus-4-6-without-reasoning

**Config:** No reasoning flags set. `AnthropicModel(reasoning=False)` (the default).

**What this does:**  
`self.thinking = None` — the `thinking` kwarg is not added to the API call. The model produces no thinking blocks. `format_tool_result_messages()` receives `reasoning_blocks=None` and skips the echo-back step.

**API-level effect:** Standard Anthropic messages API call, no extended thinking.

**Token tracking:** `TokenUsage.reasoning` will be 0 throughout (no thinking tokens billed). All other fields (input, output, cache) are tracked normally.

**Model:** anthropic-claude-opus-4-6  
**Max tokens:** 32768

**Note on stability:** This run required 4 attempts (attempt01-crashed, attempt02-resume, attempt03-resume-crashed, attempt04-resume), all against the mcfm-translate transformation — `attempt01-crashed/metadata/manifest.toml` and `loop_001_author.toml` both confirm `task_file = .../mcfm-translate/loop.toml`. (An unrelated, stray `mcfm-cleanup` transformation folder previously sat alongside attempt01-crashed's own data; it did not reflect what that attempt actually ran and has since been removed.) Crashes were unrelated to the reasoning flag.

---

## Key Difference for This Experiment

This day compared three things simultaneously: harness architecture (ccworkflow vs. csloop), and within csloop, the effect of the reasoning flag on the same model and task. The ccworkflow always had thinking active (effortLevel: high, no way to turn it off per-agent in transform.js). The two csloop runs isolated the reasoning variable: same model (opus-4-6), same task, same harness — only the thinking parameter differed.

See `comparison_ccworkflow_vs_csloop.md` in this directory for the full results analysis.
