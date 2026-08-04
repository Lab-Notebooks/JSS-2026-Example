"""Documented gaps in the raw logs that the parsers cannot recover on their own,
patched in explicitly here (with sourcing) rather than silently under-counted.

experiments/07-24-2028/ccworkflow-sonnet-4-6-effort-high/usage_report.md
(generated inside that run, corrected 2026-07-25 via transcript analysis)
documents two opus-4-6 integrate agents — a8a87b and abb36a — whose
agent-<id>.jsonl transcripts are absent from the archived workflow-wf_*/
directory (parse_ccworkflow.py has nothing to read for them), yet they are the
two most expensive agents in the entire run: abb36a alone (the stalled
integrate-Group-2 agent, still PAUSED mid-fix-loop when the workflow was
terminated) accounts for 28.16M cache-read tokens and ~$20.53 (at the
corrected opus-4-6 rate — see analysis/pricing.py) — more than the
rest of the run combined. Excluding them would understate this run's true cost
by more than half. Their token counts are taken verbatim from that report's
per-agent table, which flags them "unverified but internally consistent" with
the reported opus subtotals (not fabricated — corrected once already from an
earlier, inflated version of this same report).
"""

WALL_TIME_OVERRIDE_SECONDS = {
    # The 07-24 ccworkflow run's true wall-clock span (start to last event) is
    # documented in usage_report.md as 2h 19m 22s (8,362s). Computing the span
    # from timestamps in the archived agent-*.jsonl files alone yields only
    # ~64 min, because it inherits the same archive gap as the cost figures
    # above (the two missing opus integrate agents ran later in the session
    # and their timestamps aren't recoverable from the archive).
    ("07-24-2028", "ccworkflow-sonnet-4-6-effort-high"): 8362,
}

MISSING_CCWORKFLOW_AGENTS = [
    {
        "day": "07-24-2028",
        "run_name": "ccworkflow-sonnet-4-6-effort-high",
        "agent_id": "a8a87b",
        "phase": "integrate",
        "model": "claude-opus-4-6",
        "status": "interrupted",
        "input_tokens": 10766,
        "output_tokens": 16823,
        "cache_write_tokens": 166226,
        "cache_read_tokens": 893989,
    },
    {
        "day": "07-24-2028",
        "run_name": "ccworkflow-sonnet-4-6-effort-high",
        "agent_id": "abb36a",
        "phase": "integrate",
        "model": "claude-opus-4-6",
        "status": "interrupted",  # "PAUSED (integrate G2)" in usage_report.md
        "input_tokens": 17016,
        "output_tokens": 162466,
        "cache_write_tokens": 367756,
        "cache_read_tokens": 28160084,
    },
]
