"""Download all raw data for the study into data/raw/.

Run from the repo root: python src/download.py
Re-running skips files that are already present.

Sources:
  - Anthropic Economic Index (Hugging Face, CC-BY): observed exposure,
    task penetration, and the 2025-02-10 / 2026-06-26 releases.
  - O*NET 31.0 (CC-BY): task statements, task ratings, occupation data.
  - BLS OEWS May 2025 (public domain): national wage/employment levels
    and the 4-digit NAICS industry staffing patterns (for the CI mapping).
"""

from pathlib import Path

import requests
from huggingface_hub import snapshot_download

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# Dataset commit pinned 2026-09-27 so reruns fetch identical data.
AEI_REVISION = "2ea58ff75e4247d26810c37f10c179edc2466cac"

AEI_PATTERNS = [
    "labor_market_impacts/*",
    "release_2025_02_10/*",
    "release_2026_06_26/*",
    "README.md",
]

ONET = "https://www.onetcenter.org/dl_files/database/db_31_0_csv"
OEWS = "https://www.bls.gov/oes/special-requests"

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
    (f"{ONET}/tasks_to_dwas.csv", "onet/tasks_to_dwas.csv",
     "task -> detailed work activity links (for task classification)"),
    (f"{ONET}/gwas_to_iwas_to_dwas.csv", "onet/gwas_to_iwas_to_dwas.csv",
     "DWA -> generalized work activity hierarchy (information vs physical)"),
    (f"{ONET}/content_model_reference.csv", "onet/content_model_reference.csv",
     "element names for the work-activity hierarchy"),
    (f"{OEWS}/oesm25nat.zip", "oews/oesm25nat.zip",
     "OEWS May 2025 national: employment and wages by SOC (levels only)"),
    (f"{OEWS}/oesm25in4.zip", "oews/oesm25in4.zip",
     "OEWS May 2025 by 4-digit NAICS: staffing patterns for the CI flag"),
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
