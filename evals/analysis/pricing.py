"""Per-token USD billing rates used by generate_graphs.py.

All rates are USD per 1,000,000 tokens, taken directly from Anthropic's
published pricing page (https://platform.claude.com/docs/en/about-claude/pricing),
fetched 2026-08-12:

  Claude Opus 5:   $5 / MTok input,  $25 / MTok output,
                    $6.25 / MTok 5m-cache-write, $0.50 / MTok cache read
  Claude Sonnet 5: $2 / MTok input,  $10 / MTok output,
                    $2.50 / MTok 5m-cache-write, $0.20 / MTok cache read
                    ($2/$10 input/output is Sonnet 5's standing price, not
                    introductory pricing — the previously-scheduled increase
                    to $3/$15 on 2026-09-01 was cancelled.)

Kimi K3 (model id oaic-moonshotai/Kimi-K3; the run directory is named
codescribe-kimi-k3-5, which is a naming slip -- the model is K3, not K3.5) is not an
Anthropic model and has no entry here on purpose — cost() raises KeyError for
it, and callers must treat that run's USD cost as not applicable rather than
silently pricing it off someone else's rate card.
"""

PRICING = {
    "claude-opus-5": {
        "input": 5.00,
        "output": 25.00,
        "cache_write": 6.25,   # 1.25x input, 5-minute TTL
        "cache_read": 0.50,    # 0.1x input
    },
    "claude-sonnet-5": {
        "input": 2.00,
        "output": 10.00,
        "cache_write": 2.50,
        "cache_read": 0.20,
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
