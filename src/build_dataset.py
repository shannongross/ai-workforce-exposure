"""Build the occupation-level analysis dataset.

Step 1 (this file, so far): reproduce Anthropic's observed-exposure baseline.

Massenkoff & McCrory (2026, appendix) define task exposure r~_t = covered_t
* beta_t * alpha_t and job exposure as the time-fraction-weighted sum of r~_t
over the job's tasks. labor_market_impacts/task_penetration.csv already holds
r~_t (nonzero values all lie in [0.5, 1], the alpha signature), so what we
reproduce here is the task-to-occupation aggregation. Their time-fraction
weights (Tamkin & McCrory 2025) are not published, so we try candidate
weightings and validate each against their published job_exposure.csv by
Spearman rank correlation. Target from OUTLINE: rho > 0.95.

Run from the repo root: python src/build_dataset.py
"""

from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

# Frequency-category midpoints, times per year, for the O*NET FT scale
# (1 = yearly or less ... 7 = hourly or more). Used to approximate the
# "fraction of time spent on task" weights in the paper.
FT_TIMES_PER_YEAR = {1: 0.5, 2: 3, 3: 9, 4: 30, 5: 125, 6: 500, 7: 2000}


def normalize(s: pd.Series) -> pd.Series:
    # Punctuation-insensitive: the AEI and O*NET task texts differ by
    # commas/periods for otherwise identical tasks.
    s = s.astype(str).str.lower().str.strip()
    s = s.str.replace(r"[^a-z0-9 ]", "", regex=True)
    return s.str.replace(r"\s+", " ", regex=True)


def load_tasks() -> pd.DataFrame:
    """Task-level exposure joined to O*NET-SOC occupations via task text."""
    pen = pd.read_csv(RAW / "economic_index/labor_market_impacts/task_penetration.csv")
    pen["task_key"] = normalize(pen["task"])
    # A handful of task texts repeat with the same value; keep one each.
    pen = pen.drop_duplicates("task_key")[["task_key", "penetration"]]

    # Union of the O*NET vintage the AEI shipped with and the current 31.0
    # statements: together they match 100% of nonzero-penetration tasks.
    frames = []
    for f in ["economic_index/release_2025_02_10/onet_task_statements.csv",
              "onet/task_statements.csv"]:
        t = pd.read_csv(RAW / f)[["O*NET-SOC Code", "Task ID", "Task"]]
        frames.append(t)
    stmts = (pd.concat(frames)
             .drop_duplicates(["O*NET-SOC Code", "Task ID"]))
    stmts["task_key"] = normalize(stmts["Task"])
    stmts["soc"] = stmts["O*NET-SOC Code"].str[:7]  # 8-digit O*NET-SOC -> 6-digit SOC

    df = stmts.merge(pen, on="task_key", how="left")
    matched = df["penetration"].notna().mean()
    print(f"task join: {len(stmts)} O*NET task rows, "
          f"{matched:.1%} matched to a penetration value")
    # Unmatched tasks were not scored by Anthropic; the paper assigns
    # ungated tasks exposure 0, so missing means 0 here as well.
    df["penetration"] = df["penetration"].fillna(0.0)
    return df


def add_weights(df: pd.DataFrame) -> pd.DataFrame:
    ratings = pd.read_csv(RAW / "onet/task_ratings.csv")

    im = ratings.loc[ratings["Scale ID"] == "IM",
                     ["O*NET-SOC Code", "Task ID", "Data Value"]]
    im = im.rename(columns={"Data Value": "importance"})

    # Approximate time fraction from the FT scale: expected uses per year =
    # sum over categories of (share of respondents * category midpoint).
    ft = ratings[ratings["Scale ID"] == "FT"].copy()
    ft["times"] = ft["Category"].map(FT_TIMES_PER_YEAR) * ft["Data Value"] / 100
    freq = (ft.groupby(["O*NET-SOC Code", "Task ID"], as_index=False)["times"]
            .sum().rename(columns={"times": "freq"}))

    df = df.merge(im, on=["O*NET-SOC Code", "Task ID"], how="left")
    df = df.merge(freq, on=["O*NET-SOC Code", "Task ID"], how="left")
    return df


def job_exposure(df: pd.DataFrame, weight: str | None) -> pd.DataFrame:
    """Weighted mean of task penetration by 6-digit SOC (mean across
    O*NET-SOC detail codes within a SOC, mirroring the many-to-one map)."""
    d = df.copy()
    d["w"] = 1.0 if weight is None else d[weight]
    d = d.dropna(subset=["w"])
    per_onet = (d.groupby(["soc", "O*NET-SOC Code"])
                .apply(lambda g: (g["penetration"] * g["w"]).sum() / g["w"].sum(),
                       include_groups=False)
                .rename("exposure").reset_index())
    return per_onet.groupby("soc", as_index=False)["exposure"].mean()


def main() -> None:
    df = add_weights(load_tasks())

    published = pd.read_csv(RAW / "economic_index/labor_market_impacts/job_exposure.csv")
    published = published.rename(columns={"occ_code": "soc"})

    results = {}
    for name, weight in [("equal", None), ("importance", "importance"),
                         ("frequency", "freq")]:
        ours = job_exposure(df, weight)
        merged = published.merge(ours, on="soc", how="inner")
        rho = spearmanr(merged["observed_exposure"], merged["exposure"]).statistic
        results[name] = (rho, merged)
        print(f"  weight={name:<11} n={len(merged):>3} occupations  "
              f"spearman rho={rho:.4f}")

    best = max(results, key=lambda k: results[k][0])
    rho, merged = results[best]
    print(f"best: {best} (rho={rho:.4f}, target > 0.95)")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = merged.rename(columns={"exposure": f"exposure_{best}"})
    out.to_csv(PROCESSED / "exposure_baseline.csv", index=False)
    print(f"wrote data/processed/exposure_baseline.csv ({len(out)} occupations)")


if __name__ == "__main__":
    main()
