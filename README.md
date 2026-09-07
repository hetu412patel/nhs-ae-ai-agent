# NHS A&E AI Agent — Operational Decision Support

AI Agent for NHS A&E operational decision support — forecasting, risk classification, an interactive Power BI dashboard, and an n8n + Ollama AI Agent that turns predictions into manager-facing recommendations.

## Overview

Predicting A&E pressure is not the same as acting on it — 123 NHS trusts already have forecasting tools live, but the output still sits on a dashboard for a manager to interpret manually. This project closes that gap with a free, end-to-end pipeline that takes 16 years of real NHS England A&E data, cleans and forecasts it in Python (Jupyter notebook), calculates a transparent risk flag, visualises it in an interactive Power BI dashboard, and — through a self-hosted n8n + Ollama AI Agent — turns the forecast into a plain-English recommendation that is logged to Google Sheets and emailed directly to a manager.

## Key Results

| Metric | Result |
|---|---|
| Forecasting model | Linear Regression |
| Forecast RMSE | 72,285 patients |
| Forecast R² | 0.907 (explains over 90% of monthly variance) |
| Improvement over baseline | 68.8% better than a seasonal-naive baseline |
| Risk classification model | Logistic Regression |
| Classification accuracy / F1 | 79.9% / 77.9% |
| Dataset coverage | 191 months (Aug 2010 – Jun 2026), 16 years of NHS England A&E data |

## Project Pipeline

**Clean the Data** (Python) → **Explore & Forecast** (Python / Jupyter) → **Build Risk Flag** (rule base) → **Visualise** (Power BI) → **Build AI Agent** (n8n + Ollama) → **Deliver & Log** (Google Sheets + Gmail)

## Repository Structure

```
nhs-ae-ai-agent/
├── README.md
├── Dataset/
│   ├── 01_raw_Monthly-AE-Time-Series.csv     # Raw NHS England A&E workbook
│   └── 02_clean_Monthly_AE_data.csv          # Cleaned, analysis-ready dataset
├── outputs/
│   ├── predictions_with_riskflag.csv         # Forecasted attendances + predicted risk flag
│   ├── model_comparison_regression.csv       # Regression model comparison (RMSE, MAE, R²)
│   ├── model_comparison_classification.csv   # Classification model comparison (accuracy, F1)
│   └── confusion_matrix.csv                  # Risk classifier confusion matrix
├── NHS_AE_Data_Preparation.ipynb             # Raw Excel → clean, one-row-per-month dataset
├── NHS_AE_EDA.ipynb                          # Exploratory analysis: seasonal patterns, performance trends, correlations
├── NHS_AE_Forecasting.ipynb                  # Attendance forecasting + risk classification models
└── NHS_A&E_Dashboard.pbix                    # Power BI dashboard file
```

## Tech Stack

| Layer | Tool |
|---|---|
| Data cleaning & analysis | Python (pandas, NumPy), Jupyter notebook |
| Forecasting & classification | Python (scikit-learn) |
| Visualisation | Power BI |
| AI Agent / automation | n8n (self-hosted), Ollama (local LLM) |
| Delivery & logging | Google Sheets, Gmail |

## How to Run the Notebooks

1. Clone the repository:
```
   git clone https://github.com/hetu412patel/nhs-ae-ai-agent.git
   cd nhs-ae-ai-agent
```
2. Install dependencies:
```
   pip install pandas numpy scikit-learn matplotlib seaborn jupyter
```
3. Run the notebooks in order:
   - `NHS_AE_Data_Preparation.ipynb`
   - `NHS_AE_EDA.ipynb`
   - `NHS_AE_Forecasting.ipynb`
4. Open `NHS_A&E_Dashboard.pbix` in Power BI Desktop to explore the live dashboard

## Dashboard Preview

**A&E Pressure Overview Dashboard**

<img width="947" height="745" alt="image" src="https://github.com/user-attachments/assets/47040b9b-f82f-421b-a596-16757b4e2ad1" />


**A&E Detailed Trend**

<img width="1322" height="742" alt="image" src="https://github.com/user-attachments/assets/8f62511f-b3a7-4d67-8e85-2c7a92a6f839" />


## Project Status

**Built now:** forecasting model, risk classifier, live Power BI dashboard, and the full n8n + Ollama AI Agent pipeline — all built and tested end-to-end.

**Future scope:** manager feedback learning loop, trust-level granular data across 100+ NHS trusts.
