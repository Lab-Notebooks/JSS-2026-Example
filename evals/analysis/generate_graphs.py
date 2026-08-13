#!/usr/bin/env python3.10
"""Generate the paper figures + summary tables for the 08-11/08-12-2026
evaluation of the mcfm-translate transformation: ccworkflow (sonnet-5 author /
opus-5 integrate) vs. csloop (opus-5, opus-5 +reasoning x2, and Kimi K3.5).

"Files settled" throughout is the exact count from git_file_counts.py (the
software/mcfm submodule branch for each run), not the agent's own in-loop
checklist in agent_log.md — the two can disagree (see git_file_counts.py's
docstring), and the submodule diff is ground truth.

Run with: python3.10 analysis/generate_graphs.py
(Needs Python 3.10+ for tomllib, or `pip install tomli` on older Pythons.)

Reads only from experiments/ (read-only). Writes, under analysis/figures/:
  fig1_cost_and_cache.png        - standalone, compact
  fig2_reasoning_tool_calls.png  - standalone, compact
  fig3_coverage.png              - standalone, compact
  fig4_wall_time.png             - standalone, compact
  fig5_tool_calls_per_file.png   - standalone, compact
  fig_combined.png               - all panels together, for single-figure use in a paper
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
from pricing import cost, PRICING
from git_file_counts import translated_file_count, translated_file_units, module_of

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
# Run identity / labeling — 08-11-2026 and 08-12-2026
# ---------------------------------------------------------------------------
DAY = "08-12-2026"  # the day used by the csloop with-reasoning/run2 comparison below
RUN_LABELS = {
    ("08-11-2026", "csloop-opus-5"): "csloop opus-5 (08-11)",
    ("08-11-2026", "csloop-opus-5-with-reasoning"): "csloop opus-5 +reasoning (08-11)",
    ("08-12-2026", "ccworkflow-sonnet-5-opus-5-integrate"): "ccworkflow (sonnet-5 author, opus-5 integrate)",
    ("08-12-2026", "ccworkflow-sonnet-5-opus-5-integrate-run2"): "ccworkflow (sonnet-5 author, opus-5 integrate, run2)",
    ("08-12-2026", "codescribe-opus-5-run2"): "csloop opus-5 (run2, 08-12)",
    ("08-12-2026", "codescribe-opus-5-with-reasoning"): "csloop opus-5 +reasoning (08-12)",
    ("08-12-2026", "codescribe-sonnet-5-with-reasoning"): "csloop sonnet-5 +reasoning (08-12)",
    ("08-12-2026", "codescribe-sonnet-5-with-reasoning-run2"): "csloop sonnet-5 +reasoning (run2, 08-12)",
    ("08-12-2026", "codescribe-kimi-k3-5"): "csloop Kimi K3.5",
}
# Short x-axis codes — keeps bars legible even in the compact standalone
# figures; each figure captions the full mapping once, below the plot.
RUN_CODES = {
    ("08-11-2026", "csloop-opus-5"): "R1",
    ("08-11-2026", "csloop-opus-5-with-reasoning"): "R2",
    ("08-12-2026", "ccworkflow-sonnet-5-opus-5-integrate"): "R3",
    ("08-12-2026", "ccworkflow-sonnet-5-opus-5-integrate-run2"): "R4",
    ("08-12-2026", "codescribe-opus-5-run2"): "R5",
    ("08-12-2026", "codescribe-opus-5-with-reasoning"): "R6",
    ("08-12-2026", "codescribe-sonnet-5-with-reasoning"): "R7",
    ("08-12-2026", "codescribe-sonnet-5-with-reasoning-run2"): "R8",
    ("08-12-2026", "codescribe-kimi-k3-5"): "R9",
}
RUN_CODE_CAPTION = (
    "R1 = csloop opus-5 (08-11)  |  R2 = csloop opus-5 +reasoning (08-11)  |  "
    "R3 = ccworkflow (sonnet-5 author, opus-5 integrate)  |  R4 = ccworkflow (…, run2)  |  "
    "R5 = csloop opus-5 (run2, 08-12)  |  R6 = csloop opus-5 +reasoning (08-12)  |  "
    "R7 = csloop sonnet-5 +reasoning (08-12)  |  R8 = csloop sonnet-5 +reasoning (run2, 08-12)  |  "
    "R9 = csloop Kimi K3.5"
)
KEYS = list(RUN_LABELS.keys())

MODEL_COLOR = {
    "claude-sonnet-5": CAT["blue"],
    "claude-opus-5": CAT["violet"],
}
UNPRICED_COLOR = MUTED


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
            "unpriced_models": set(),
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
        try:
            c = cost(
                model,
                row["input_tokens"],
                row["output_tokens"],
                row["cache_write_tokens"],
                row["cache_read_tokens"],
            )
        except KeyError:
            r["unpriced_models"].add(model)
            continue
        r["cost"] += c
        r["cost_by_model"][model] = r["cost_by_model"].get(model, 0.0) + c

    return runs, cc_rows, cs_rows


def compute_reasoning_stats(cs_rows):
    """csloop opus-5: +reasoning vs. run2 (the plain rerun) tool-call outcomes.
    Not a strict ON/OFF pair (run2 isn't explicitly labeled "no reasoning"), so
    panels below call this "with-reasoning vs. run2" rather than "ON vs OFF"."""
    with_r = [r for r in cs_rows if r["day"] == DAY and r["run_name"] == "codescribe-opus-5-with-reasoning"]
    run2 = [r for r in cs_rows if r["day"] == DAY and r["run_name"] == "codescribe-opus-5-run2"]

    def agg(rows):
        ok = sum(r["tool_ok"] for r in rows)
        errors = sum(r["tool_errors"] for r in rows)
        rejected = sum(r["tool_rejected"] for r in rows)
        return {"ok": ok, "errors": errors, "rejected": rejected, "total": ok + errors + rejected}

    return {"with_reasoning": agg(with_r), "run2": agg(run2)}


def _ccworkflow_wall_time_seconds(day, run_name):
    """Span between the first and last assistant-message timestamp across all
    agent-*.jsonl files in the run's workflow-wf_* dir."""
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
    """Sum of per-loop duration_s across author+review phases. csloop runs
    one loop at a time (no intra-run parallelism), so this sum approximates
    true elapsed engine time within a session."""
    return sum(r["duration_s"] for r in cs_rows if r["day"] == day and r["run_name"] == run_name)


def load_wall_times(cs_rows):
    wall_times = {}
    for day, run_name in KEYS:
        if "ccworkflow" in run_name:
            wall_times[(day, run_name)] = _ccworkflow_wall_time_seconds(day, run_name)
        else:
            wall_times[(day, run_name)] = _csloop_wall_time_seconds(cs_rows, day, run_name)
    return wall_times


def total_tool_calls(cc_rows, cs_rows, day, run_name):
    """Executed tool calls (ok + error), excluding policy-rejected calls that
    never ran, so the count is comparable across harnesses."""
    if "ccworkflow" in run_name:
        return sum(
            r["tool_ok"] + r["tool_error"]
            for r in cc_rows
            if r["day"] == day and r["run_name"] == run_name
        )
    return sum(
        r["tool_executed"]
        for r in cs_rows
        if r["day"] == day and r["run_name"] == run_name
    )


def load_files_settled():
    """Exact translated-file count per run, from the software/mcfm submodule
    branch (git_file_counts.py) — not the agent's self-reported checklist."""
    return {key: translated_file_count(*key) for key in KEYS}


def load_translated_units():
    """Exact list of translated-file identities per run (e.g. "BDK/M1bit1"),
    used to compare which specific files different runs picked."""
    return {key: translated_file_units(*key) for key in KEYS}


def modules_touched(translated_units):
    """{run: {module: file_count}} — which top-level src/ directories each
    run's translated files came from."""
    from collections import Counter
    return {k: Counter(module_of(u) for u in (units or [])) for k, units in translated_units.items()}


def pairwise_file_overlap(translated_units):
    """For every pair of runs that share at least one top-level module, the
    exact and set-based overlap of which files they translated. Pairs with no
    module in common are skipped — there's nothing to compare."""
    keys = list(translated_units.keys())
    pairs = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            set_a = set(translated_units[a] or [])
            set_b = set(translated_units[b] or [])
            modules_a = {module_of(u) for u in set_a}
            modules_b = {module_of(u) for u in set_b}
            shared_modules = sorted(modules_a & modules_b)
            if not shared_modules:
                continue
            overlap = set_a & set_b
            pairs.append({
                "a": a, "b": b,
                "shared_modules": shared_modules,
                "files_a": len(set_a), "files_b": len(set_b),
                "overlap": len(overlap),
                "overlap_files": sorted(overlap),
            })
    return pairs


def load_tool_calls_per_file(cc_rows, cs_rows, files_settled):
    result = {}
    for key in KEYS:
        day, run_name = key
        calls = total_tool_calls(cc_rows, cs_rows, day, run_name)
        files = files_settled[key]
        result[key] = {
            "tool_calls": calls,
            "files_settled": files,
            "per_file": (calls / files) if files else None,
        }
    return result


# ---------------------------------------------------------------------------
# Panel A — total cost by model
# ---------------------------------------------------------------------------
def draw_cost_panel(ax, runs, letter=None):
    labels = [RUN_CODES[k] for k in KEYS]
    x = range(len(KEYS))

    all_models_seen = []
    for k in KEYS:
        for m in runs[k]["cost_by_model"]:
            if m not in all_models_seen:
                all_models_seen.append(m)

    bottoms = [0.0] * len(KEYS)
    for model in all_models_seen:
        heights = [runs[k]["cost_by_model"].get(model, 0.0) for k in KEYS]
        ax.bar(x, heights, bottom=bottoms, width=0.6, color=MODEL_COLOR.get(model, CAT["aqua"]),
               edgecolor=SURFACE, linewidth=1)
        bottoms = [b + h for b, h in zip(bottoms, heights)]

    for xi, k in zip(x, KEYS):
        total = bottoms[xi]
        label = f"${total:.2f}"
        if runs[k]["unpriced_models"]:
            label += "\n(+ unpriced tokens)"
        ax.text(xi, total + max(bottoms) * 0.03, label, ha="center", va="bottom",
                fontsize=ANNOT_SIZE, color=INK_SECONDARY)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("USD (proxy rates)")
    ax.set_title(_title("Total cost by model", letter))
    ax.set_ylim(0, max(bottoms) * 1.3)
    handles = [mpatches.Patch(color=MODEL_COLOR.get(m, CAT["aqua"]), label=m) for m in all_models_seen]
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
# Panel C/D — csloop opus-5: +reasoning vs. run2 tool-call outcomes
# ---------------------------------------------------------------------------
def draw_reasoning_counts_panel(ax, stats, letter=None):
    labels = ["opus-5\n+reasoning", "opus-5\nrun2"]
    x = [0, 1]
    outcome_colors = {"ok": STATUS["good"], "errors": STATUS["critical"], "rejected": STATUS["warning"]}
    ok_vals = [stats["with_reasoning"]["ok"], stats["run2"]["ok"]]
    err_vals = [stats["with_reasoning"]["errors"], stats["run2"]["errors"]]
    rej_vals = [stats["with_reasoning"]["rejected"], stats["run2"]["rejected"]]

    ax.bar(x, ok_vals, width=0.5, color=outcome_colors["ok"], label="ok")
    ax.bar(x, err_vals, width=0.5, bottom=ok_vals, color=outcome_colors["errors"], label="errors")
    bottom2 = [a + b for a, b in zip(ok_vals, err_vals)]
    ax.bar(x, rej_vals, width=0.5, bottom=bottom2, color=outcome_colors["rejected"], label="rejected")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Tool calls (count)")
    ax.set_title(_title("csloop opus-5: raw tool-call outcomes", letter))
    ax.legend(frameon=False, loc="upper left")


def draw_reasoning_rate_panel(ax, stats, letter=None):
    labels = ["opus-5\n+reasoning", "opus-5\nrun2"]
    x = [0, 1]
    outcome_colors = {"ok": STATUS["good"], "errors": STATUS["critical"], "rejected": STATUS["warning"]}

    def rates(cond):
        tot = stats[cond]["total"] or 1
        return (100 * stats[cond]["ok"] / tot, 100 * stats[cond]["errors"] / tot, 100 * stats[cond]["rejected"] / tot)

    r_ok, r_err, r_rej = zip(*[rates("with_reasoning"), rates("run2")])
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
    ax.set_title(_title("csloop opus-5: outcome rate", letter))


# ---------------------------------------------------------------------------
# Panel E — files translated
# ---------------------------------------------------------------------------
def draw_files_panel(ax, files_settled, letter=None):
    labels = [RUN_CODES[k] for k in KEYS]
    x = list(range(len(KEYS)))
    harness_color = {"ccworkflow": CAT["blue"], "csloop": CAT["orange"]}
    settled = [files_settled[k] or 0 for k in KEYS]
    colors = [harness_color["ccworkflow"] if "ccworkflow" in k[1] else harness_color["csloop"] for k in KEYS]

    ax.bar(x, settled, width=0.6, color=colors, edgecolor=SURFACE, linewidth=1)
    for xi, s in zip(x, settled):
        ax.text(xi, s + max(settled) * 0.03, str(s), ha="center", fontsize=ANNOT_SIZE, color=INK_SECONDARY)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Files settled (git-exact)")
    ax.set_ylim(0, max(settled) * 1.2)
    ax.set_title(_title("Files translated", letter))
    handles = [
        mpatches.Patch(color=harness_color["ccworkflow"], label="ccworkflow"),
        mpatches.Patch(color=harness_color["csloop"], label="csloop"),
    ]
    ax.legend(handles=handles, frameon=False, loc="upper left")


# ---------------------------------------------------------------------------
# Panel F — claimed correctness (self-reported; no human_review present for
# these runs, so there's no verified-vs-claimed comparison to draw here)
# ---------------------------------------------------------------------------
def draw_correctness_panel(ax, coverage, letter=None):
    plot_keys = [k for k in KEYS if coverage[k]["self_reported_pass"]]
    px = list(range(len(plot_keys)))

    for i, k in enumerate(plot_keys):
        sp = coverage[k]["self_reported_pass"]
        pct = 100 * sp[0] / sp[1]
        ax.bar(i, pct, width=0.5, color=CAT["blue"], edgecolor=SURFACE, linewidth=0.5)
        ax.text(i, pct + 3, f"{sp[0]}/{sp[1]}", ha="center", va="bottom",
                fontsize=ANNOT_SIZE, color=INK_SECONDARY)

    ax.set_xticks(px)
    ax.set_xticklabels([RUN_CODES[k] for k in plot_keys])
    ax.set_ylabel("mcfm test pass rate (%)")
    ax.set_ylim(0, 122)
    ax.set_title(_title("Self-reported correctness", letter))


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
# Panel H — tool calls per file settled
# ---------------------------------------------------------------------------
def draw_tool_calls_per_file_panel(ax, tool_calls_per_file, letter=None):
    labels = [RUN_CODES[k] for k in KEYS]
    x = list(range(len(KEYS)))
    harness_color = {"ccworkflow": CAT["blue"], "csloop": CAT["orange"]}
    per_file = [tool_calls_per_file[k]["per_file"] or 0 for k in KEYS]
    colors = [harness_color["ccworkflow"] if "ccworkflow" in k[1] else harness_color["csloop"] for k in KEYS]

    ax.bar(x, per_file, width=0.5, color=colors, edgecolor=SURFACE, linewidth=1)
    for xi, k in zip(x, KEYS):
        v = tool_calls_per_file[k]
        label = f"{v['per_file']:.0f}" if v["per_file"] is not None else "n/a\n(0 files)"
        ax.text(xi, (v["per_file"] or 0) + max(per_file) * 0.03, label,
                ha="center", fontsize=ANNOT_SIZE, color=INK_SECONDARY)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Tool calls per file settled")
    ax.set_ylim(0, max(per_file) * 1.25)
    ax.set_title(_title("Tool-call cost per file", letter))
    handles = [
        mpatches.Patch(color=harness_color["ccworkflow"], label="ccworkflow"),
        mpatches.Patch(color=harness_color["csloop"], label="csloop"),
    ]
    ax.legend(handles=handles, loc="upper right", frameon=False, ncol=2)


# ---------------------------------------------------------------------------
# Standalone compact figures
# ---------------------------------------------------------------------------
def save_fig(fig, name, caption_lines):
    line_gap = 0.05
    for i, line in enumerate(reversed(caption_lines)):
        fig.text(0.5, 0.01 + i * line_gap, line, ha="center", fontsize=CAPTION_SIZE, color=INK, wrap=True)
    out = FIGURES_DIR / name
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def make_standalone_figures(runs, coverage, files_settled, reasoning_stats, wall_times, tool_calls_per_file):
    # Fig 1 — cost & cache
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.2, 4.2))
    fig.suptitle("Token cost & cache efficiency", fontsize=SUPTITLE_SIZE)
    draw_cost_panel(a1, runs)
    draw_cache_panel(a2, runs)
    fig.tight_layout(rect=[0, 0.20, 1, 0.90])
    save_fig(fig, "fig1_cost_and_cache.png", [
        RUN_CODE_CAPTION,
        "Kimi K3.5 is not an Anthropic model and is excluded from USD cost (no rate card here on purpose).",
    ])

    # Fig 2 — csloop opus-5: +reasoning vs run2
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.6, 3.9))
    fig.suptitle("csloop opus-5: +reasoning vs. run2", fontsize=SUPTITLE_SIZE)
    draw_reasoning_counts_panel(a1, reasoning_stats)
    draw_reasoning_rate_panel(a2, reasoning_stats)
    fig.tight_layout(rect=[0, 0.16, 1, 0.90])
    save_fig(fig, "fig2_reasoning_tool_calls.png", [
        "run2 is a plain rerun, not an explicit reasoning-OFF condition — comparison shown as-is.",
    ])

    # Fig 3 — coverage
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.6, 3.9))
    fig.suptitle("Coverage & correctness", fontsize=SUPTITLE_SIZE)
    draw_files_panel(a1, files_settled)
    draw_correctness_panel(a2, coverage)
    fig.tight_layout(rect=[0, 0.16, 1, 0.90])
    save_fig(fig, "fig3_coverage.png", [
        RUN_CODE_CAPTION,
        "No human_review files exist for these runs, so only self-reported pass rates are shown.",
    ])

    # Fig 4 — wall time
    fig, a1 = plt.subplots(figsize=(5.2, 4.0))
    fig.suptitle("Wall-clock time", fontsize=SUPTITLE_SIZE)
    draw_wall_time_panel(a1, wall_times)
    a1.set_title("")
    fig.tight_layout(rect=[0, 0.22, 1, 0.90])
    save_fig(fig, "fig4_wall_time.png", [
        RUN_CODE_CAPTION,
        "ccworkflow: span of first-to-last agent timestamp. csloop: sum of per-loop duration_s.",
    ])

    # Fig 5 — tool calls per file
    fig, a1 = plt.subplots(figsize=(5.2, 4.0))
    fig.suptitle("Tool-call cost per file", fontsize=SUPTITLE_SIZE)
    draw_tool_calls_per_file_panel(a1, tool_calls_per_file)
    a1.set_title("")
    fig.tight_layout(rect=[0, 0.22, 1, 0.90])
    save_fig(fig, "fig5_tool_calls_per_file.png", [
        RUN_CODE_CAPTION,
        "Executed tool calls (ok + error) divided by files settled (git-exact count, git_file_counts.py).",
    ])


# ---------------------------------------------------------------------------
# Combined single figure
# ---------------------------------------------------------------------------
def _bump_fonts_for_combined(scale=1.15):
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


def make_combined_figure(runs, coverage, files_settled, reasoning_stats, wall_times, tool_calls_per_file):
    fig = plt.figure(figsize=(11, 13.5))
    gs = fig.add_gridspec(4, 2, hspace=0.55, wspace=0.32, top=0.94, bottom=0.05, left=0.09, right=0.98)

    draw_cost_panel(fig.add_subplot(gs[0, 0]), runs, letter="(a)")
    draw_cache_panel(fig.add_subplot(gs[0, 1]), runs, letter="(b)")
    draw_reasoning_counts_panel(fig.add_subplot(gs[1, 0]), reasoning_stats, letter="(c)")
    draw_reasoning_rate_panel(fig.add_subplot(gs[1, 1]), reasoning_stats, letter="(d)")
    draw_files_panel(fig.add_subplot(gs[2, 0]), files_settled, letter="(e)")
    draw_wall_time_panel(fig.add_subplot(gs[2, 1]), wall_times, letter="(f)")
    draw_tool_calls_per_file_panel(fig.add_subplot(gs[3, 0]), tool_calls_per_file, letter="(g)")
    draw_correctness_panel(fig.add_subplot(gs[3, 1]), coverage, letter="(h)")

    fig.suptitle(
        "08-11/08-12-2026: ccworkflow vs. csloop on mcfm-translate — cost, cache, tool calls & coverage",
        fontsize=SUPTITLE_SIZE + 2,
        y=0.985,
    )
    fig.text(0.5, 0.025, RUN_CODE_CAPTION, ha="center", fontsize=CAPTION_SIZE * 1.55, color=INK)
    fig.text(0.5, 0.005, "Kimi K3.5 tokens are excluded from USD cost (non-Anthropic, no rate card here).",
              ha="center", fontsize=CAPTION_SIZE * 1.55, color=INK)

    out = FIGURES_DIR / "fig_combined.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


# ---------------------------------------------------------------------------
# Summary tables (markdown) — single source of numeric truth for the write-up
# ---------------------------------------------------------------------------
def write_summary_tables(runs, coverage, files_settled, translated_units, reasoning_stats, wall_times, tool_calls_per_file):
    lines = ["# Summary tables (generated by analysis/generate_graphs.py — do not hand-edit)\n"]

    lines.append("## Run comparison: cost, cache, wall time, tool calls & files settled\n")
    lines.append(
        "| Run | Cost (USD, proxy rates) | Cache-read share | Wall time | Tool calls / file | "
        "Files settled (git-exact) | Time / file | Cost / file |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for k in KEYS:
        r = runs[k]
        wt = wall_times.get(k)
        t = tool_calls_per_file[k]
        files = files_settled[k]
        total_input_side = r["input"] + r["cache_write"] + r["cache_read"]
        share = 100.0 * r["cache_read"] / total_input_side if total_input_side else 0.0
        cost_str = f"${r['cost']:.2f}"
        if r["unpriced_models"]:
            cost_str += " (n/a, non-Anthropic)"
        wt_str = f"{wt/60:.0f} min" if wt else "unknown"
        per_file_str = f"{t['per_file']:.1f}" if t["per_file"] is not None else "—"
        time_per_file_str = f"{wt/60/files:.1f} min" if (wt and files) else "—"
        if files and not r["unpriced_models"]:
            cost_per_file_str = f"${r['cost']/files:.2f}"
        elif r["unpriced_models"]:
            cost_per_file_str = "n/a"
        else:
            cost_per_file_str = "—"
        lines.append(
            f"| {RUN_LABELS[k].replace(chr(10), ' ')} | {cost_str} | {share:.0f}% | {wt_str} | "
            f"{per_file_str} | {files if files is not None else '—'} | {time_per_file_str} | {cost_per_file_str} |"
        )
    lines.append("")

    lines.append("## Token usage, cost, cache & wall time detail\n")
    lines.append("| Run | Input | Output | Cache write | Cache read | Cache-read share | Cost (USD, proxy rates) | Wall time |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for k in KEYS:
        r = runs[k]
        wt = wall_times.get(k)
        wt_str = f"{wt/60:.0f} min" if wt else "unknown"
        total_input_side = r["input"] + r["cache_write"] + r["cache_read"]
        share = 100.0 * r["cache_read"] / total_input_side if total_input_side else 0.0
        cost_str = f"${r['cost']:.2f}"
        if r["unpriced_models"]:
            cost_str += f" (+ tokens from {', '.join(sorted(r['unpriced_models']))}, not priced)"
        lines.append(
            f"| {RUN_LABELS[k].replace(chr(10), ' ')} | {r['input']:,} | {r['output']:,} | "
            f"{r['cache_write']:,} | {r['cache_read']:,} | {share:.0f}% | {cost_str} | {wt_str} |"
        )
    lines.append("")

    lines.append("## Cost by model\n")
    lines.append("| Run | " + " | ".join(sorted(PRICING.keys())) + " |")
    lines.append("|---|" + "---:|" * len(PRICING))
    for k in KEYS:
        r = runs[k]
        cells = [f"${r['cost_by_model'].get(m, 0.0):.2f}" for m in sorted(PRICING.keys())]
        lines.append(f"| {RUN_LABELS[k].replace(chr(10), ' ')} | " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## csloop opus-5: +reasoning vs. run2 tool-call outcomes (08-12-2026)\n")
    lines.append("| Condition | ok | errors | rejected | total | error rate | rejected rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for cond_key, cond_label in [("with_reasoning", "opus-5 +reasoning"), ("run2", "opus-5 run2")]:
        c = reasoning_stats[cond_key]
        tot = c["total"] or 1
        lines.append(
            f"| {cond_label} | {c['ok']} | {c['errors']} | {c['rejected']} | {c['total']} | "
            f"{100*c['errors']/tot:.1f}% | {100*c['rejected']/tot:.1f}% |"
        )
    lines.append("")

    lines.append("## Status & self-reported correctness\n")
    lines.append("| Run | Status | Self-reported pass |")
    lines.append("|---|---|---|")
    for k in KEYS:
        c = coverage[k]
        sp = f"{c['self_reported_pass'][0]}/{c['self_reported_pass'][1]}" if c["self_reported_pass"] else "—"
        lines.append(f"| {RUN_LABELS[k].replace(chr(10), ' ')} | {c['final_status']} | {sp} |")
    lines.append("")

    mods = modules_touched(translated_units)
    all_modules = sorted({m for counts in mods.values() for m in counts})
    lines.append("## Which src/ module each run translated files from (git-exact)\n")
    lines.append(
        "Which top-level `software/mcfm/src/` directory each run's translated files came from — "
        "shows whether runs converged on the same module or scattered across different ones.\n"
    )
    lines.append("| Run | " + " | ".join(all_modules) + " | Total |")
    lines.append("|---|" + "---:|" * (len(all_modules) + 1))
    for k in KEYS:
        counts = mods[k]
        cells = [str(counts.get(m, 0) or "") for m in all_modules]
        lines.append(f"| {RUN_LABELS[k].replace(chr(10), ' ')} | " + " | ".join(cells) + f" | {sum(counts.values())} |")
    lines.append("")

    overlaps = pairwise_file_overlap(translated_units)
    lines.append("## File-level overlap between runs sharing a module (git-exact)\n")
    lines.append(
        "For every pair of runs that translated files from at least one of the same modules: how many of "
        "the *exact same files* they both picked, vs. how many files each translated in total. High overlap "
        "relative to the smaller run's total means the two runs converged on the same files; low overlap "
        "despite a shared module means they diverged within it.\n"
    )
    lines.append("| Run A | Run B | Shared module(s) | Files (A) | Files (B) | Overlap | Overlap / min(A,B) |")
    lines.append("|---|---|---|---:|---:|---:|---:|")
    for p in sorted(overlaps, key=lambda p: -p["overlap"]):
        denom = min(p["files_a"], p["files_b"]) or 1
        lines.append(
            f"| {RUN_LABELS[p['a']].replace(chr(10), ' ')} | {RUN_LABELS[p['b']].replace(chr(10), ' ')} | "
            f"{', '.join(p['shared_modules'])} | {p['files_a']} | {p['files_b']} | {p['overlap']} | "
            f"{100*p['overlap']/denom:.0f}% |"
        )
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

    files_settled = load_files_settled()
    for k, f in files_settled.items():
        print(f"{k}: files settled (git-exact) = {f}")

    translated_units = load_translated_units()

    reasoning_stats = compute_reasoning_stats(cs_rows)
    wall_times = load_wall_times(cs_rows)
    for k, s in wall_times.items():
        print(f"{k}: wall time {s/60:.1f} min" if s else f"{k}: wall time unknown")

    tool_calls_per_file = load_tool_calls_per_file(cc_rows, cs_rows, files_settled)
    for k, t in tool_calls_per_file.items():
        print(f"{k}: {t}")

    make_standalone_figures(runs, coverage, files_settled, reasoning_stats, wall_times, tool_calls_per_file)
    _bump_fonts_for_combined()
    make_combined_figure(runs, coverage, files_settled, reasoning_stats, wall_times, tool_calls_per_file)
    write_summary_tables(runs, coverage, files_settled, translated_units, reasoning_stats, wall_times, tool_calls_per_file)


if __name__ == "__main__":
    main()
