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

<img width="1492" height="267" alt="n8n AI agent workflow" src="https://github.com/user-attachments/assets/67da2cfd-9dbd-499d-ac5b-8a4508562899" />

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
├── ae_dashboard/
│   └── app.py                                   Gradio dashboard (Operational Risk Board)
├── Dataset/                                     Raw NHS workbook (.xls) and cleaned dataset (02_clean_Monthly_AE_data.csv)
├── Literature Review/                           Sources and notes behind the research gap
├── Other/                                       Supporting files
├── figures/                                     Charts, diagrams, dashboard and n8n workflow screenshots
├── outputs/                                     Model results, predictions, forward-check results, agent input file
├── NHS_AE_Data_Preparation.ipynb                Step 1: clean, merge, baseline, risk flag, features
├── NHS_AE_EDA.ipynb                             Step 2: exploratory data analysis
├── NHS_AE_Forecasting.ipynb                     Step 3: models, evaluation, forward check, agent input file
├── NHS_AE_Operational_Intelligence_Report.docx  Full project report (Word)
├── NHS_AE_Operational_Intelligence_Report.pdf   Full project report (PDF)
├── NHS_AE_Operational_Intelligence_Report.pptx  Final presentation slides
├── NHS_AI_Agent.pptx                            AI agent walkthrough slides
├── requirements.txt                             Python packages for the whole project
└── README.md
```

### Run the project

You can run the project in three stages. Stages A and B need no accounts or credentials. Stage C (the AI agent) is optional and needs free Google credentials of your own.

#### Before you start

- Python 3.10+ and Git.
- Clone the repository and run every command **from the repository root**:

```bash
git clone https://github.com/hetu412patel/nhs-ae-ai-agent.git
cd nhs-ae-ai-agent
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

#### A. Build the data and models (notebooks)

Open and run these in order (Jupyter or VS Code):

1. `NHS_AE_Data_Preparation.ipynb` → creates `Dataset/02_clean_Monthly_AE_data.csv`
2. `NHS_AE_EDA.ipynb` → charts and key findings
3. `NHS_AE_Forecasting.ipynb` → model comparison, forward check, and the files in `outputs/`

Check that `outputs/` now contains `predictions_with_riskflag.csv`, `model_comparison_regression.csv`, `model_comparison_classification.csv`, `confusion_matrix.csv`, `forward_check_results.csv` and `Automation_ready_data.csv`.

#### B. Launch the dashboard

```bash
python ae_dashboard/app.py
```

Open http://127.0.0.1:7860. It reads `Dataset/02_clean_Monthly_AE_data.csv` and `outputs/predictions_with_riskflag.csv`, so run stage A first and run the command from the repository root.

#### C. Run the AI agent (optional)

**1. Install the tools**

- Install [Node.js](https://nodejs.org) (LTS), then n8n:

  ```bash
  npm install -g n8n
  ```

- Install [Ollama](https://ollama.com), then download a model and keep Ollama running:

  ```bash
  ollama pull <model>
  ```

  Use the model named in the project report (Appendix C, included in this repository), or any model your machine can run.

**2. Point n8n at the data file**

n8n reads local files only from its files folder, by default `.n8n-files` in your home directory. Set an environment variable with that path so the Forecasting notebook can copy `Automation_ready_data.csv` there for you.

```powershell
# Windows (PowerShell), then restart your terminal and Jupyter / VS Code
setx N8N_FILES_DIR "C:\Users\<you>\.n8n-files"
```

```bash
# macOS / Linux (add to ~/.bashrc or ~/.zshrc to keep it)
export N8N_FILES_DIR="$HOME/.n8n-files"
```

Re-run the last cell of `NHS_AE_Forecasting.ipynb`. It prints a line confirming the copy. If you skip this step, copy `outputs/Automation_ready_data.csv` into the folder by hand.

**3. Create your own Google credentials (needed for Google Sheets and Gmail)**

Credentials are **not** included in this repository and must never be committed. Each person creates their own, free:

1. Go to [Google Cloud Console](https://console.cloud.google.com), create a project, and enable the **Gmail API** and **Google Sheets API**.
2. Configure the **OAuth consent screen** and add your own Google account as a **test user**.
3. Create an **OAuth client ID** (type: Web application). Add the redirect URL that n8n shows when you create a Google credential (usually `http://localhost:5678/rest/oauth2-credential/callback`).
4. Copy the **Client ID** and **Client Secret** into n8n: *Credentials → Create → Gmail OAuth2 / Google Sheets OAuth2*, then click *Sign in with Google*.
5. Create a Google Sheet for the log, with a header row matching the columns set in the **Edit Fields1** node (for example month, risk level, recommendation, timestamp).

**4. Build the workflow in n8n**

```bash
n8n start
```

Open http://localhost:5678 and create the workflow shown in [The AI Agent](#2-the-ai-agent-n8n--ollama), node by node:

| Node | Setting to use |
|---|---|
| Schedule Trigger | Once a month |
| Read/Write Files from Disk | Read file `Automation_ready_data.csv` from the n8n files folder |
| Extract from File | Operation: Extract From CSV |
| Sort / Limit | Sort by `Month` (newest first), limit to 1 item |
| Edit Fields | Map the CSV columns you want the model to quote |
| Basic LLM Chain + Ollama Chat Model | Ollama credential base URL `http://localhost:11434`; choose your model; paste the prompt from Appendix C of the project report (included in this repository) |
| Edit Fields1 | Shape the reply into the log columns |
| Append row in sheet | Google Sheets credential, your log sheet |
| If | Send to the email branch when the risk level is Medium or High |
| Send a message | Gmail credential, the manager's address |

**5. Test it**

Click *Execute workflow* once. Confirm that a new row appears in your Google Sheet and, if the latest month is Medium or High, that the email arrives. Then activate the workflow so the monthly schedule runs on its own.

### Troubleshooting

| Problem | Fix |
|---|---|
| Dashboard says a CSV is missing | Run stage A first, and run `python ae_dashboard/app.py` from the repository root. |
| `launch() got an unexpected keyword argument` | Your Gradio is too old: `pip install -U "gradio>=6.0"`. |
| Forecasting notebook does not copy the agent file | Set `N8N_FILES_DIR`, restart the terminal and Jupyter / VS Code, and re-run the last cell. |
| n8n cannot read the CSV | The file must be inside the n8n files folder (default `~/.n8n-files`). |
| n8n cannot reach the model | Check Ollama is running and the base URL is `http://localhost:11434`. |
| Google says "access blocked" or a redirect mismatch | Add your account as a test user, and make the OAuth redirect URL exactly match the one n8n shows. |

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
