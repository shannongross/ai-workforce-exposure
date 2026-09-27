"""Exploratory modeling over the measurement uncertainty space.

The headline claim — information-based utility tasks show almost no
observed AI usage, far below the economy-wide margin — depends on
judgment calls. Each is treated as an uncertain parameter and the full
factorial of specifications is enumerated (small enough that sampling
is unnecessary). For every specification we compute the share of
information tasks with any observed usage, in the core utility
occupations and economy-wide, and their ratio.

Run from the repo root: python src/robustness.py
"""

import itertools
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from build_dataset import PHYSICAL_GWAS, RAW, REFERENCE, PROCESSED, load_tasks

# GWAs plausibly requiring physical presence even though informational:
# monitoring surroundings, identifying objects/events, inspecting equipment
PRESENCE_GWAS = {"4.A.1.a.2", "4.A.1.b.1", "4.A.1.b.2"}
# Interpersonal GWAs (4.A.4.*): communication, training, coordinating
INTERPERSONAL_PREFIX = "4.A.4"

# Featured levers (definitional, shown in the paper): rule, presence,
# core_set. Mechanical levers (unmatched, weighting) stay in the ensemble
# to demonstrate they are inert; usage is binary (any observed usage),
# since no analysis uses the penetration magnitude. SOC 51-80xx industrial
# cousins (chemical/refinery operators) are NOT a utility definition; they
# serve as the occupational-twins comparison instead.
PARAMS = {
    "rule": ["any_physical", "majority_physical", "strict_information"],
    "presence_is_physical": [False, True],
    "unmatched": ["zero", "drop"],
    "core_set": ["core11", "extended"],
    "weighting": ["equal", "importance"],
}


def prepare() -> pd.DataFrame:
    """Task-level frame for all occupations: GWAs, penetration, importance."""
    td = pd.read_csv(RAW / "onet/tasks_to_dwas.csv")
    td["gwa"] = td["DWA Element ID"].str.extract(r"^(4\.A\.\d\.[a-z]\.\d+)")
    gwas = td.groupby(["O*NET-SOC Code", "Task ID"])["gwa"].agg(list)

    tasks = load_tasks().drop_duplicates(["soc", "Task ID"])
    tasks = tasks.merge(gwas.rename("gwas"),
                        left_on=["O*NET-SOC Code", "Task ID"],
                        right_index=True, how="inner")

    ratings = pd.read_csv(RAW / "onet/task_ratings.csv")
    im = (ratings[ratings["Scale ID"] == "IM"]
          [["O*NET-SOC Code", "Task ID", "Data Value"]]
          .rename(columns={"Data Value": "importance"}))
    tasks = tasks.merge(im, on=["O*NET-SOC Code", "Task ID"], how="left")
    tasks["importance"] = tasks["importance"].fillna(3.0)

    # matched = the task text found a value in task_penetration.csv;
    # load_tasks() fills unmatched with 0, so recover the distinction
    pen = pd.read_csv(RAW / "economic_index/labor_market_impacts/task_penetration.csv")
    from build_dataset import normalize
    matched_keys = set(normalize(pen["task"]))
    tasks["matched"] = tasks["task_key"].isin(matched_keys)
    return tasks


def occupation_sets() -> dict[str, set]:
    core = set(pd.read_csv(REFERENCE / "utility_core_occupations.csv")["soc"])
    ana = pd.read_csv(PROCESSED / "analysis.csv")
    return {
        "core11": core,
        "extended": set(ana.loc[ana["utility_workforce"] == True, "OCC_CODE"]),
    }


def classify(tasks: pd.DataFrame, rule: str, presence_is_physical: bool) -> pd.Series:
    physical = set(PHYSICAL_GWAS) | (PRESENCE_GWAS if presence_is_physical else set())

    def one(gwas: list) -> str:
        phys = sum(g in physical for g in gwas)
        inter = sum(str(g).startswith(INTERPERSONAL_PREFIX) for g in gwas)
        if rule == "any_physical":
            return "physical" if phys else "information"
        if rule == "majority_physical":
            return "physical" if phys > len(gwas) / 2 else "information"
        # strict_information: physical if any physical GWA; interpersonal
        # tasks are their own class, excluded from the information margin
        if phys:
            return "physical"
        return "interpersonal" if inter == len(gwas) else "information"

    return tasks["gwas"].apply(one)


def evaluate(tasks: pd.DataFrame, occ_sets: dict, spec: dict) -> dict:
    t = tasks.copy()
    t["cls"] = classify(t, spec["rule"], spec["presence_is_physical"])
    if spec["unmatched"] == "drop":
        t = t[t["matched"]]
    t = t[t["cls"] == "information"]
    t["used"] = t["penetration"] > 0  # binary: any observed usage
    t["w"] = 1.0 if spec["weighting"] == "equal" else t["importance"]

    in_core = t["soc"].isin(occ_sets[spec["core_set"]])
    out = dict(spec)
    for name, mask in [("utility", in_core), ("economy", ~in_core)]:
        g = t[mask]
        out[f"{name}_info_tasks"] = len(g)
        out[f"{name}_used_share"] = (
            (g["used"] * g["w"]).sum() / g["w"].sum() if len(g) else float("nan"))
    out["ratio"] = (out["economy_used_share"] / out["utility_used_share"]
                    if out["utility_used_share"] > 0 else float("inf"))
    return out


def main() -> None:
    tasks = prepare()
    occ_sets = occupation_sets()
    keys, values = zip(*PARAMS.items())
    specs = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
    print(f"enumerating {len(specs)} specifications ...")

    results = pd.DataFrame([evaluate(tasks, occ_sets, s) for s in specs])
    results.to_csv(PROCESSED / "robustness_info_gap.csv", index=False)

    r = results.dropna(subset=["utility_used_share"])
    print(f"\nutility info-task used share: min={r['utility_used_share'].min():.3f} "
          f"median={r['utility_used_share'].median():.3f} "
          f"max={r['utility_used_share'].max():.3f}")
    print(f"economy info-task used share: min={r['economy_used_share'].min():.3f} "
          f"median={r['economy_used_share'].median():.3f} "
          f"max={r['economy_used_share'].max():.3f}")
    holds = (r["utility_used_share"] < r["economy_used_share"]).mean()
    factor5 = ((r["economy_used_share"] > 5 * r["utility_used_share"])
               | (r["utility_used_share"] == 0)).mean()
    print(f"claim 'utility below economy' holds in {holds:.1%} of specs")
    print(f"claim 'utility at least 5x below economy (or zero)' holds in "
          f"{factor5:.1%} of specs")

    spec_curve(r)
    spec_curve(r, absolute=True)

    # which lever moves the utility share most: range of group means
    print("\nparameter influence on utility used share (range of means):")
    for p in PARAMS:
        means = r.groupby(p)["utility_used_share"].mean()
        print(f"  {p:<22} {means.max() - means.min():.4f}  "
              + "  ".join(f"{k}={v:.3f}" for k, v in means.items()))


def spec_curve(r: pd.DataFrame, absolute: bool = False) -> None:
    """Parallel-coordinates view: one line per specification, one axis per
    outcome metric. Every line starts low on the utility axis and high on
    the economy axis - the gap holds across the whole ensemble.

    absolute=True scales each axis from zero to its maximum possible value
    (shares to 1.0), showing how small the whole phenomenon is in absolute
    terms; the default zooms to the observed ranges."""
    BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
    INK, MUTED, SURFACE = "#0b0b0b", "#898781", "#fcfcfb"

    axes = [("utility_used_share", "Utility info-task\nusage share"),
            ("economy_used_share", "Economy info-task\nusage share"),
            ("ratio", "Gap\n(economy ÷ utility)"),
            ("utility_info_tasks", "Feasible utility tasks\nin scope (n)")]
    d = r.copy()
    d["ratio"] = d["ratio"].clip(upper=d["ratio"].replace(
        float("inf"), pd.NA).dropna().max())
    if absolute:
        lo = {c: 0.0 for c, _ in axes}
        hi = {"utility_used_share": 1.0, "economy_used_share": 1.0,
              "ratio": d["ratio"].max(),
              "utility_info_tasks": d["utility_info_tasks"].max()}
    else:
        lo = {c: d[c].min() for c, _ in axes}
        hi = {c: d[c].max() for c, _ in axes}
        # the two share axes use ONE common scale, so the utility->economy
        # jump is visible; per-axis normalization would hide the gap
        shared_lo = min(lo["utility_used_share"], lo["economy_used_share"])
        shared_hi = max(hi["utility_used_share"], hi["economy_used_share"])
        for c in ("utility_used_share", "economy_used_share"):
            lo[c], hi[c] = shared_lo, shared_hi
    norm = {c: (d[c] - lo[c]) / (hi[c] - lo[c]) for c, _ in axes}

    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    colors = {"core11": ORANGE, "extended": BLUE}
    for i in d.index:
        ax.plot(range(len(axes)), [norm[c][i] for c, _ in axes],
                color=colors[d.loc[i, "core_set"]], alpha=0.25, linewidth=1)
    for x, (c, label) in enumerate(axes):
        ax.axvline(x, color="#c3c2b7", linewidth=1)
        fmt = "{:.0f}" if c == "utility_info_tasks" else "{:.2f}"
        ax.text(x, -0.06, fmt.format(lo[c]), ha="center", va="top",
                fontsize=8.5, color=MUTED)
        ax.text(x, 1.06, fmt.format(hi[c]), ha="center", va="bottom",
                fontsize=8.5, color=MUTED)
        ax.text(x, -0.16, label, ha="center", va="top", fontsize=9, color=INK)
    handles = [plt.Line2D([], [], color=c, linewidth=2) for c in colors.values()]
    ax.legend(handles, ["core utility occupations (11)",
                        "extended utility workforce (21)"],
              frameon=False, fontsize=8.5, loc="upper center",
              bbox_to_anchor=(0.5, 1.28), ncol=2,
              title="utility workforce definition (lever L1)",
              title_fontsize=8.5)
    ax.set_xlim(-0.3, len(axes) - 0.7); ax.set_ylim(-0.02, 1.02)
    ax.axis("off")
    title = (f"{len(d)} specifications on absolute scales: AI usage in "
             "information tasks is a small phenomenon everywhere — "
             "and smallest in utilities"
             if absolute else
             f"{len(d)} specifications, one line each: utility usage "
             "stays low no matter the measurement choices")
    ax.set_title(title, loc="left", fontweight="bold", fontsize=11, y=1.34)
    fig.tight_layout()
    name = ("robustness_parallel_absolute.png" if absolute
            else "robustness_parallel.png")
    out = Path(__file__).resolve().parents[1] / "figures" / name
    fig.savefig(out, bbox_inches="tight", dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
