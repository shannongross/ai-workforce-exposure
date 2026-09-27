"""Exploratory look at the raw ingredients, before any CI analysis.

Produces both static figures for the paper (figures/eda/*.png) and one
self-contained interactive page (docs/index.html) that GitHub Pages can
serve. Only occupation-level aggregates are embedded in the page; raw
data stays local.

Run from the repo root: python src/eda.py
"""

import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
FIGS = ROOT / "figures" / "eda"
DOCS = ROOT / "docs"

# palette: categorical slots 1-3 (blue = all occupations, orange = utility
# core, aqua = extended utility workforce); ink/grid tokens from the same
# reference palette. Three slots validate all-pairs for scatters.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "figure.dpi": 150,
})


def load_exposure() -> pd.DataFrame:
    df = pd.read_csv(RAW / "economic_index/labor_market_impacts/job_exposure.csv")
    soc = pd.read_csv(RAW / "economic_index/release_2025_02_10/SOC_Structure.csv")
    major = (soc.dropna(subset=["Major Group"])
             .assign(major=lambda d: d["Major Group"].str[:2])
             .set_index("major")["SOC or O*NET-SOC 2019 Title"].to_dict())
    df["major"] = df["occ_code"].str[:2]
    df["major_title"] = df["major"].map(major).str.replace(" Occupations", "", regex=False)
    return df


def load_oews() -> pd.DataFrame:
    with zipfile.ZipFile(RAW / "oews/oesm25nat.zip") as z:
        with z.open("oesm25nat/national_M2025_dl.xlsx") as f:
            oews = pd.read_excel(f)
    oews = oews[oews["O_GROUP"] == "detailed"][["OCC_CODE", "TOT_EMP", "A_MEDIAN"]]
    for c in ["TOT_EMP", "A_MEDIAN"]:
        oews[c] = pd.to_numeric(oews[c], errors="coerce")  # '*'/'#' = suppressed
    return oews.rename(columns={"OCC_CODE": "occ_code"})


def shorten(s: pd.Series, n: int) -> pd.Series:
    return s.where(s.str.len() <= n,
                   s.str.slice(0, n).str.rsplit(" ", n=1).str[0] + "…")


def fig_distribution(exp: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), width_ratios=[1, 1.4])
    axes[0].hist(exp["observed_exposure"], bins=40, color=BLUE)
    axes[0].set_xlabel("Observed exposure")
    axes[0].set_ylabel("Occupations")
    axes[0].set_title("Most occupations sit near zero", loc="left")

    top = exp.nlargest(15, "observed_exposure").iloc[::-1]
    axes[1].barh(shorten(top["title"], 42), top["observed_exposure"],
                 color=BLUE, height=0.62)
    axes[1].set_xlabel("Observed exposure")
    axes[1].set_title("Top 15 occupations", loc="left")
    fig.suptitle("Observed AI exposure across 756 occupations (Anthropic Economic Index)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGS / "exposure_distribution.png", bbox_inches="tight")
    plt.close(fig)


def fig_by_group(exp: pd.DataFrame):
    order = (exp.groupby("major_title")["observed_exposure"]
             .median().sort_values().index)
    fig, ax = plt.subplots(figsize=(9, 7))
    data = [exp.loc[exp["major_title"] == g, "observed_exposure"] for g in order]
    bp = ax.boxplot(data, vert=False, tick_labels=order, patch_artist=True,
                    medianprops={"color": INK}, flierprops={"markersize": 3,
                    "markerfacecolor": MUTED, "markeredgecolor": "none"})
    for box in bp["boxes"]:
        box.set(facecolor=BLUE, alpha=0.75, edgecolor="none")
    ax.set_xlabel("Observed exposure")
    ax.set_title("Exposure by major occupation group (SOC 2-digit)",
                 loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "exposure_by_group.png", bbox_inches="tight")
    plt.close(fig)


def fig_task_gate():
    pen = pd.read_csv(RAW / "economic_index/labor_market_impacts/task_penetration.csv")
    nz = pen[pen["penetration"] > 0]["penetration"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(nz, bins=25, color=BLUE)
    ax.set_xlabel("Task-level exposure (nonzero tasks only)")
    ax.set_ylabel("Tasks")
    ax.set_title(f"The usage gate zeroes out most tasks: {len(nz):,} of {len(pen):,} "
                 f"pass; survivors lie in [0.5, 1]", loc="left", fontweight="bold")
    ax.annotate("α floor: augmentation-only\nusage scores 0.5",
                xy=(0.5, 30), xytext=(0.55, 120), color="#52514e",
                arrowprops={"arrowstyle": "->", "color": MUTED})
    fig.tight_layout()
    fig.savefig(FIGS / "task_gate.png", bbox_inches="tight")
    plt.close(fig)
    return len(nz), len(pen)


def fig_interaction_types() -> pd.DataFrame:
    aa = pd.read_csv(RAW / "economic_index/release_2025_02_10/automation_vs_augmentation.csv")
    aa = aa.sort_values("pct")
    # AEI classification: directive + feedback loop = automation-like;
    # task iteration + learning + validation = augmentation-like
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.barh(aa["interaction_type"], aa["pct"], color=BLUE, height=0.62)
    for _, r in aa.iterrows():
        ax.text(r["pct"] + 0.4, r["interaction_type"], f"{r['pct']:.0f}%",
                va="center", color="#52514e", fontsize=9)
    ax.set_xlabel("Share of Claude.ai conversations (%)")
    ax.set_title("Interaction types, economy-wide (Feb 2025 release)",
                 loc="left", fontweight="bold")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(FIGS / "interaction_types.png", bbox_inches="tight")
    plt.close(fig)
    return aa


def fig_wage_scatter(exp: pd.DataFrame, oews: pd.DataFrame) -> pd.DataFrame:
    df = exp.merge(oews, on="occ_code", how="inner").dropna(subset=["A_MEDIAN"])
    print(f"wage scatter: {len(df)} of {len(exp)} occupations have OEWS wage data")
    fig, ax = plt.subplots(figsize=(8, 5.5))
    size = (df["TOT_EMP"] / df["TOT_EMP"].max()) * 600 + 6
    ax.scatter(df["A_MEDIAN"], df["observed_exposure"], s=size,
               color=BLUE, alpha=0.45, edgecolors="none")
    ax.set_xscale("log")
    ax.set_xlabel("Median annual wage, May 2025 (log scale, USD)")
    ax.set_ylabel("Observed exposure")
    ax.set_title("Exposure vs. wage (point size = employment)",
                 loc="left", fontweight="bold")
    labeled = df.nlargest(3, "observed_exposure")
    for (_, r), dy in zip(labeled.iterrows(), (3, 3, -10)):
        ax.annotate(shorten(pd.Series([r["title"]]), 34)[0],
                    (r["A_MEDIAN"], r["observed_exposure"]),
                    fontsize=7.5, color="#52514e",
                    xytext=(6, dy), textcoords="offset points")
    fig.tight_layout()
    fig.savefig(FIGS / "exposure_vs_wage.png", bbox_inches="tight")
    plt.close(fig)
    return df


def fig_reproduction() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data/processed/exposure_baseline.csv")
    recon = df.columns[df.columns.str.startswith("exposure_")][0]
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.plot([0, 0.8], [0, 0.8], color=MUTED, linewidth=1, linestyle="--")
    ax.scatter(df["observed_exposure"], df[recon], s=14, color=BLUE,
               alpha=0.5, edgecolors="none")
    df["gap"] = df[recon] - df["observed_exposure"]
    outliers = pd.concat([df.nlargest(3, "gap"), df.nsmallest(3, "gap")])
    for (_, r), dy in zip(outliers.iterrows(), (5, -4, -13, 5, -4, -13)):
        ax.annotate(shorten(pd.Series([r["title"]]), 34)[0],
                    (r["observed_exposure"], r[recon]),
                    fontsize=7.5, color="#52514e",
                    xytext=(6, dy), textcoords="offset points")
    ax.set_xlabel("Published observed exposure (Anthropic)")
    ax.set_ylabel("Our reconstruction from public task data")
    ax.set_title("Reconstruction diverges where unpublished inputs bind\n"
                 "(Spearman ρ = 0.87)", loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "reproduction_diagnostic.png", bbox_inches="tight")
    plt.close(fig)
    return df


def load_analysis() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data/processed/analysis.csv")
    df["group"] = "All other occupations"
    df.loc[df["utility_workforce"] == True, "group"] = "Utility workforce (extended)"
    df.loc[df["utility_core"] == True, "group"] = "Utility core"
    return df


def fig_utility_core(ana: pd.DataFrame):
    """The 11 operational-core occupations: exposure, with employment and
    wage as context. The story is the wall of zeros."""
    core = (ana[ana["utility_core"] == True]
            .sort_values(["observed_exposure", "emp_national"]))
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = [f"{shorten(pd.Series([t]), 46)[0]}   "
              f"({e / 1000:.0f}k workers)" for t, e in
              zip(core["title"], core["emp_national"])]
    ax.barh(labels, core["observed_exposure"], color=ORANGE, height=0.62)
    ax.axvline(ana["observed_exposure"].mean(), color=MUTED, linewidth=1,
               linestyle="--")
    ax.annotate(f"economy-wide mean ({ana['observed_exposure'].mean():.3f})",
                xy=(ana["observed_exposure"].mean(), 0.2), xytext=(4, 0),
                textcoords="offset points", color="#52514e", fontsize=8.5)
    for i, v in enumerate(core["observed_exposure"]):
        if v == 0:
            ax.text(0.0012, i, "0", va="center", color="#52514e", fontsize=8.5)
    ax.set_xlabel("Observed exposure")
    ax.set_title("Core utility occupations: observed AI exposure is near zero",
                 loc="left", fontweight="bold")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(FIGS / "utility_core.png", bbox_inches="tight")
    plt.close(fig)


def fig_utility_vs_economy(ana: pd.DataFrame):
    """Cumulative distribution of exposure: utility groups against the rest.
    An ECDF handles the huge mass at zero honestly."""
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, color in [("All other occupations", BLUE),
                         ("Utility workforce (extended)", AQUA),
                         ("Utility core", ORANGE)]:
        vals = ana.loc[ana["group"] == label, "observed_exposure"].sort_values()
        ax.step(vals, (vals.rank(method="first")) / len(vals), where="post",
                color=color, linewidth=2, label=f"{label} (n={len(vals)})")
    ax.set_xlabel("Observed exposure")
    ax.set_ylabel("Cumulative share of occupations")
    ax.set_title("Utility occupations are concentrated at zero exposure",
                 loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIGS / "utility_vs_economy_ecdf.png", bbox_inches="tight")
    plt.close(fig)


def fig_utility_scatter(ana: pd.DataFrame):
    """Wage vs. exposure with the utility workforce highlighted: utility
    occupations pay mid-to-high wages yet sit on the exposure floor."""
    df = ana.dropna(subset=["median_wage"])
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    order = [("All other occupations", BLUE, 0.25, 14),
             ("Utility workforce (extended)", AQUA, 0.9, 34),
             ("Utility core", ORANGE, 0.95, 46)]
    for label, color, alpha, size in order:
        d = df[df["group"] == label]
        ax.scatter(d["median_wage"], d["observed_exposure"], s=size,
                   color=color, alpha=alpha, edgecolors=SURFACE,
                   linewidths=0.6, label=f"{label} (n={len(d)})")
    for _, r in df[df["utility_core"] == True].nlargest(2, "observed_exposure").iterrows():
        ax.annotate(r["title"], (r["median_wage"], r["observed_exposure"]),
                    fontsize=7.5, color="#52514e",
                    xytext=(6, 3), textcoords="offset points")
    ax.annotate("Water/Wastewater Operators (128k)\nPower-Line Installers (131k)",
                xy=(9.5e4, 0.0), xytext=(1.6e5, 0.09), color="#52514e",
                fontsize=8, arrowprops={"arrowstyle": "->", "color": MUTED})
    ax.set_xscale("log")
    ax.set_xlabel("Median annual wage, May 2025 (log scale, USD)")
    ax.set_ylabel("Observed exposure")
    ax.set_title("Well-paid, essential — and on the exposure floor",
                 loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(FIGS / "utility_wage_scatter.png", bbox_inches="tight")
    plt.close(fig)


def utility_page_section(ana: pd.DataFrame) -> str:
    """Interactive utility-focus panels: highlighted scatter + core bars."""
    df = ana.dropna(subset=["median_wage"])
    sec = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.09,
        subplot_titles=("Wage vs. exposure, utility workforce highlighted",
                        "Core utility occupations"))
    for label, color, size, alpha in [
            ("All other occupations", BLUE, 6, 0.3),
            ("Utility workforce (extended)", AQUA, 9, 0.95),
            ("Utility core", ORANGE, 11, 0.95)]:
        d = df[df["group"] == label]
        sec.add_scatter(x=d["median_wage"], y=d["observed_exposure"],
                        mode="markers", name=label, customdata=d["title"],
                        marker={"color": color, "size": size, "opacity": alpha},
                        hovertemplate="%{customdata}<br>wage: $%{x:,.0f}<br>"
                                      "exposure: %{y:.3f}<extra></extra>",
                        row=1, col=1)
    core = (ana[ana["utility_core"] == True]
            .sort_values("observed_exposure"))
    sec.add_bar(x=core["observed_exposure"], y=core["title"], orientation="h",
                marker_color=ORANGE, showlegend=False,
                customdata=core["emp_national"],
                hovertemplate="%{y}<br>exposure: %{x:.3f}<br>"
                              "employment: %{customdata:,.0f}<extra></extra>",
                row=1, col=2)
    sec.update_xaxes(type="log", title_text="median annual wage (USD)",
                     gridcolor=GRID, row=1, col=1)
    sec.update_xaxes(title_text="observed exposure", gridcolor=GRID, row=1, col=2)
    sec.update_yaxes(gridcolor=GRID)
    sec.update_layout(
        height=520, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        legend={"orientation": "h", "y": -0.25},
        font={"family": 'system-ui, -apple-system, "Segoe UI", sans-serif',
              "color": INK},
        margin={"t": 40, "l": 60, "r": 30})
    return sec.to_html(full_html=False, include_plotlyjs=False)


def build_page(exp, aa, wage, repro, n_gated, n_tasks, ana):
    """One self-contained interactive page for GitHub Pages. Embeds only
    occupation-level aggregates, never the raw task file."""
    page = make_subplots(
        rows=3, cols=2, vertical_spacing=0.11, horizontal_spacing=0.09,
        subplot_titles=(
            "Exposure distribution (756 occupations)", "Top 15 occupations",
            "Exposure vs. median wage (size = employment)",
            "Interaction types, economy-wide",
            "Published vs. reconstructed exposure (ρ = 0.87)",
            f"Task gate: {n_gated:,} of {n_tasks:,} tasks pass",
        ),
        specs=[[{}, {}], [{}, {}], [{}, {}]])

    page.add_histogram(x=exp["observed_exposure"], nbinsx=40,
                       marker_color=BLUE, row=1, col=1,
                       hovertemplate="exposure %{x}<br>%{y} occupations<extra></extra>")

    top = exp.nlargest(15, "observed_exposure").iloc[::-1]
    page.add_bar(x=top["observed_exposure"], y=top["title"], orientation="h",
                 marker_color=BLUE, row=1, col=2,
                 hovertemplate="%{y}<br>exposure: %{x:.3f}<extra></extra>")

    page.add_scatter(x=wage["A_MEDIAN"], y=wage["observed_exposure"],
                     mode="markers", customdata=wage["title"],
                     marker={"color": BLUE, "opacity": 0.45,
                             "size": (wage["TOT_EMP"] / wage["TOT_EMP"].max()) * 38 + 4},
                     hovertemplate="%{customdata}<br>wage: $%{x:,.0f}<br>"
                                   "exposure: %{y:.3f}<extra></extra>",
                     row=2, col=1)

    page.add_bar(x=aa["pct"], y=aa["interaction_type"], orientation="h",
                 marker_color=BLUE, row=2, col=2,
                 hovertemplate="%{y}: %{x:.1f}%<extra></extra>")

    recon = repro.columns[repro.columns.str.startswith("exposure_")][0]
    page.add_scatter(x=[0, 0.8], y=[0, 0.8], mode="lines",
                     line={"color": MUTED, "dash": "dash", "width": 1},
                     hoverinfo="skip", row=3, col=1)
    page.add_scatter(x=repro["observed_exposure"], y=repro[recon],
                     mode="markers", customdata=repro["title"],
                     marker={"color": BLUE, "opacity": 0.5, "size": 6},
                     hovertemplate="%{customdata}<br>published: %{x:.3f}<br>"
                                   "reconstructed: %{y:.3f}<extra></extra>",
                     row=3, col=1)

    pen = pd.read_csv(RAW / "economic_index/labor_market_impacts/task_penetration.csv")
    page.add_histogram(x=pen.loc[pen["penetration"] > 0, "penetration"], nbinsx=25,
                       marker_color=BLUE, row=3, col=2,
                       hovertemplate="task exposure %{x}<br>%{y} tasks<extra></extra>")

    page.update_xaxes(type="log", title_text="median annual wage (USD)", row=2, col=1)
    page.update_xaxes(title_text="published exposure", row=3, col=1)
    page.update_yaxes(title_text="reconstructed", row=3, col=1)
    page.update_layout(
        height=1500, showlegend=False, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font={"family": 'system-ui, -apple-system, "Segoe UI", sans-serif',
              "color": INK},
        margin={"t": 40, "l": 60, "r": 30})
    page.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    page.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)

    body = page.to_html(full_html=False, include_plotlyjs="cdn")
    utility_section = utility_page_section(ana)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>AI Workforce Exposure — Data Explorer</title>
<style>
  body {{ background: {SURFACE}; color: {INK}; margin: 0 auto; max-width: 1080px;
         padding: 24px 16px; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }}
  h1 {{ font-size: 1.5rem; }} p, li {{ color: #52514e; max-width: 70ch; line-height: 1.5; }}
  footer {{ color: #898781; font-size: 0.85rem; border-top: 1px solid {GRID};
            margin-top: 24px; padding-top: 12px; }}
  a {{ color: {BLUE}; }}
</style>
</head>
<body>
<h1>AI exposure in the workforce: a look at the data</h1>
<p>Exploratory view of the occupation-level data behind an independent study of
AI exposure in critical-infrastructure occupations. Exposure scores come from the
<a href="https://huggingface.co/datasets/Anthropic/EconomicIndex">Anthropic Economic
Index</a> ("observed exposure", Massenkoff &amp; McCrory 2026); wages and employment
from <a href="https://www.bls.gov/oes/">BLS OEWS</a> (May 2025). Charts show
occupation-level aggregates only. Hover any point for details.</p>
<h2>The utility workforce focus</h2>
<p>The study centers on the occupations that operate energy and water systems:
an operational core of 11 occupations (plant and system operators, line
installers, substation repairers) plus an extended workforce identified by
employment concentration in utility industries. Core utility occupations
average 0.009 observed exposure against 0.077 economy-wide — nine of the
eleven, including all ~128,000 water and wastewater operators, register
exactly zero.</p>
{utility_section}
<h2>The input data</h2>
{body}
<footer>
Independent research by Shannon Gross — not affiliated with or endorsed by Anthropic.
Exposure data: Anthropic Economic Index (CC-BY). Wages: BLS OEWS (public domain).
Code: <span><!-- repo link added on publish --></span>
</footer>
</body>
</html>"""
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote docs/index.html ({len(html) / 1e6:.2f} MB)")


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    exp = load_exposure()
    oews = load_oews()

    fig_distribution(exp)
    fig_by_group(exp)
    n_gated, n_tasks = fig_task_gate()
    aa = fig_interaction_types()
    wage = fig_wage_scatter(exp, oews)
    repro = fig_reproduction()

    ana = load_analysis()
    fig_utility_core(ana)
    fig_utility_vs_economy(ana)
    fig_utility_scatter(ana)

    build_page(exp, aa, wage, repro, n_gated, n_tasks, ana)
    print(f"wrote {len(list(FIGS.glob('*.png')))} figures to figures/eda/")


if __name__ == "__main__":
    main()
