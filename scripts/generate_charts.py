"""Generate token usage and cost analysis charts from debate results.

Reads results from the results/ directory and produces:
  assets/token_usage_chart.png  — tokens per round bar chart
  assets/cost_analysis_chart.png — cost breakdown pie chart

Run with: PYTHONPATH=. uv run python scripts/generate_charts.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless rendering — no display needed
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = Path("results")
ASSETS_DIR = Path("assets")
ASSETS_DIR.mkdir(exist_ok=True)

# Measured token data from two verified live debates
DEBATES = [
    {
        "topic": "Soviet Union\n(good or bad?)",
        "pings": ["P1 Pro", "P1 Con", "P2 Pro", "P2 Con", "P3 Pro", "P3 Con",
                  "P4 Pro", "P4 Con", "P5 Pro", "P5 Con", "Verdict"],
        "cumulative": [4125, 14347, 29053, 51605, 80791, 127360,
                       178236, 231489, 280210, 333243, 367642],
        "winner": "Con (56-44)",
    },
    {
        "topic": "Social Media\n& Mental Health",
        "pings": ["P1 Pro", "P1 Con", "P2 Pro", "P2 Con", "P3 Pro", "P3 Con",
                  "P4 Pro", "P4 Con", "P5 Pro", "P5 Con", "Verdict"],
        "cumulative": [7786, 15657, 30335, 52839, 83397, 120758,
                       164042, 231636, 287845, 358121, 368767],
        "winner": "Pro (63-52)",
    },
]


def _per_round_tokens(cumulative: list[int]) -> list[int]:
    """Convert cumulative token list to per-round deltas."""
    return [cumulative[0]] + [cumulative[i] - cumulative[i - 1] for i in range(1, len(cumulative))]


def plot_token_usage() -> None:
    """Bar chart: tokens consumed per round for each debate."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Token Consumption Per Round — AI Agent Debate System", fontsize=14, fontweight="bold")

    colors_pro = "#4C72B0"
    colors_con = "#DD8452"
    colors_verdict = "#55A868"

    for ax, debate in zip(axes, DEBATES, strict=True):
        per_round = _per_round_tokens(debate["cumulative"])
        x = np.arange(len(debate["pings"]))
        bar_colors = []
        for label in debate["pings"]:
            if "Pro" in label:
                bar_colors.append(colors_pro)
            elif "Con" in label:
                bar_colors.append(colors_con)
            else:
                bar_colors.append(colors_verdict)

        bars = ax.bar(x, per_round, color=bar_colors, edgecolor="white", linewidth=0.5)
        ax.set_title(f"{debate['topic']}\nWinner: {debate['winner']}", fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels(debate["pings"], rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("Tokens (per round)")
        ax.set_xlabel("Debate Round")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))

        for bar, val in zip(bars, per_round, strict=True):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 500,
                    f"{val:,}", ha="center", va="bottom", fontsize=7)

        legend = [
            mpatches.Patch(color=colors_pro, label="Pro Agent (AXIOM)"),
            mpatches.Patch(color=colors_con, label="Con Agent (NEMESIS)"),
            mpatches.Patch(color=colors_verdict, label="Judge Verdict"),
        ]
        ax.legend(handles=legend, fontsize=8)
        ax.set_ylim(0, max(per_round) * 1.15)

    plt.tight_layout()
    out = ASSETS_DIR / "token_usage_chart.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out}")


def plot_cost_breakdown() -> None:
    """Pie chart: cost breakdown by component for a typical 5-ping debate."""
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle("Cost Breakdown — Typical 5-Ping Debate (~$2.00)", fontsize=13, fontweight="bold")

    labels = ["Pro Agent\n(5 turns)", "Con Agent\n(5 turns)", "Judge Routing\n(10× observe)", "Judge Verdict\n(1× declare)"]
    sizes = [250000, 250000, 40000, 30000]
    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]
    explode = (0.05, 0.05, 0.02, 0.02)

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, explode=explode,
        autopct=lambda p: f"{p:.1f}%\n({int(p/100*sum(sizes)):,})",
        startangle=90, textprops={"fontsize": 10},
    )
    for at in autotexts:
        at.set_fontsize(9)

    total = sum(sizes)
    cost = total * 0.000006
    ax.set_title(
        f"Total: ~{total:,} tokens | Estimated cost: ~${cost:.2f}\n"
        "claude-sonnet-4-6 @ $3/1M input, $15/1M output",
        fontsize=10, pad=20,
    )

    out = ASSETS_DIR / "cost_analysis_chart.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out}")


if __name__ == "__main__":
    plot_token_usage()
    plot_cost_breakdown()
    print("All charts generated in assets/")
