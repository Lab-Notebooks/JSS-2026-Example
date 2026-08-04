"""Per-token USD billing rates used by generate_graphs.py.

All rates are USD per 1,000,000 tokens, taken directly from Anthropic's
published pricing page (https://platform.claude.com/docs/en/about-claude/pricing),
fetched 2026-07-25:

  Claude Opus 4.6:   $5 / MTok input,  $25 / MTok output,
                      $6.25 / MTok 5m-cache-write, $0.50 / MTok cache read
  Claude Sonnet 4.6: $3 / MTok input,  $15 / MTok output,
                      $3.75 / MTok 5m-cache-write, $0.30 / MTok cache read

GPT-5.4 rates use OpenAI's still-served gpt-5.4-class tier as the closest
public proxy, since that model has no first-party rate card as of 2026-07-25.

CORRECTION (2026-07-25): an earlier version of this file used opus-4-6 rates
of $15 / $75 / $18.75 / $1.50, copied from experiments/07-24-2028/
ccworkflow-sonnet-4-6-effort-high/usage_report.md — a report generated inside
that experiment run itself, which claimed those were "Anthropic published
rates as of 2026-07." That claim was wrong: $15/$75 is the published rate for
Claude Opus 4.1 (deprecated), not Opus 4.6. Verified against the official
pricing page above; all opus-4-6 figures below and everywhere downstream
(summary_tables.md, the generated figures, EVALUATION.md, and
usage_report.md itself) have been corrected accordingly.
"""

PRICING = {
    "claude-opus-4-6": {
        "input": 5.00,
        "output": 25.00,
        "cache_write": 6.25,   # 1.25x input, 5-minute TTL
        "cache_read": 0.50,    # 0.1x input
    },
    "claude-sonnet-4-6": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "gpt-5-4": {
        "input": 2.50,
        "output": 15.00,
        "cache_write": 2.50,   # gpt-5.4-class tier has no separate cache-write fee; billed at input rate
        "cache_read": 0.25,
    },
}


def cost(model, input_tokens=0, output_tokens=0, cache_write_tokens=0, cache_read_tokens=0):
    """Return USD cost for the given token counts under `model`'s rate card.

    Unknown models raise KeyError rather than silently defaulting — a silent
    fallback would misprice a model nobody priced on purpose.
    """
    rates = PRICING[model]
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + cache_write_tokens * rates["cache_write"]
        + cache_read_tokens * rates["cache_read"]
    ) / 1_000_000
