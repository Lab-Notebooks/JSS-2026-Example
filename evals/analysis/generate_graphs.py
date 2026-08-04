#!/usr/bin/env python3.10
"""Generate the paper figures + summary tables for the ccworkflow-vs-csloop
evaluation of the mcfm-translate transformation.

Run with: python3.10 analysis/generate_graphs.py
(Needs Python 3.10+ for tomllib, or `pip install tomli` on older Pythons.)

Reads only from experiments/ (read-only). Writes, under analysis/figures/:
  fig1_cost_and_cache.png        - standalone, compact
  fig2_reasoning_tool_calls.png  - standalone, compact
  fig3_coverage.png              - standalone, compact
  fig4_wall_time.png             - standalone, compact
  fig_combined.png               - all 7 panels together, for single-figure use in a paper
and analysis/summary_tables.md (the numeric source of truth behind every panel).

Every plotting function below draws onto an Axes it's given (draw_*), so the
same code builds both the small standalone figures and the one combined
figure — no logic is duplicated between them.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, str(Path(__file__).parent))

from parse_ccworkflow import parse_all_ccworkflow
from parse_csloop import parse_all_csloop
from parse_coverage import coverage_for_run
from pricing import cost
from known_gaps import MISSING_CCWORKFLOW_AGENTS, WALL_TIME_OVERRIDE_SECONDS

REPO_ROOT = Path(__file__).parent.parent
EXPERIMENTS = REPO_ROOT / "experiments"
FIGURES_DIR = Path(__file__).parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Style — validated default palette from the dataviz skill (references/palette.md)
# ---------------------------------------------------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

CAT = {
    "blue": "#2a78d6",
    "orange": "#eb6834",
    "aqua": "#1baf7a",
    "yellow": "#eda100",
    "magenta": "#e87ba4",
    "green": "#008300",
    "violet": "#4a3aa7",
    "red": "#e34948",
}
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

FONT = "DejaVu Sans"  # pinned to one concrete font (not a fallback list) so every
                      # text element in every figure — titles included — renders
                      # in exactly the same typeface.

TITLE_SIZE = 9.5
TICK_SIZE = 8
LABEL_SIZE = 8.3
LEGEND_SIZE = 7.3
ANNOT_SIZE = 7.3
SUPTITLE_SIZE = 12.5
CAPTION_SIZE = 7.3

plt.rcParams.update(
    {
        "font.family": FONT,
        "font.size": LABEL_SIZE,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_SECONDARY,
        "axes.labelsize": LABEL_SIZE,
        "axes.titlesize": TITLE_SIZE,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": TICK_SIZE,
        "ytick.labelsize": TICK_SIZE,
        "legend.fontsize": LEGEND_SIZE,
        "grid.color": GRID,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
    }
)

# ---------------------------------------------------------------------------
# Run identity / labeling
# ---------------------------------------------------------------------------
RUN_LABELS = {
    ("07-24-2028", "ccworkflow-sonnet-4-6-effort-high"): "ccworkflow (run A)",
    ("07-24-2028", "csloop-opus-4-6-with-reasoning"): "csloop opus-4-6 +reasoning",
    ("07-24-2028", "csloop-opus-4-6-without-reasoning"): "csloop opus-4-6 no-reasoning",
    ("07-25-2028", "ccworkflow-sonnet-4-6-effort-high"): "ccworkflow (run B)",
    ("07-25-2028", "csloop-sonnet-4-6-with-reasoning"): "csloop sonnet-4-6 +reasoning",
}
# Short x-axis codes (keeps bars compact and avoids label collisions); figures
# caption the full mapping once, below the plot.
RUN_CODES = {
    ("07-24-2028", "ccworkflow-sonnet-4-6-effort-high"): "R1",
    ("07-24-2028", "csloop-opus-4-6-with-reasoning"): "R2",
    ("07-24-2028", "csloop-opus-4-6-without-reasoning"): "R3",
    ("07-25-2028", "ccworkflow-sonnet-4-6-effort-high"): "R4",
    ("07-25-2028", "csloop-sonnet-4-6-with-reasoning"): "R5",
}
RUN_CODE_CAPTION = (
    "R1 = ccworkflow (run A)  |  R2 = csloop opus-4-6 +reasoning  |  "
    "R3 = csloop opus-4-6 no-reasoning  |  R4 = ccworkflow (run B)  |  "
    "R5 = csloop sonnet-4-6 +reasoning"
)
KEYS = list(RUN_LABELS.keys())
# Runs deliberately excluded from the figures because they never executed
# (verified via parse_coverage.coverage_for_run -> "not-executed"):
#   07-25-2028/csloop-gpt-5-4-effort-high               (planned, no GPT-5.4 run ever ran)
#   07-25-2028/csloop-sonnet-4-6-with-reasoning-retries  (empty placeholder for a retry-hardened rerun)


def normalize_model(model):
    return model.replace("anthropic-", "") if model else model


def run_key(day, run_name):
    return (day, run_name)


def _title(text, letter):
    return f"{letter} {text}" if letter else text


# ---------------------------------------------------------------------------
# Load + aggregate
# ---------------------------------------------------------------------------
def load_run_aggregates():
    cc_rows = parse_all_ccworkflow(EXPERIMENTS)
    cs_rows = parse_all_csloop(EXPERIMENTS)
    # Patch in agents whose transcripts are missing from the archive but are
    # documented in a corrected accounting for that run — see known_gaps.py.
    # Without this, the 07-24 ccworkflow run's cost would be understated by
    # more than half (it's missing the single largest cost line).
    cc_rows = cc_rows + [dict(row, n_messages=None, tool_ok=None, tool_error=None) for row in MISSING_CCWORKFLOW_AGENTS]

    runs = {}
    for key in KEYS:
        runs[key] = {
            "harness": "ccworkflow" if "ccworkflow" in key[1] else "csloop",
            "input": 0,
            "output": 0,
            "cache_write": 0,
            "cache_read": 0,
            "cost": 0.0,
            "cost_by_model": {},
        }

    for row in cc_rows + cs_rows:
        key = run_key(row["day"], row["run_name"])
        if key not in runs:
            continue
        r = runs[key]
        model = normalize_model(row["model"])
        r["input"] += row["input_tokens"]
        r["output"] += row["output_tokens"]
        r["cache_write"] += row["cache_write_tokens"]
        r["cache_read"] += row["cache_read_tokens"]
        c = cost(
            model,
            row["input_tokens"],
            row["output_tokens"],
            row["cache_write_tokens"],
            row["cache_read_tokens"],
        )
        r["cost"] += c
        r["cost_by_model"][model] = r["cost_by_model"].get(model, 0.0) + c

    return runs, cc_rows, cs_rows


def compute_reasoning_stats(cs_rows):
    with_r = [r for r in cs_rows if r["run_name"] == "csloop-opus-4-6-with-reasoning"]
    without_r = [r for r in cs_rows if r["run_name"] == "csloop-opus-4-6-without-reasoning"]

    def agg(rows):
        ok = sum(r["tool_ok"] for r in rows)
        errors = sum(r["tool_errors"] for r in rows)
        rejected = sum(r["tool_rejected"] for r in rows)
        return {"ok": ok, "errors": errors, "rejected": rejected, "total": ok + errors + rejected}

    return {"with_reasoning": agg(with_r), "without_reasoning": agg(without_r)}


def _ccworkflow_wall_time_seconds(day, run_name):
    """Span between the first and last assistant-message timestamp across all
    agent-*.jsonl files in the run's workflow-wf_* dir. Falls back to a
    documented override where the archive is known to be missing agents
    (see known_gaps.WALL_TIME_OVERRIDE_SECONDS)."""
    key = (day, run_name)
    if key in WALL_TIME_OVERRIDE_SECONDS:
        return WALL_TIME_OVERRIDE_SECONDS[key]

    import json as _json
    from datetime import datetime as _dt

    run_dir = EXPERIMENTS / day / run_name
    timestamps = []
    for workflow_dir in run_dir.glob("workflow-wf_*"):
        for agent_path in workflow_dir.glob("agent-*.jsonl"):
            with open(agent_path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    ts = _json.loads(line).get("timestamp")
                    if ts:
                        timestamps.append(ts)
    if len(timestamps) < 2:
        return None
    timestamps.sort()
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    t0 = _dt.strptime(timestamps[0], fmt)
    t1 = _dt.strptime(timestamps[-1], fmt)
    return (t1 - t0).total_seconds()


def _csloop_wall_time_seconds(cs_rows, day, run_name):
    """Sum of per-loop duration_s across all attempts. csloop runs one loop at
    a time (no intra-run parallelism), so this sum approximates true elapsed
    engine time within a session — it does not include gaps between crashed
    attempts (waiting for a human to notice and resume), which is a real but
    separate cost, reported alongside coverage in the write-up."""
    return sum(r["duration_s"] for r in cs_rows if r["day"] == day and r["run_name"] == run_name)


def load_wall_times(cs_rows):
    wall_times = {}
    for day, run_name in KEYS:
        if "ccworkflow" in run_name:
            wall_times[(day, run_name)] = _ccworkflow_wall_time_seconds(day, run_name)
        else:
            wall_times[(day, run_name)] = _csloop_wall_time_seconds(cs_rows, day, run_name)
    return wall_times


# ---------------------------------------------------------------------------
# Panel A — total cost by model
# ---------------------------------------------------------------------------
def draw_cost_panel(ax, runs, letter=None):
    labels = [RUN_CODES[k] for k in KEYS]
    x = range(len(KEYS))
    bar_colors = {"claude-sonnet-4-6": CAT["blue"], "claude-opus-4-6": CAT["violet"]}

    all_models_seen = []
    for k in KEYS:
        for m in runs[k]["cost_by_model"]:
            if m not in all_models_seen:
                all_models_seen.append(m)

    bottoms = [0.0] * len(KEYS)
    for model in all_models_seen:
        heights = [runs[k]["cost_by_model"].get(model, 0.0) for k in KEYS]
        ax.bar(x, heights, bottom=bottoms, width=0.6, color=bar_colors.get(model, CAT["aqua"]),
               edgecolor=SURFACE, linewidth=1)
        bottoms = [b + h for b, h in zip(bottoms, heights)]

    for xi, total in zip(x, bottoms):
        ax.text(xi, total + max(bottoms) * 0.03, f"${total:.0f}", ha="center", va="bottom",
                fontsize=ANNOT_SIZE, color=INK_SECONDARY)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("USD (proxy rates)")
    ax.set_title(_title("Total cost by model", letter))
    ax.set_ylim(0, max(bottoms) * 1.22)
    handles = [mpatches.Patch(color=bar_colors.get(m, CAT["aqua"]), label=m) for m in all_models_seen]
    ax.legend(handles=handles, loc="upper center", frameon=False)


# ---------------------------------------------------------------------------
# Panel B — cache-read share of input-side tokens
# ---------------------------------------------------------------------------
def draw_cache_panel(ax, runs, letter=None):
    labels = [RUN_CODES[k] for k in KEYS]
    x = range(len(KEYS))

    shares = []
    for k in KEYS:
        r = runs[k]
        total_input_side = r["input"] + r["cache_write"] + r["cache_read"]
        shares.append(100.0 * r["cache_read"] / total_input_side if total_input_side else 0.0)

    ax.bar(x, shares, width=0.6, color=CAT["aqua"], edgecolor=SURFACE, linewidth=1)
    for xi, s in zip(x, shares):
        ax.text(xi, s + 2, f"{s:.0f}%", ha="center", va="bottom", fontsize=ANNOT_SIZE, color=INK_SECONDARY)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Cache-read share (%)")
    ax.set_ylim(0, 112)
    ax.set_title(_title("Cache efficiency", letter))


# ---------------------------------------------------------------------------
# Panel C/D — reasoning ON vs OFF tool-call outcomes (opus-4-6)
# ---------------------------------------------------------------------------
def draw_reasoning_counts_panel(ax, stats, letter=None):
    labels = ["reasoning ON\n(3 loops)", "reasoning OFF\n(15 loops, 4 attempts)"]
    x = [0, 1]
    outcome_colors = {"ok": STATUS["good"], "errors": STATUS["critical"], "rejected": STATUS["warning"]}
    ok_vals = [stats["with_reasoning"]["ok"], stats["without_reasoning"]["ok"]]
    err_vals = [stats["with_reasoning"]["errors"], stats["without_reasoning"]["errors"]]
    rej_vals = [stats["with_reasoning"]["rejected"], stats["without_reasoning"]["rejected"]]

    ax.bar(x, ok_vals, width=0.5, color=outcome_colors["ok"], label="ok")
    ax.bar(x, err_vals, width=0.5, bottom=ok_vals, color=outcome_colors["errors"], label="errors")
    bottom2 = [a + b for a, b in zip(ok_vals, err_vals)]
    ax.bar(x, rej_vals, width=0.5, bottom=bottom2, color=outcome_colors["rejected"], label="rejected")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Tool calls (count)")
    ax.set_title(_title("Reasoning ON/OFF: raw tool-call outcomes", letter))
    ax.legend(frameon=False, loc="upper left")


def draw_reasoning_rate_panel(ax, stats, letter=None):
    labels = ["reasoning ON", "reasoning OFF"]
    x = [0, 1]
    outcome_colors = {"ok": STATUS["good"], "errors": STATUS["critical"], "rejected": STATUS["warning"]}

    def rates(cond):
        tot = stats[cond]["total"] or 1
        return (100 * stats[cond]["ok"] / tot, 100 * stats[cond]["errors"] / tot, 100 * stats[cond]["rejected"] / tot)

    r_ok, r_err, r_rej = zip(*[rates("with_reasoning"), rates("without_reasoning")])
    ax.bar(x, r_ok, width=0.5, color=outcome_colors["ok"])
    ax.bar(x, r_err, width=0.5, bottom=r_ok, color=outcome_colors["errors"])
    bottom2 = [a + b for a, b in zip(r_ok, r_err)]
    ax.bar(x, r_rej, width=0.5, bottom=bottom2, color=outcome_colors["rejected"])
    for xi, (e, rj) in enumerate(zip(r_err, r_rej)):
        ax.text(xi, 102, f"err {e:.1f}%\nrej {rj:.1f}%", ha="center", fontsize=ANNOT_SIZE, color=INK_SECONDARY)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Share of tool calls (%)")
    ax.set_ylim(0, 118)
    ax.set_title(_title("Reasoning ON/OFF: outcome rate", letter))


# ---------------------------------------------------------------------------
# Panel E — files translated
# ---------------------------------------------------------------------------
def draw_files_panel(ax, coverage, letter=None):
    labels = [RUN_CODES[k] for k in KEYS]
    x = list(range(len(KEYS)))
    harness_color = {"ccworkflow": CAT["blue"], "csloop": CAT["orange"]}
    settled = [coverage[k]["files_settled"] for k in KEYS]
    colors = [harness_color["ccworkflow"] if "ccworkflow" in k[1] else harness_color["csloop"] for k in KEYS]

    ax.bar(x, settled, width=0.6, color=colors, edgecolor=SURFACE, linewidth=1)
    for xi, s in zip(x, settled):
        ax.text(xi, s + max(settled) * 0.03, str(s), ha="center", fontsize=ANNOT_SIZE, color=INK_SECONDARY)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Files settled")
    ax.set_ylim(0, max(settled) * 1.2)
    ax.set_title(_title("Files translated", letter))
    handles = [
        mpatches.Patch(color=harness_color["ccworkflow"], label="ccworkflow"),
        mpatches.Patch(color=harness_color["csloop"], label="csloop"),
    ]
    ax.legend(handles=handles, frameon=False, loc="upper left")


# ---------------------------------------------------------------------------
# Panel F — claimed vs. verified correctness
# ---------------------------------------------------------------------------
def draw_correctness_panel(ax, coverage, letter=None):
    # Only where data exists. Labeled with the raw n/m fraction (not just %)
    # because the denominators genuinely differ across runs (272-test suite
    # vs. a 90-test partial run) — a percent-only label would hide that.
    plot_keys = [k for k in KEYS if coverage[k]["self_reported_pass"] or coverage[k]["human_verified_pass"]]
    px = list(range(len(plot_keys)))
    width = 0.35

    for i, k in enumerate(plot_keys):
        sp = coverage[k]["self_reported_pass"]
        vp = coverage[k]["human_verified_pass"]
        if sp is not None:
            pct = 100 * sp[0] / sp[1]
            ax.bar(i - width / 2, pct, width=width, color=CAT["blue"], hatch="///", edgecolor=INK_SECONDARY,
                   linewidth=0.5, label="self-reported" if i == 0 else None)
            ax.text(i - width / 2, pct + 3, f"{sp[0]}/{sp[1]}", ha="center", va="bottom",
                    fontsize=ANNOT_SIZE - 0.3, color=INK_SECONDARY)
        if vp is not None:
            pct = 100 * vp[0] / vp[1]
            ax.bar(i + width / 2, pct, width=width, color=STATUS["good"], edgecolor=SURFACE, linewidth=0.5,
                   label="verified" if i == 0 else None)
            ax.text(i + width / 2, pct + 3, f"{vp[0]}/{vp[1]}", ha="center", va="bottom",
                    fontsize=ANNOT_SIZE - 0.3, color=INK_SECONDARY)

    # R5 (rightmost) has only a verified bar reaching ~49%, leaving its top
    # quadrant empty — that's where the legend sits, clear of every label.
    ax.set_xticks(px)
    ax.set_xticklabels([RUN_CODES[k] for k in plot_keys])
    ax.set_ylabel("mcfm test pass rate (%)")
    ax.set_ylim(0, 122)
    ax.set_title(_title("Claimed vs. verified correctness", letter))
    ax.legend(frameon=False, loc="center right", bbox_to_anchor=(1.0, 0.62))


# ---------------------------------------------------------------------------
# Panel G — wall-clock time by run
# ---------------------------------------------------------------------------
def draw_wall_time_panel(ax, wall_times, letter=None):
    labels = [RUN_CODES[k] for k in KEYS]
    x = list(range(len(KEYS)))
    minutes = [(wall_times[k] or 0) / 60.0 for k in KEYS]
    harness_color = {"ccworkflow": CAT["blue"], "csloop": CAT["orange"]}
    colors = [harness_color["ccworkflow"] if "ccworkflow" in k[1] else harness_color["csloop"] for k in KEYS]

    ax.bar(x, minutes, width=0.5, color=colors, edgecolor=SURFACE, linewidth=1)
    for xi, m in zip(x, minutes):
        ax.text(xi, m + max(minutes) * 0.03, f"{m:.0f} min", ha="center", fontsize=ANNOT_SIZE, color=INK_SECONDARY)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Wall-clock minutes")
    ax.set_ylim(0, max(minutes) * 1.25)
    ax.set_title(_title("Wall-clock time", letter))
    handles = [
        mpatches.Patch(color=harness_color["ccworkflow"], label="ccworkflow"),
        mpatches.Patch(color=harness_color["csloop"], label="csloop"),
    ]
    ax.legend(handles=handles, loc="upper right", frameon=False, ncol=2)


# ---------------------------------------------------------------------------
# Standalone compact figures
# ---------------------------------------------------------------------------
def save_fig(fig, name, caption_lines):
    # Reserve real vertical space per caption line (each line is drawn from
    # the bottom edge upward) instead of stacking them a hairline apart.
    line_gap = 0.05
    for i, line in enumerate(reversed(caption_lines)):
        fig.text(0.5, 0.01 + i * line_gap, line, ha="center", fontsize=CAPTION_SIZE, color=INK, wrap=True)
    out = FIGURES_DIR / name
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def make_standalone_figures(runs, coverage, reasoning_stats, wall_times):
    # Fig 1 — cost & cache
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.6, 3.9))
    fig.suptitle("Token cost & cache efficiency", fontsize=SUPTITLE_SIZE)
    draw_cost_panel(a1, runs)
    draw_cache_panel(a2, runs)
    fig.tight_layout(rect=[0, 0.20, 1, 0.90])
    save_fig(fig, "fig1_cost_and_cache.png", [
        RUN_CODE_CAPTION,
        "R1's opus-4-6 cost includes 2 agents missing from its archive, taken from a corrected accounting.",
    ])

    # Fig 2 — reasoning on/off
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.6, 3.9))
    fig.suptitle("Reasoning ON vs OFF — csloop, opus-4-6", fontsize=SUPTITLE_SIZE)
    draw_reasoning_counts_panel(a1, reasoning_stats)
    draw_reasoning_rate_panel(a2, reasoning_stats)
    fig.tight_layout(rect=[0, 0.16, 1, 0.90])
    save_fig(fig, "fig2_reasoning_tool_calls.png", [
        "Billed reasoning tokens are 0 in every loop regardless of the flag; bars show tool-call outcomes instead.",
    ])

    # Fig 3 — coverage
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.6, 3.9))
    fig.suptitle("Coverage & correctness", fontsize=SUPTITLE_SIZE)
    draw_files_panel(a1, coverage)
    draw_correctness_panel(a2, coverage)
    fig.tight_layout(rect=[0, 0.16, 1, 0.90])
    save_fig(fig, "fig3_coverage.png", [RUN_CODE_CAPTION])

    # Fig 4 — wall time (single panel: skip the ax-level title, the suptitle covers it)
    fig, a1 = plt.subplots(figsize=(4.6, 3.9))
    fig.suptitle("Wall-clock time", fontsize=SUPTITLE_SIZE)
    draw_wall_time_panel(a1, wall_times)
    a1.set_title("")
    fig.tight_layout(rect=[0, 0.22, 1, 0.90])
    save_fig(fig, "fig4_wall_time.png", [
        "R1 uses a documented session span (partial archive); csloop bars sum per-loop duration, "
        "excluding crash/resume gaps.",
    ])


# ---------------------------------------------------------------------------
# Combined single figure — 6 panels, for one-figure-per-paper use.
# The correctness panel (claimed vs. verified) is intentionally left out here
# — it stays a standalone figure (fig3_coverage.png) since its claimed/
# verified nuance deserves its own caption rather than competing for space.
# ---------------------------------------------------------------------------
def _bump_fonts_for_combined(scale=1.15):
    """Combined panels are physically larger than the compact standalone
    ones, so bump text a bit for readability, and darken ticks/axis labels/
    legend text (base theme keeps these a secondary gray) to full black for
    print contrast. Called once, after the compact standalone figures are
    already saved at their base sizes/colors."""
    global ANNOT_SIZE
    plt.rcParams.update({
        "font.size": LABEL_SIZE * scale,
        "axes.titlesize": TITLE_SIZE * scale,
        "axes.labelsize": LABEL_SIZE * scale,
        "axes.labelcolor": INK,
        "xtick.labelsize": TICK_SIZE * scale,
        "ytick.labelsize": TICK_SIZE * scale,
        "xtick.color": INK,
        "ytick.color": INK,
        "legend.fontsize": LEGEND_SIZE * scale,
        "legend.labelcolor": INK,
    })
    ANNOT_SIZE = ANNOT_SIZE * scale


def make_combined_figure(runs, coverage, reasoning_stats, wall_times):
    fig = plt.figure(figsize=(10.5, 9.8))
    gs = fig.add_gridspec(3, 2, hspace=0.38, wspace=0.32, top=0.93, bottom=0.07, left=0.08, right=0.98)

    draw_cost_panel(fig.add_subplot(gs[0, 0]), runs, letter="(a)")
    draw_cache_panel(fig.add_subplot(gs[0, 1]), runs, letter="(b)")
    draw_reasoning_counts_panel(fig.add_subplot(gs[1, 0]), reasoning_stats, letter="(c)")
    draw_reasoning_rate_panel(fig.add_subplot(gs[1, 1]), reasoning_stats, letter="(d)")
    draw_files_panel(fig.add_subplot(gs[2, 0]), coverage, letter="(e)")
    draw_wall_time_panel(fig.add_subplot(gs[2, 1]), wall_times, letter="(f)")

    fig.suptitle(
        "ccworkflow vs. csloop on transformations/mcfm-translate: cost, reasoning & coverage",
        fontsize=SUPTITLE_SIZE + 2,
        y=0.985,
    )
    # Split into two lines (rather than relying on matplotlib's wrap=True,
    # which under-wraps center-aligned text) so the caption never runs past
    # the figure width.
    caption_line1 = "R1 = ccworkflow (run A)  |  R2 = csloop opus-4-6 +reasoning  |  R3 = csloop opus-4-6 no-reasoning"
    caption_line2 = "R4 = ccworkflow (run B)  |  R5 = csloop sonnet-4-6 +reasoning"
    fig.text(0.5, 0.03, caption_line1, ha="center", fontsize=CAPTION_SIZE * 1.55, color=INK)
    fig.text(0.5, 0.005, caption_line2, ha="center", fontsize=CAPTION_SIZE * 1.55, color=INK)

    out = FIGURES_DIR / "fig_combined.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


# ---------------------------------------------------------------------------
# Summary tables (markdown) — single source of numeric truth for the write-up
# ---------------------------------------------------------------------------
def write_summary_tables(runs, coverage, reasoning_stats, wall_times):
    lines = ["# Summary tables (generated by analysis/generate_graphs.py — do not hand-edit)\n"]

    lines.append("## Token usage, cost & wall time by run\n")
    lines.append("| Run | Input | Output | Cache write | Cache read | Cost (USD, proxy rates) | Wall time |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for k in KEYS:
        r = runs[k]
        wt = wall_times.get(k)
        wt_str = f"{wt/60:.0f} min" if wt else "unknown"
        lines.append(
            f"| {RUN_LABELS[k]} | {r['input']:,} | {r['output']:,} | "
            f"{r['cache_write']:,} | {r['cache_read']:,} | ${r['cost']:.2f} | {wt_str} |"
        )
    lines.append("")

    lines.append("## Reasoning ON vs OFF — csloop opus-4-6 tool-call outcomes\n")
    lines.append("| Condition | ok | errors | rejected | total | error rate | rejected rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for cond_key, cond_label in [("with_reasoning", "reasoning ON"), ("without_reasoning", "reasoning OFF")]:
        c = reasoning_stats[cond_key]
        tot = c["total"] or 1
        lines.append(
            f"| {cond_label} | {c['ok']} | {c['errors']} | {c['rejected']} | {c['total']} | "
            f"{100*c['errors']/tot:.1f}% | {100*c['rejected']/tot:.1f}% |"
        )
    lines.append("")

    lines.append("## Coverage & correctness by run\n")
    lines.append("| Run | Status | Files settled | Self-reported pass | Human-verified pass |")
    lines.append("|---|---|---:|---|---|")
    for k in KEYS:
        c = coverage[k]
        sp = f"{c['self_reported_pass'][0]}/{c['self_reported_pass'][1]}" if c["self_reported_pass"] else "—"
        vp = f"{c['human_verified_pass'][0]}/{c['human_verified_pass'][1]}" if c["human_verified_pass"] else "—"
        lines.append(f"| {RUN_LABELS[k]} | {c['final_status']} | {c['files_settled']} | {sp} | {vp} |")
    lines.append("")

    lines.append("## Runs excluded (never executed)\n")
    for run_dir in [
        "07-25-2028/csloop-gpt-5-4-effort-high",
        "07-25-2028/csloop-sonnet-4-6-with-reasoning-retries",
    ]:
        c = coverage_for_run(EXPERIMENTS / run_dir)
        lines.append(f"- `{run_dir}` — status: {c['final_status']} (no metadata, no agent_log.md, no logs)")
    lines.append("")

    out = Path(__file__).parent / "summary_tables.md"
    out.write_text("\n".join(lines))
    print(f"wrote {out}")


def main():
    runs, cc_rows, cs_rows = load_run_aggregates()
    print(f"ccworkflow rows: {len(cc_rows)}, csloop rows: {len(cs_rows)}")

    coverage = {k: coverage_for_run(EXPERIMENTS / k[0] / k[1]) for k in KEYS}
    for k, c in coverage.items():
        print(f"{k}: {c}")

    reasoning_stats = compute_reasoning_stats(cs_rows)
    wall_times = load_wall_times(cs_rows)
    for k, s in wall_times.items():
        print(f"{k}: wall time {s/60:.1f} min" if s else f"{k}: wall time unknown")

    make_standalone_figures(runs, coverage, reasoning_stats, wall_times)
    _bump_fonts_for_combined()
    make_combined_figure(runs, coverage, reasoning_stats, wall_times)
    write_summary_tables(runs, coverage, reasoning_stats, wall_times)


if __name__ == "__main__":
    main()
