# NHS A&E Operational Intelligence

An AI-driven decision-support proof of concept for NHS A&E managers. It turns a monthly demand signal into a Low / Medium / High risk flag, shows it on a dashboard, and uses an AI agent to draft a short, plain-English recommendation that a person reviews.

The project uses only public, aggregated England-level data and free, open tools. It gives decision support only (staffing, escalation and monitoring). It does not give clinical advice, and it has not been through a clinical-safety assessment.

**Author:** Hetakshi Patel, Generate Sustainable Impact Research Internship (October 2026)

<img width="1822" height="831" alt="NHS A&E Operational Intelligence project overview" src="https://github.com/user-attachments/assets/9f8d6d55-0cea-4728-921b-aa57556d6e48" />

## Repository structure

```
.
├── Dataset/                          Raw NHS workbook and the cleaned monthly dataset
├── ae_dashboard/                     Gradio dashboard (Operational Risk Board)
├── figures/                          Images used in the report and slides (charts, diagrams, dashboard)
├── outputs/                          Model results, predictions and the agent's input file
├── NHS_AE_Data_Preparation.ipynb     Step 1: clean, merge, baseline, risk flag, features
├── NHS_AE_EDA.ipynb                  Step 2: exploratory data analysis
├── NHS_AE_Forecasting.ipynb          Step 3: models, evaluation, prediction files
└── README.md
```

| Path | What it contains |
|---|---|
| `Dataset/` | NHS England Monthly A&E Time Series (raw `.xls`) and `02_clean_Monthly_AE_data.csv` (191 rows, 25 columns) produced by the preparation notebook |
| `ae_dashboard/` | The dashboard app (`app.py`) |
| `figures/` | Charts, diagrams and dashboard screenshots used in the report and slides |
| `outputs/` | `predictions_with_riskflag.csv`, `model_comparison_regression.csv`, `model_comparison_classification.csv`, `confusion_matrix.csv`, `Automation_ready_data.csv` |
| `NHS_AE_Data_Preparation.ipynb` | Cleans and merges the Activity and Performance sheets, derives rates, builds the 3-year seasonal baseline, risk flag and model features |
| `NHS_AE_EDA.ipynb` | Demand, 4-hour performance, 12-hour waits, admissions, seasonality and correlations |
| `NHS_AE_Forecasting.ipynb` | Compares regression and classification models, saves predictions and the file the AI agent reads |

## Data

NHS England, A&E Attendances and Emergency Admissions, Monthly Time Series (Open Government Licence). August 2010 to June 2026 gives 191 monthly rows, of which 179 can be risk-rated (the first 12 months have no earlier same-month data for a baseline).

## How it works

1. **Prepare:** clean and merge the data, then add season, a 3-year same-month baseline and a risk flag.
2. **Analyse:** explore patterns, then fit models for monthly attendances and for the risk band.
3. **Show:** the dashboard displays KPIs, trends, drivers and a table of high-risk months.
4. **Act:** an n8n workflow with a local Ollama model reads `outputs/Automation_ready_data.csv`, drafts a short recommendation, logs it to Google Sheets and emails the manager for Medium and High months. A person reviews every suggestion.

### Risk rule

`ratio = attendances this month ÷ average of the same month in the previous 3 years`

| Ratio | Meaning | Risk |
|---|---|---|
| above 1.10 | more than 10% above normal | High |
| above 1.03, up to 1.10 | 3% to 10% above normal | Medium |
| 1.03 or below | within 3% of normal | Low |

The thresholds are a transparent project rule, not a clinical standard.

## Results

Months rated: 56 Low, 93 Medium, 30 High.

| Task | Best model | Result (5-fold cross-validation) |
|---|---|---|
| Estimate monthly attendances | Linear regression | R² 0.907, RMSE 72,285, 68.8% lower error than the seasonal baseline |
| Classify risk band | Logistic regression | Accuracy 79.9%, macro-F1 0.779 (143 of 179 months correct) |

These scores come from inputs that describe the month being estimated, so they show how well a model explains a month, not how well it predicts ahead. A stricter time-ordered forward check gives lower accuracy; see Section 5.1 of the report.

## Run it

Requirements: Python 3.10+.

```bash
pip install pandas numpy scikit-learn matplotlib seaborn plotly gradio xlrd jupyter
```

**1. Notebooks.** Open and run them in this order, from the repository root:

1. `NHS_AE_Data_Preparation.ipynb`
2. `NHS_AE_EDA.ipynb`
3. `NHS_AE_Forecasting.ipynb`

**2. Dashboard.** `app.py` reads `Dataset/02_clean_Monthly_AE_data.csv` and `outputs/predictions_with_riskflag.csv` relative to the folder you run it from. From the repository root:

```bash
python ae_dashboard/app.py
```

Then open the local address shown in the terminal (usually http://127.0.0.1:7860). The dashboard has three pages: Overview, Drivers & Explorer, and High-risk & Outlook. The "Next month outlook" chart compares actual attendances with the model's estimate for the same month.

## Known limitations

- National monthly data only; local and trust-level differences are hidden.
- Only 179 months can be modelled, and the 3-year baseline moves with demand.
- Headline scores overstate how well the model predicts ahead (see Results).
- Recent months are almost all rated Medium, so the Medium band needs refining.
- The risk thresholds are a judgement and are not clinically validated.
- The AI agent has not yet been reviewed by A&E managers.
- Not assessed under the NHS clinical-safety standards (DCB0129 / DCB0160).

## Data source

NHS England, A&E Attendances and Emergency Admissions: Monthly Time Series, published under the Open Government Licence v3.0.
