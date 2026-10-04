# NHS A&E Operational Intelligence

An AI-driven decision-support proof of concept for NHS A&E managers. It turns a monthly demand signal into a Low / Medium / High risk flag, shows it on a dashboard, and uses an AI agent to draft a short, plain-English recommendation that a person reviews.

The project uses only public, aggregated England-level data and free, open tools. It gives decision support only (staffing, escalation and monitoring). It does not give clinical advice, and it has not been through a clinical-safety assessment.

<img width="963" height="587" alt="image" src="https://github.com/user-attachments/assets/f91087a5-5f6c-4a77-a466-5c3b89242ab9" />

## Repository structure

```
.
├── Dataset/                          Raw NHS workbook and the cleaned monthly dataset
├── ae_dashboard/                     Gradio dashboard (Operational Risk Board)
├── figures/                          All the images along with graphs,outputs and dashboard
├── outputs/                          Model results, predictions and the agent's input file
├── NHS_AE_Data_Preparation.ipynb     Step 1: clean, merge, baseline, risk flag, features
├── NHS_AE_EDA.ipynb                  Step 2: exploratory data analysis
├── NHS_AE_Forecasting.ipynb          Step 3: models, evaluation, prediction files
└── README.md
```

| Path | What it contains |
|---|---|
| `Dataset/` | NHS England Monthly A&E Time Series (raw `.xls`) and `02_clean_Monthly_AE_data.csv` produced by the preparation notebook |
| `ae_dashboard/` | The dashboard app (`app.py`) |
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

| Ratio | Risk |
|---|---|
| above 1.10 | High |
| above 1.03, up to 1.10 | Medium |
| 1.03 or below | Low |

The thresholds are a transparent project rule, not a clinical standard.

## Results

Months rated: 56 Low, 93 Medium, 30 High.

| Task | Best model | Result (5-fold cross-validation) |
|---|---|---|
| Estimate monthly attendances | Linear regression | R² 0.907, RMSE 72,285, 68.8% lower error than the seasonal baseline |
| Classify risk band | Logistic regression | Accuracy 79.9%, F1-score 0.779 (143 of 179 months correct) |

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

If your `ae_dashboard` folder holds its own copies of `Dataset/` and `outputs/`, run it from inside that folder instead:

```bash
cd ae_dashboard
python app.py
```

Then open the local address shown in the terminal (usually http://127.0.0.1:7860). The dashboard has three pages: Overview, Drivers & Explorer, and High-risk & Outlook.

## Known limitations

- National monthly data only; local and trust-level differences are hidden.
- Only 179 months can be modelled, and the 3-year baseline moves with demand.
- Recent months are almost all rated Medium, so the Medium band needs refining.
- The risk thresholds are a judgement and are not clinically validated.
- The AI agent has not yet been reviewed by A&E managers.
- Not assessed under the NHS clinical-safety standards (DCB0129 / DCB0160).

## Licence and data source

Data: NHS England, Open Government Licence v3.0. Add a licence for the code here if you want others to reuse it.
