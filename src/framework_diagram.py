"""Conceptual (XLRM-style) system diagram of the measurement study.

Levers here are the analyst's measurement choices, swept systematically in
src/robustness.py; exogenous factors are properties of the data generation
that no specification can vary.

Run from the repo root: python src/framework_diagram.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, FancyBboxPatch

INK, SUB, SURFACE, EDGE = "#0b0b0b", "#52514e", "#fcfcfb", "#c3c2b7"

LEVERS = [
    "L1: Utility workforce definition\n      (core 11 / 51-80xx / extended)",
    "L2: Information-task rule\n      (any / majority / strict)",
    "L3: Monitoring & inspection\n      (information vs physical)",
    "L4: Usage threshold (>0 / .5 / .8)",
    "L5: Unmatched tasks (zero / drop)",
    "L6: Task weighting (equal / importance)",
]
EXOGENOUS = [
    "X1: Claude-only platform coverage",
    "X2: Usage gate (≥100) & privacy suppression",
    "X3: Work-context classifier accuracy",
    "X4: Utility IT / security / procurement regimes",
    "X5: O*NET task vintage & crosswalk",
]
RELATIONSHIPS = ("O*NET tasks → work-activity classification\n"
                 "→ join to observed Claude usage\n"
                 "→ aggregate to occupation sets\n"
                 "→ utility vs economy comparison")
METRICS = [
    "M1: Share of utility information\n      tasks with any usage",
    "M2: Same share, economy-wide",
    "M3: Utility–economy gap (ratio)",
    "M4: Size of the feasible margin\n      (info share of utility work)",
]


def block(ax, x, y, w, h, title, lines, fontsize=8.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012",
                                facecolor="white", edgecolor=EDGE, linewidth=1))
    ax.text(x + w / 2, y + h - 0.035, title, ha="center", va="top",
            fontweight="bold", fontsize=10, color=INK)
    ax.text(x + 0.015, y + h - 0.09, "\n".join(lines), ha="left", va="top",
            fontsize=fontsize, color=SUB, linespacing=1.55)


def main() -> None:
    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    fig.patch.set_facecolor(SURFACE)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    block(ax, 0.01, 0.24, 0.27, 0.52,
          "MEASUREMENT LEVERS (L)", LEVERS)
    ax.text(0.145, 0.19, "analyst choices, swept in the\n216-specification ensemble",
            ha="center", va="top", fontsize=8, color=SUB, style="italic")

    block(ax, 0.345, 0.72, 0.31, 0.27, "EXOGENOUS FACTORS (X)",
          EXOGENOUS, fontsize=8.2)

    block(ax, 0.365, 0.30, 0.27, 0.30, "RELATIONSHIPS (R)",
          [RELATIONSHIPS], fontsize=8.6)

    block(ax, 0.72, 0.28, 0.27, 0.44, "OUTCOME METRICS (M)", METRICS)

    arrow_style = dict(width=0.012, head_width=0.035, head_length=0.018,
                       color=EDGE, length_includes_head=True)
    ax.add_patch(FancyArrow(0.29, 0.45, 0.06, 0, **arrow_style))
    ax.add_patch(FancyArrow(0.5, 0.71, 0, -0.09, **arrow_style))
    ax.add_patch(FancyArrow(0.645, 0.45, 0.06, 0, **arrow_style))

    ax.set_title("System diagram: measuring the AI adoption gap in utility work",
                 loc="left", fontweight="bold", fontsize=12, color=INK)
    fig.tight_layout()
    out = Path(__file__).resolve().parents[1] / "figures" / "framework.png"
    fig.savefig(out, bbox_inches="tight", dpi=150, facecolor=SURFACE)
    print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
