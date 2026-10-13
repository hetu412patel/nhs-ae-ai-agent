# NHS A&E Operational Intelligence

**An AI agent that turns a monthly A&E demand signal into a plain-English recommendation for the manager, logs it, and alerts them when pressure rises. A person reviews every suggestion.**

Built entirely with public, aggregated England-level data and free, open tools (Python, n8n, Ollama, Gradio). It gives decision support only (staffing, escalation and monitoring). It gives no clinical advice and has not been through a clinical-safety assessment.

**Author:** Hetakshi Patel (October 2026)

<img width="1822" height="831" alt="NHS A&E Operational Intelligence project overview" src="https://github.com/user-attachments/assets/9f8d6d55-0cea-4728-921b-aa57556d6e48" />

## At a glance

| | |
|---|---|
| **Problem** | A&E demand is about a third higher than in 2010–11 while four-hour performance has fallen from 97.2% to 75.0%. Managers get forecasts, but not explained advice on what to do. |
| **Gap** | Forecasting tools exist, but no established system turns a forecast into an explained, manager-facing recommendation with a human decision. |
| **Solution** | Clean NHS data → transparent Low / Medium / High risk flag → dashboard + **n8n AI agent** that drafts, logs and emails a recommendation. |
| **Safety design** | Operational data only, local AI model, every recommendation time-stamped and logged, manager accepts, amends or ignores. |
| **Status** | Research prototype. Not yet reviewed by A&E managers or assessed under DCB0129 / DCB0160. |

---

## 1. Literature review and the gap

| Area | What exists | Limit |
|---|---|---|
| **Demand forecasting** | A forecasting tool is live in 123 trusts, looking about 3 weeks ahead. | It predicts; it does not explain or recommend. |
| **Estate intelligence** | Funded, building-focused tools such as Twinview at Eastbourne DGH and a Manchester six-hospital digital twin, within a £10bn AI programme announced July 2026. | Uses building data only: no patient-flow advice. |
| **Patient-facing AI** | NHS App AI triage (2026). Symptom checkers scored 55.8% triage accuracy in 2020 (Schmieding et al., 2022). | Talks to patients directly, so it carries the highest safety risk. |
| **Governance** | Clinical-safety standards DCB0129 / DCB0160. | Not built for adaptive AI, which explains the caution around it. |

**The gap this project fills:** *forecast → explanation → recommendation → human decision.* No system was found that links all four for A&E managers. This repository builds a small working example using free tools.

**Research questions:** (1) Can the approach transfer to other sectors? (2) Why is decision-support AI rare in the NHS? (3) Does a funded model exist elsewhere in the NHS? (4) Can a free-tool agent show the way?

---

## 2. The AI Agent (n8n + Ollama)

Once a month the agent reads the latest figures, writes a short plain-English note, logs it, and emails the manager only when risk is Medium or High.

<img width="1492" height="267" alt="image" src="https://github.com/user-attachments/assets/67da2cfd-9dbd-499d-ac5b-8a4508562899" />

### What each node does

| # | Node | What it does |
|---|---|---|
| 1 | **Schedule Trigger** | Starts the workflow automatically once a month. No one has to remember to run it. |
| 2 | **Read/Write Files from Disk** | Reads `Automation_ready_data.csv` from the n8n files folder. |
| 3 | **Extract from File** | Converts the CSV into rows the workflow can use. |
| 4 | **Sort** | Orders rows by month so the newest comes first. |
| 5 | **Limit** | Keeps only the latest month. |
| 6 | **Edit Fields** | Selects the real figures (attendances, forecast, baseline, 4-hour performance, 12-hour waits, last month's values, risk flag) and shapes them for the prompt. |
| 7 | **Basic LLM Chain** | Sends the figures plus fixed rules to the model and receives the recommendation. |
| 7a | **Ollama Chat Model** | The language model, running locally on the user's own machine. No data leaves it. |
| 8 | **Edit Fields1** | Tidies the model's reply into the columns for the log. |
| 9 | **Append row in sheet** | Adds a time-stamped row to Google Sheets: a permanent record of every recommendation. |
| 10 | **If** | Checks the risk level. Medium or High goes to the email; Low is logged only. |
| 11 | **Send a message (Gmail)** | Emails the recommendation to the A&E manager. |

### What the manager receives

A short note, in plain English, built from real figures, covering **staffing, escalation and monitoring**. The prompt tells the model to use only the figures supplied, to give no clinical advice, and to match the advice to the risk level.

### Why this is safe to put in front of a manager

- **Human in charge:** the agent advises; the manager accepts, amends or ignores.
- **Logged:** every recommendation is time-stamped in Google Sheets.
- **Grounded:** advice quotes real numbers, and model accuracy is stated openly.
- **Private by design:** public monthly England totals only, no patient-level data, and the model runs locally.
- **Low cost:** n8n, Ollama and the data are all free and open.

### Run the agent

1. Run the three notebooks to produce `outputs/Automation_ready_data.csv`.
2. Install [n8n](https://n8n.io) and [Ollama](https://ollama.com), then pull a model with `ollama pull <model>`.
3. Put `Automation_ready_data.csv` in your n8n files folder. The Forecasting notebook can copy it for you if you set the `N8N_FILES_DIR` environment variable (for example `C:/Users/<you>/.n8n-files`).
4. Import `agent/NHS_AE_AI_Agent_workflow.json` into n8n.
5. Connect your Google Sheets and Gmail credentials, choose the Ollama model, and set the schedule.
6. Run once manually to check the log row and the email.

---

## 3. Data

**Source:** NHS England, *A&E Attendances and Emergency Admissions: Monthly Time Series* (Open Government Licence). August 2010 to June 2026: 191 monthly rows, of which 179 can be risk-rated (the first 12 months have no earlier same-month data for a baseline).

**Pipeline:** raw `.xls` → clean and merge the Activity and Performance sheets → derive rates (admission rate, 12-hour wait rate, department-type shares) → add season, 3-year baseline and risk flag → `02_clean_Monthly_AE_data.csv` (191 rows, 25 columns).

### Risk rule

`ratio = attendances this month ÷ average of the same month in the previous 3 years`

| Ratio | Meaning | Risk |
|---|---|---|
| above 1.10 | more than 10% above normal | **High** |
| above 1.03, up to 1.10 | 3% to 10% above normal | **Medium** |
| 1.03 or below | within 3% of normal | **Low** |

Thresholds are a transparent project rule, not a clinical standard. Result: **56 Low, 93 Medium, 30 High** months.

### What the agent reads (`outputs/Automation_ready_data.csv`)

`Month`, `TotalAttendances`, `RiskFlag`, `PredictedTotalAttendances`, `PredictedRiskFlag`, `PercentWithin4hrs`, `Breach12hrRate`, `Season`, `SeasonalBaselineAvg`, plus last month's values (`PrevMonthAttendance`, `PrevMonthPercentWithin4hrs`, `PrevMonthBreach12hrRate`) so the note can explain the trend, not just one snapshot.

---

## 4. Models and results

| Task | Best model | Result (5-fold cross-validation) |
|---|---|---|
| Estimate monthly attendances | Linear regression | R² 0.907, RMSE 72,285, 68.8% lower error than the seasonal baseline |
| Classify risk band | Logistic regression | Accuracy 79.9%, macro-F1 0.779 (143 of 179 months correct) |

Simple models beat Random Forest and kNN on both tasks. Errors lean towards over-warning (21) rather than under-warning (15), and 22 of 30 High months were found.

**Forward check (stricter, time-ordered).** Train to June 2023, predict July 2023 to June 2026 using only information available a month earlier. Cross-validated scores show how well a model *explains* a month; the forward check shows how it behaves *ahead*. Code: *Forward check* section of `NHS_AE_Forecasting.ipynb` (saves `outputs/forward_check_results.csv`).

| Measure | Cross-validated | Forward check |
|---|---|---|
| Average error (RMSE) | 72,285 | 100,822 |
| Improvement on baseline | 68.8% | 53.1% |
| Risk accuracy | 79.9% | 75.0% |
| Macro-F1 | 0.779 | 0.52 |

Treat outputs as guidance with about a 4% margin.

---

## 5. Dashboard (Operational Risk Board)

Gradio + Plotly, three pages with filters: **Overview** (KPIs, trend, risk by season), **Drivers & Explorer**, and **High-risk & Outlook** (table of High months and a "Model fit" chart). The "Model fit" chart compares actual attendances with the model's estimate for the same months; it shows fit, not a forecast.

Latest month (June 2026): 2,437,906 attendances, 75.0% seen within 4 hours (20.0 points below the 95% target), pressure score 80/100, Medium risk.

---

## 6. Repository structure and how to run

```
.
├── Dataset/                          Raw NHS workbook and cleaned monthly dataset
├── ae_dashboard/                     Gradio dashboard (app.py)
├── agent/                            n8n workflow export (NHS_AE_AI_Agent_workflow.json)
├── figures/                          Charts, diagrams, dashboard and n8n workflow screenshots
├── outputs/                          Model results, predictions, forward-check results, agent input file
├── NHS_AE_Data_Preparation.ipynb     Step 1: clean, merge, baseline, risk flag, features
├── NHS_AE_EDA.ipynb                  Step 2: exploratory data analysis
├── NHS_AE_Forecasting.ipynb          Step 3: models, evaluation, forward check, agent input file
├── requirements.txt                  Python packages
└── README.md
```

Requirements: Python 3.10+.

```bash
pip install -r requirements.txt
```

1. **Notebooks** (from the repository root, in order): `NHS_AE_Data_Preparation.ipynb` → `NHS_AE_EDA.ipynb` → `NHS_AE_Forecasting.ipynb`.
2. **Dashboard:** `python ae_dashboard/app.py`, then open http://127.0.0.1:7860. It reads `Dataset/02_clean_Monthly_AE_data.csv` and `outputs/predictions_with_riskflag.csv` relative to the folder you run it from.
3. **Agent:** see *Run the agent* in Section 2.

---

## 7. Limitations, next steps and reuse

**Limitations**
- National monthly data only; local and trust-level differences are hidden.
- Only 179 months can be modelled, and the 3-year baseline moves with demand (Covid-19 months distort it).
- Headline scores overstate how well the model predicts ahead; see the forward check.
- Recent months are almost all rated Medium (17 of the last 18), so the Medium band needs refining.
- Risk thresholds are a judgement and are not clinically validated.
- The agent has not yet been reviewed by A&E managers, and the project has not been assessed under DCB0129 / DCB0160.

**Next steps:** test with A&E managers; refine the Medium band and baseline; move to trust-level data (MSitAE and ECDS); complete a clinical-safety and governance review.

**Reuse beyond the NHS:** the same five-step pattern (operational data → forecast or risk score → transparent rule → plain-English recommendation → human decision and log) could serve other services. Only the NHS A&E version has been built and tested.

---

*Data: NHS England Monthly A&E Time Series (Open Government Licence). Research prototype; decision support only.*
