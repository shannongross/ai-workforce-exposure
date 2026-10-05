# AI task exposure and working time in community service occupations

**[Read the paper](paper/gross-2026-ai-exposure.pdf)** — *Can AI Give Time
Back? Task Exposure and Working Time in Local Community Service Occupations*
(Shannon Gross, October 2026).

This repository holds the data pipeline and figures behind it.

The analysis combines three published task-level measures — theoretical AI
exposure, time spent per task, and observed AI use — for the three largest
occupations in NAICS 624200, Community Food and Housing, and Emergency and
Other Relief Services:

- Social and Human Service Assistants (SOC 21-1093)
- Child, Family, and School Social Workers (SOC 21-1021)
- Social and Community Service Managers (SOC 11-9151)

## Data

All data are public and are downloaded, not stored here.

| Source | Used for |
|---|---|
| BLS Occupational Employment and Wage Statistics, May 2025 | Employment by occupation |
| O*NET 31.0 | Task statements, skill ratings |
| Eloundou et al. (2023), "GPTs are GPTs" | Exposure rating for each task |
| Hatgis-Kessell et al. (2026), "Estimating Time Spent on Work Tasks" | Hours per day for each task |
| Massenkoff and McCrory (2026), Anthropic Economic Index | Observed AI use for each task |
| National Center for Charitable Statistics | NTEE to NAICS crosswalk |

## Run

```
pip install -r requirements.txt
python src/download.py
```

Data lands in `data/raw/`. Two steps are manual, because BLS blocks scripted
downloads:

1. If the script lists a BLS file it could not fetch, download it in a browser
   and save it to the path the script prints.
2. Download the May 2025 national industry-specific file (`oesm25in4.zip`) from
   https://www.bls.gov/oes/tables.htm and unzip it to `data/raw/oews/oesm25in4/`.
   The script does not fetch this file.

Then run the notebooks. Figures are written to `figures/`, which is not
committed; the versions used in the paper are in `paper/figures/`.

| Notebook | Produces |
|---|---|
| `subq1.ipynb` | Working time by task and exposure category (Figures 1–3) |
| `subq2.ipynb` | Task counts versus time (Figure 4) |
| `eda.ipynb` | Sector context and source-data checks, not used in the paper |
