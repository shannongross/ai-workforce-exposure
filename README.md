# AI task exposure and working time in community service occupations

Code for the working paper *Can AI Give Time Back? Task Exposure and Working
Time in Local Community Service Occupations* (Shannon Gross, October 2026).

The analysis combines three published task-level measures (theoretical AI
exposure, time spent per task, and observed AI use) for the three largest
occupations in NAICS 6242, Community Food and Housing, and Emergency and Other
Relief Services:

- Social and Human Service Assistants (SOC 21-1093)
- Child, Family, and School Social Workers (SOC 21-1021)
- Social and Community Service Managers (SOC 11-9151)

## Data

All data are public and are downloaded, not stored in this repository.

| Source | Used for |
|---|---|
| BLS Occupational Employment and Wage Statistics, May 2025 | Employment by occupation |
| O*NET 31.0 | Task statements |
| Eloundou et al. (2024), "GPTs are GPTs" | Exposure rating for each task |
| Hatgis-Kessell et al. (2026), "Estimating Time Spent on Work Tasks" | Hours per day for each task |
| Anthropic Economic Index | Observed AI use for each task |
| National Center for Charitable Statistics | NTEE to NAICS crosswalk |

## Run

```
pip install -r requirements.txt
python src/download.py
```

`src/download.py` saves the data to `data/raw/`. Two steps are manual, because
BLS blocks scripted downloads:

1. If the script lists a BLS file it could not fetch, download it in a browser
   and save it to the path the script prints.
2. Download the May 2025 national industry-specific file (`oesm25in4.zip`) from
   https://www.bls.gov/oes/tables.htm and unzip it to `data/raw/oews/oesm25in4/`.
   The script does not fetch this file.

Then run the notebooks:

| Notebook | Produces |
|---|---|
| `subq1.ipynb` | Working time by task and exposure category for each occupation (Figures 1 to 3) |
| `subq2.ipynb` | Task counts versus time (Figure 4) |
| `eda.ipynb` | Exploratory analysis, not used in the paper |

## Contents

- `src/download.py`: data download
- `src/` (other scripts): exploratory analysis from an earlier, broader version of the study
- `subq1.ipynb`, `subq2.ipynb`: analysis and figures for the paper
- `figures/`: figure output
- `paper/`: LaTeX source for the paper
