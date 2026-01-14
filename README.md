# MASS Database Dashboard (Age × Sex × Classification)

## What this does
An interactive dashboard to:
- Visualize participant counts by **Classification / Diagnosis / HC age band**, **Age**, **AgeGroup**, and **Sex**
- Check **within-group sex balance** (e.g., PD: Male vs Female) + a recruitment plan to fix imbalances
- Optionally match **across groups** by **AgeGroup × Sex** (cell-wise) and plan recruitment
- Handle "weird" Healthy Control storage by assigning HC to age bands using **Age**:
  - `HC_lt35` (<35), `HC_35-60` (35–59), `HC_60plus` (≥60)

## Expected CSV columns
`userid`, `Age`, `Sex`, `Classification`

## Install
```bash
pip install streamlit pandas numpy plotly
```

## Run
```bash
streamlit run mass_dashboard.py
```

## Key settings
- Sidebar → **Show HC as…**
  - Three age bands (recommended), or Single group (HC)
- Sidebar → **Count participants as…**
  - Unique participants (userid) recommended if you have repeated rows/visits
