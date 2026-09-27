# How Exposed Is Critical Infrastructure to AI?

An empirical look at observed AI usage in critical-infrastructure occupations,
using the [Anthropic Economic Index](https://huggingface.co/datasets/Anthropic/EconomicIndex),
O*NET, and BLS OEWS data. The study asks how much critical-infrastructure
occupations actually use AI relative to the broader economy, whether that usage
is automation- or augmentation-shaped, and how robust those conclusions are to
the measurement choices behind them.

The paper is in [paper/](paper/). <!-- TODO: link the PDF/blog post when done -->

## Reproducing the analysis

```
pip install -r requirements.txt
python src/download.py        # fetch raw data into data/raw/ (~380 MB)
python src/build_dataset.py   # exposure baseline + CI flag + joins
python src/analysis.py        # descriptives and regression -> figures/, tables
python src/robustness.py      # specification ensemble -> figures/
```

BLS blocks scripted downloads, so `download.py` will ask you to fetch the two
OEWS zip files once in a browser; it prints the URLs and destination paths.

Each step prints how many occupations enter and leave, and why. The robustness
ensemble uses a fixed random seed; the Economic Index dataset is pinned to a
specific revision in `src/download.py`.

## Data sources and licenses

| Source | Used for | License |
|---|---|---|
| [Anthropic Economic Index](https://huggingface.co/datasets/Anthropic/EconomicIndex) | Observed exposure, task penetration, automation/augmentation shares | CC-BY |
| [O*NET 31.0](https://www.onetcenter.org/database.html) | Task statements, importance weights, work context | CC-BY 4.0 |
| [BLS OEWS, May 2025](https://www.bls.gov/oes/) | Wage/employment levels; industry staffing patterns | Public domain |
| [CISA critical infrastructure sectors](https://www.cisa.gov/topics/critical-infrastructure-security-and-resilience/critical-infrastructure-sectors) | Sector definitions | Public domain |

The CISA-sector-to-NAICS mapping is hand-built and committed at
[data/reference/cisa_sectors_naics.csv](data/reference/cisa_sectors_naics.csv),
with a rationale column documenting each judgment call. The broad/narrow split
there is one of the parameters varied in the robustness section.

## AI assistance

<!-- TODO(Shannon): rewrite in your own words before publishing. -->
AI tools (Claude) assisted with data-download boilerplate and debugging.
All research design choices, the CISA sector mapping, the interpretation of
results, and the text of the paper are my own.

## Author

Shannon Gross
