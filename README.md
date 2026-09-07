# MASS Demographics & Recruitment Balance Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A lightweight **Streamlit dashboard for research-cohort demographics, group balance, and recruitment planning**. It summarizes participant counts by classification, age, age group, and sex, and helps identify demographic imbalances within and across study groups.

Developed by **Vinay Shankar**.  
Website: https://tfaworld.org/  
Contact: vinay@tfaworld.org

## What this project does

The dashboard is designed for study teams that need a quick visual overview of cohort composition without repeatedly rebuilding demographic summaries in spreadsheets.

It can:

- summarize participant counts by **Classification**, **Age**, **AgeGroup**, and **Sex**;
- visualize within-group sex balance;
- identify groups that are over- or under-represented;
- generate simple recruitment targets to improve balance;
- compare groups by **AgeGroup × Sex** cells;
- optionally calculate cell-wise matching targets across groups;
- handle Healthy Control records stored as a single group or automatically split them into age bands.

## Healthy Control age bands

When age-banded Healthy Controls are enabled, the dashboard assigns participants using age:

| Group | Age rule |
|---|---|
| `HC_lt35` | younger than 35 years |
| `HC_35-60` | 35 to 59 years |
| `HC_60plus` | 60 years or older |

## Expected data

The default workflow expects a CSV with these columns:

```text
userid,Age,Sex,Classification
```

Example:

```text
P001,22,F,HC
P002,64,M,PD
P003,61,F,RBD
```

`userid` is used to count unique participants when repeated rows or visits are present.

## Requirements

- Python 3.10+ recommended
- Streamlit
- pandas
- NumPy
- Plotly

Install the project dependencies with:

```bash
pip install -r requirements.txt
```

or directly:

```bash
pip install streamlit pandas numpy plotly
```

## Run the dashboard

From the repository directory:

```bash
streamlit run mass_dashboard.py
```

`app.py` currently contains the same dashboard implementation and is retained for compatibility with hosting environments that expect an `app.py` entry point.

## Key controls

The Streamlit sidebar includes options for:

- Healthy Control display mode;
- participant counting method;
- classification/group selection;
- demographic filtering;
- within-group balance review;
- cross-group matching and recruitment planning.

For repeated-measures datasets, counting **unique participants by `userid`** is generally preferable to counting rows.

## Research-data and privacy note

This repository includes a small example/current CSV named `MASS_DATA.csv`. Before publishing or sharing any dataset, confirm that it is appropriate for public release under the applicable IRB, consent language, institutional policy, and data-use restrictions.

Participant identifiers should be de-identified or replaced with non-identifying study codes. Do not place names, contact information, medical-record identifiers, dates of birth, or other direct identifiers in a public repository.

The dashboard is an exploratory cohort-management utility. It does not determine whether a study is statistically matched and does not replace a prespecified statistical analysis plan.

## Project structure

```text
demograph/
├── app.py
├── mass_dashboard.py
├── MASS_DATA.csv
├── requirements.txt
├── LICENSE
└── README.md
```

## Suggested use cases

- recruitment monitoring for case-control studies;
- age- and sex-balance checks before analysis;
- identifying under-represented recruitment cells;
- cohort summaries for lab meetings;
- exploratory demographic QC before formal statistical matching.

## Author

**Vinay Shankar**  
Website: https://tfaworld.org/  
Email: vinay@tfaworld.org

## License

This project is released under the **MIT License**. See [LICENSE](LICENSE).
