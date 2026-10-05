"""Download all raw data for the study into data/raw/.

Run from the repo root: python src/download.py
Re-running skips files that are already present.

Sources:
  - Anthropic Economic Index (Hugging Face, CC-BY): observed exposure,
    task penetration, and the 2025-02-10 / 2026-06-26 releases.
  - O*NET 31.0 (CC-BY): task statements, task ratings, occupation data,
    and skill importance ratings (Eloundou et al. relate these to exposure).
  - BLS OEWS May 2025 (public domain): national wage/employment levels
    for occupation-level wages and employment.
"""

from pathlib import Path

import requests
from huggingface_hub import snapshot_download

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# Dataset commit pinned 2026-09-27 so reruns fetch identical data.
AEI_REVISION = "2ea58ff75e4247d26810c37f10c179edc2466cac"

AEI_PATTERNS = [
    "labor_market_impacts/*",
    # from the Feb 2025 release only the task statements (used in the
    # task-text join alongside O*NET 31.0)
    "release_2025_02_10/onet_task_statements.csv",
    "release_2026_06_26/*",
    "README.md",
]

ONET = "https://www.onetcenter.org/dl_files/database/db_31_0_csv"
OEWS = "https://www.bls.gov/oes/special-requests"

# Eloundou et al. (2023) "GPTs are GPTs", arXiv:2303.10130. Theoretical LLM
# exposure ratings (alpha/beta/gamma), MIT licensed. Anthropic's labor market
# impacts report uses their beta as its theoretical-capability series.
# Commit pinned 2026-09-29 so reruns fetch identical data.
GPTS = ("https://raw.githubusercontent.com/openai/GPTs-are-GPTs/"
        "9ed4148d15f4c4a2666f45bf0006e56b3a3b9f70")
# the task-level ratings behind occ_level.csv, pinned at their own commit
GPTS_TASKS = ("https://raw.githubusercontent.com/openai/GPTs-are-GPTs/"
              "36af7ac78d218158fd2070bd8775c86a99f222da")

# Hatgis-Kessell, Aguirre, Wan & Bommasani (2026) "Estimating time spent on
# work tasks", arXiv:2608.05172. Share of the working day per O*NET task --
# the weight needed to go from share-of-tasks to share-of-time.
# Commit pinned 2026-09-29 so reruns fetch identical data.
TIMESHARE = ("https://raw.githubusercontent.com/Stephanehk/"
             "Estimating-Time-Spent-On-Work/"
             "777ebb911ba8e79a02b122c1ea2f808326aab163")

# National Center for Charitable Statistics (Urban Institute). The NTEE
# taxonomy the IRS uses to classify nonprofits, with each code's NAICS
# equivalent -- how the study's industry scope is derived rather than chosen.
# Refreshed against the IRS list each January, so this is "latest", not pinned.
NCCS = "https://nccsdata.s3.amazonaws.com/lookups/bmf/latest"

# (url, destination relative to data/raw/, what it is)
FILES = [
    (f"{ONET}/task_statements.csv", "onet/task_statements.csv",
     "O*NET task text, keyed by O*NET-SOC code"),
    (f"{ONET}/task_ratings.csv", "onet/task_ratings.csv",
     "task importance/relevance ratings (weights for aggregation)"),
    (f"{ONET}/occupation_data.csv", "onet/occupation_data.csv",
     "O*NET-SOC titles and descriptions"),
    (f"{ONET}/work_context.csv", "onet/work_context.csv",
     "work-context ratings (robustness: work-context filter arm)"),
    (f"{ONET}/essential_skills.csv", "onet/essential_skills.csv",
     "importance of the 10 basic skills (science, critical thinking, writing...)"),
    (f"{ONET}/transferable_skills.csv", "onet/transferable_skills.csv",
     "importance of the 25 cross-functional skills (programming, negotiation...)"),
    (f"{ONET}/tasks_to_dwas.csv", "onet/tasks_to_dwas.csv",
     "task -> detailed work activity links (for task classification)"),
    (f"{ONET}/gwas_to_iwas_to_dwas.csv", "onet/gwas_to_iwas_to_dwas.csv",
     "DWA -> generalized work activity hierarchy (information vs physical)"),
    (f"{ONET}/content_model_reference.csv", "onet/content_model_reference.csv",
     "element names for the work-activity hierarchy"),
    (f"{OEWS}/oesm25nat.zip", "oews/oesm25nat.zip",
     "OEWS May 2025 national: employment and wages by SOC (levels only)"),
    (f"{GPTS}/data/occ_level.csv", "gpts_are_gpts/occ_level.csv",
     "theoretical LLM exposure by occupation (alpha/beta/gamma, human + GPT-4)"),
    (f"{GPTS_TASKS}/data/full_labelset.tsv", "gpts_are_gpts/full_labelset.tsv",
     "the same exposure ratings per TASK, joinable on O*NET Task ID"),
    (f"{TIMESHARE}/task_time_share_estimates.xlsx",
     "time_share/task_time_share_estimates.xlsx",
     "estimated hours per day spent on each O*NET task"),
    (f"{NCCS}/ntee_code.csv", "nccs/ntee_code.csv",
     "NTEE nonprofit categories with their NAICS equivalents (scope crosswalk)"),
]


def download(url: str, dest: Path) -> str:
    if dest.exists():
        return "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    if resp.status_code == 403 and "bls.gov" in url:
        # BLS blocks all scripted clients at the CDN (TLS fingerprinting),
        # so these two files must be fetched once in a browser.
        return "MANUAL"
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return f"{len(resp.content) / 1e6:.1f} MB"


def main() -> None:
    print("Anthropic Economic Index (Hugging Face) ...")
    path = snapshot_download(
        repo_id="Anthropic/EconomicIndex",
        repo_type="dataset",
        revision=AEI_REVISION,
        allow_patterns=AEI_PATTERNS,
        local_dir=RAW / "economic_index",
    )
    print(f"  -> {path}")
    print(f"  pinned revision: {AEI_REVISION}")

    manual = []
    for url, rel, note in FILES:
        status = download(url, RAW / rel)
        if status == "MANUAL":
            manual.append((url, rel))
        print(f"  {rel:<28} {status:>8}  # {note}")

    # Sanity check: the two files the whole study depends on.
    for must in ["economic_index/labor_market_impacts/job_exposure.csv",
                 "economic_index/labor_market_impacts/task_penetration.csv"]:
        assert (RAW / must).exists(), f"missing expected file: {must}"

    if manual:
        print("\nBLS rejects scripted downloads. Fetch these once in a browser,")
        print("then save them to the paths shown (rerun this script to verify):")
        for url, rel in manual:
            print(f"  {url}\n    -> data/raw/{rel}")
    else:
        print("done — all expected files present.")


if __name__ == "__main__":
    main()
