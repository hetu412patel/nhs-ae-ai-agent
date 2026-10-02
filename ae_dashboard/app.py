"""
A&E Operational Risk Board  -  Gradio version of AE_Operational_Risk_Dashboard.html
Run:   python app.py      then open http://127.0.0.1:7860
Data:  ae_data.csv (monthly A&E data + risk flag), pred_data.csv (actual vs model prediction)
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import gradio as gr

# ============================================================ 1. CONSTANTS
RISK_COLOR = {"Low": "#2E8540", "Medium": "#C77700", "High": "#C81E0F"}
RISK_ORDER = {"Low": 0, "Medium": 1, "High": 2}
SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
RISKS = ["Low", "Medium", "High"]

FEATURES = {  # column -> plain-English label
    "TotalAttendances": "Total attendances",
    "MajorAE_Attendances": "Major A&E attendances",
    "MinorInjuryUnit_Attendances": "Minor injury unit attendances",
    "TotalAdmissions": "Total admissions",
    "PercentWithin4hrs": "4-hour performance",
    "MajorInjuryPerformancePct": "Major injury performance",
    "MinorInjuryPerformancePct": "Minor injury performance",
    "SingleSpecialityPerformancePct": "Single specialty performance",
    "AdmissionRate": "Admission rate",
    "Breach12hrRate": "12-hour breach rate",
    "MajorAE_SharePct": "Major A&E share of demand",
}
TREND_METRICS = {  # dropdown label -> (column, axis label, target line)
    "Attendances": ("TotalAttendances", "Attendances", None),
    "4-hour wait performance": ("PercentWithin4hrs", "4-hour wait performance (%)", 95),
    "Admission rate": ("AdmissionRate", "Admission rate (%)", None),
    "Long waits (12hr+)": ("Breach12hrRate", "Long waits, 12hr+ (%)", None),
    "Overall pressure score": ("PressureIndex", "Overall pressure score", None),
}
EXPLORER = {**{v: k for k, v in FEATURES.items()}, "Overall pressure score": "PressureIndex"}
FORECAST_WINDOWS = {"Last 12 months": 12, "Last 24 months": 24, "Last 36 months": 36}

# ============================================================ 2. DATA + DERIVED FIELDS
df = pd.read_csv("Dataset/02_clean_Monthly_AE_data.csv", parse_dates=["Month"])
pred = pd.read_csv("outputs/predictions_with_riskflag.csv", parse_dates=["Month"])
CLEAN = df[df["RiskFlag"].isin(RISKS)].copy()

def _norm(s, lo, hi):
    return (s - lo) / (hi - lo) if hi != lo else s * 0

att = _norm(df.TotalAttendances, CLEAN.TotalAttendances.min(), CLEAN.TotalAttendances.max())
gap_c = 100 - CLEAN.PercentWithin4hrs.dropna()
gap = _norm(100 - df.PercentWithin4hrs, gap_c.min(), gap_c.max())
brc = CLEAN.Breach12hrRate
brr = _norm(df.Breach12hrRate, brc.min(), brc.max())
df["PressureIndex"] = (100 * (0.40 * att + 0.35 * gap + 0.25 * brr)).round()   # NaN if any input missing
df["RiskScore"] = df.RiskFlag.map(RISK_ORDER)
df["BaselineRatio"] = df.TotalAttendances / df.SeasonalBaselineAvg
CLEAN = df[df["RiskFlag"].isin(RISKS)].copy()
YEARS = sorted(df.Year.unique().tolist())
DATA_THROUGH = CLEAN.Month.max().strftime("%b %Y")

# ============================================================ 3. HELPERS
def fmt_int(v): return "–" if pd.isna(v) else f"{round(v):,}"
def fmt_pct(v, d=1): return "–" if pd.isna(v) else f"{v:.{d}f}%"
def fmt_month(m): return pd.Timestamp(m).strftime("%b %Y")

def get_filtered(y_from, y_to, seasons, risks):
    y_from, y_to = min(y_from, y_to), max(y_from, y_to)
    d = CLEAN[(CLEAN.Year >= y_from) & (CLEAN.Year <= y_to)
              & CLEAN.Season.isin(seasons or []) & CLEAN.RiskFlag.isin(risks or [])]
    return d.sort_values("Month")

def base_layout(fig, height=300, legend=False):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="white",
        plot_bgcolor="white", font=dict(size=11, color="#0B1F33"), showlegend=legend,
        legend=dict(orientation="h", y=-0.2), hovermode="closest")
    fig.update_xaxes(showgrid=False, linecolor="#D7DEE6")
    fig.update_yaxes(gridcolor="#EEF2F6", linecolor="#D7DEE6")
    return fig

def empty_fig(msg, height=300):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=13, color="#8494A5"))
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return base_layout(fig, height)

# ============================================================ 4. KPI STRIP
def delta(curr, prior, higher_is_bad):
    if pd.isna(curr) or pd.isna(prior) or prior == 0:
        return "–", "flat"
    d = curr - prior
    pct = abs(d / abs(prior)) * 100
    rising = d > 0
    cls = ("up" if rising else "down") + (" bad" if higher_is_bad == rising else " good")
    arrow = "▲" if rising else ("▼" if d < 0 else "·")
    return f"{arrow} {pct:.1f}% vs prior month in view", cls

def kpi_html(d):
    if d.empty:
        return '<div class="kpistrip"><div class="kpi" style="grid-column:1/-1;color:#5B6B7C;">No months match the current filters. Try widening the period, season or risk selection.</div></div>'
    last = d.iloc[-1]
    prev = d.iloc[-2] if len(d) > 1 else pd.Series(dtype=float)
    g = lambda k: prev.get(k, np.nan)
    if pd.isna(last.BaselineRatio):
        base = "no 3-yr baseline yet"
    else:
        p = (last.BaselineRatio - 1) * 100
        base = f"{abs(p):.1f}% {'above' if p >= 0 else 'below'} 3-yr {last.Month.strftime('%b')} baseline"
    perf = last.PercentWithin4hrs
    perf_sub = f"{95 - perf:.1f}pt below target" if pd.notna(perf) and perf < 95 else "at or above target"
    a, b, c, e, f = (delta(last.TotalAttendances, g("TotalAttendances"), True),
                     delta(perf, g("PercentWithin4hrs"), False),
                     delta(last.AdmissionRate, g("AdmissionRate"), False),
                     delta(last.Breach12hrRate, g("Breach12hrRate"), True),
                     delta(last.PressureIndex, g("PressureIndex"), True))
    press = "–" if pd.isna(last.PressureIndex) else int(last.PressureIndex)
    card = lambda label, val, dl, sub: (f'<div class="kpi"><div class="klabel">{label}</div>{val}'
        + (f'<div class="kdelta {dl[1]}">{dl[0]}</div>' if dl else "") + f'<div class="ksub">{sub}</div></div>')
    return '<div class="kpistrip">' + "".join([
        card("TOTAL ATTENDANCES", f'<div class="kval">{fmt_int(last.TotalAttendances)}</div>', a, base),
        card("4-HOUR PERFORMANCE", f'<div class="kval">{fmt_pct(perf)}<span class="kunit">/ 95% target</span></div>', b, perf_sub),
        card("ADMISSION RATE", f'<div class="kval">{fmt_pct(last.AdmissionRate)}</div>', c, "of attendances admitted"),
        card("12-HOUR BREACH RATE", f'<div class="kval">{fmt_pct(last.Breach12hrRate, 2)}</div>', e, "share waiting over 12hrs"),
        card("PRESSURE SCORE", f'<div class="kval">{press}<span class="kunit">/100</span></div>', f, "how busy + how slow + how many long waits, in one number"),
        card("RISK LEVEL", f'<div class="badge badge-{last.RiskFlag}">{last.RiskFlag.upper()}</div>', None, "Based on how far above normal this month is"),
    ]) + "</div>"

def summary_text(d, y_from, y_to, seasons, risks):
    s = "all seasons" if len(seasons or []) == 4 else ", ".join(seasons or []) or "no seasons"
    r = "all risk levels" if len(risks or []) == 3 else ", ".join(risks or []) or "no risk levels"
    return f'<div class="filter-summary"><span class="livedot"></span><span class="dt">Data through <b>{DATA_THROUGH}</b></span><span class="sep">|</span>{len(d)} months · {min(y_from, y_to)}–{max(y_from, y_to)} · {s} · {r}</div>'

# ============================================================ 5. CHARTS
def trend_fig(y_from, y_to, seasons, risks, metric_label):
    d = get_filtered(y_from, y_to, seasons, risks)
    col, axis_label, target = TREND_METRICS[metric_label]
    if d.empty: return empty_fig("No months match the current filters.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d.Month, y=d[col], mode="lines+markers", line=dict(color="#005EB8", width=1.5, shape="spline", smoothing=0.4),
        fill="tozeroy" if False else None, connectgaps=True,
        marker=dict(color=[RISK_COLOR[r] for r in d.RiskFlag], size=4 if len(d) > 60 else 7),
        customdata=d.RiskFlag, hovertemplate="%{x|%b %Y}<br>%{y:,.2f}  ·  risk: %{customdata}<extra></extra>"))
    if target:
        fig.add_hline(y=target, line_dash="dash", line_color="#8494A5", annotation_text="95% target",
                      annotation_position="bottom right")
    fig.update_yaxes(title_text=axis_label, tickfont=dict(size=10), title_font=dict(size=11))
    fig.update_xaxes(title_text="Year", title_font=dict(size=11), title_standoff=6,
                     tickfont=dict(size=10), tickformat="%Y", dtick="M12", tickangle=0, automargin=True)
    fig.update_yaxes(automargin=True)
    fig = base_layout(fig, 300)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    return fig

def drivers_fig(y_from, y_to, seasons, risks):
    d = get_filtered(y_from, y_to, seasons, risks)
    if d.RiskScore.nunique() < 2:
        return empty_fig("Select more than one risk level above to see this chart.", 220)
    rows = []
    for col, label in FEATURES.items():
        s = d[[col, "RiskScore"]].dropna()
        if len(s) >= 3 and s[col].std() > 0:
            rows.append((label, s[col].corr(s.RiskScore)))
    rows = sorted(rows, key=lambda t: abs(t[1]), reverse=True)[:8][::-1]
    if not rows: return empty_fig("Not enough data in this view.", 220)
    fig = go.Figure(go.Bar(
        x=[r[1] for r in rows], y=[r[0] for r in rows], orientation="h",
        marker_color=["#C81E0F" if r[1] >= 0 else "#005EB8" for r in rows],
        hovertemplate="strength of link: %{x:.2f}<extra></extra>"))
    fig.update_xaxes(range=[-1, 1], showticklabels=False, showgrid=True, gridcolor="#EEF2F6")
    fig.update_yaxes(showgrid=False)
    fig = base_layout(fig, 270)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=40))
    fig.add_annotation(text="🔴 higher when risk is high   🔵 lower when risk is high", xref="paper", yref="paper",
                       x=-0.1, y=-0.1, showarrow=False, font=dict(size=10, color="#5B6B7C"), xanchor="left")
    return fig

def season_fig(y_from, y_to, seasons, risks):
    d = get_filtered(y_from, y_to, seasons, risks)
    counts = d.groupby(["Season", "RiskFlag"]).size().unstack(fill_value=0).reindex(SEASONS, fill_value=0)
    fig = go.Figure([go.Bar(name=r, x=SEASONS, y=counts[r] if r in counts else [0] * 4,
                            marker_color=RISK_COLOR[r]) for r in RISKS])
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title_text="Season", title_font=dict(size=11), title_standoff=6,
                     tickfont=dict(size=10), automargin=True)
    fig.update_yaxes(title_text="Number of months", title_font=dict(size=11),
                     tickfont=dict(size=10), automargin=True)
    fig = base_layout(fig, 250, legend=True)
    fig.update_layout(margin=dict(l=10, r=10, t=34, b=10),
                      legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom",
                                  font=dict(size=10.5), title=dict(text="Risk level:  ", font=dict(size=10.5))))
    return fig

def explorer_fig(y_from, y_to, seasons, risks, x_label, y_label):
    d = get_filtered(y_from, y_to, seasons, risks)
    xk, yk = EXPLORER[x_label], EXPLORER[y_label]
    d = d.dropna(subset=[xk, yk])
    if d.empty: return empty_fig("No months match the current filters.", 380)
    fig = go.Figure()
    for r in RISKS:
        s = d[d.RiskFlag == r]
        fig.add_trace(go.Scatter(x=s[xk], y=s[yk], mode="markers", name=r, marker=dict(color=RISK_COLOR[r], size=8),
                                 text=s.Month.dt.strftime("%b %Y"),
                                 hovertemplate="%{text}<br>" + x_label + ": %{x:,.1f}<br>" + y_label + ": %{y:,.1f}<extra></extra>"))
    fig.update_xaxes(title_text=x_label); fig.update_yaxes(title_text=y_label)
    return base_layout(fig, 380, legend=True)

def high_risk_table(y_from, y_to, seasons, risks):
    d = get_filtered(y_from, y_to, seasons, risks)
    d = d[d.RiskFlag == "High"].sort_values("Month", ascending=False)
    cols = ["Month", "Attendances", "vs 3-yr baseline", "4-hour performance", "12-hour breach rate"]
    if d.empty:
        return pd.DataFrame([["No High-risk months in the current filter selection.", "", "", "", ""]], columns=cols)
    return pd.DataFrame({
        cols[0]: d.Month.map(fmt_month), cols[1]: d.TotalAttendances.map(fmt_int),
        cols[2]: d.BaselineRatio.map(lambda v: "–" if pd.isna(v) else f"+{(v - 1) * 100:.1f}%"),
        cols[3]: d.PercentWithin4hrs.map(fmt_pct), cols[4]: d.Breach12hrRate.map(lambda v: fmt_pct(v, 2))})

def forecast_fig(window_label):
    r = pred.tail(FORECAST_WINDOWS[window_label])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=r.Month, y=r.TotalAttendances, name="Actual", mode="lines+markers",
                             line=dict(color="#00205B", width=2), marker=dict(size=4)))
    fig.add_trace(go.Scatter(x=r.Month, y=r.PredictedTotalAttendances, name="Model predicted", mode="lines+markers",
                             line=dict(color="#C77700", width=2, dash="dot"), marker=dict(size=4)))
    fig.update_yaxes(tickformat=".2s")
    return base_layout(fig, 320, legend=True)

# ============================================================ 6. ORCHESTRATION
def update_all(y_from, y_to, seasons, risks, metric, x_label, y_label):
    d = get_filtered(y_from, y_to, seasons, risks)
    return (summary_text(d, y_from, y_to, seasons, risks), kpi_html(d),
            trend_fig(y_from, y_to, seasons, risks, metric),
            drivers_fig(y_from, y_to, seasons, risks), season_fig(y_from, y_to, seasons, risks),
            explorer_fig(y_from, y_to, seasons, risks, x_label, y_label),
            high_risk_table(y_from, y_to, seasons, risks))

CSS = """
/* ================= base / no page scrollbar ================= */
html,body{height:100%;margin:0;overflow:hidden !important;}
.gradio-container{height:100dvh !important;overflow:hidden !important;background:#EAEFF4 !important;
  max-width:1600px !important;font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
  display:flex !important;flex-direction:column !important;padding:8px 14px !important;box-sizing:border-box;}
.gradio-container .block{padding:0;}
.gradio-container .main.fillable.app{min-height:0 !important;flex:1 1 auto !important;}
.gradio-container .main.fillable.app > .wrap{min-height:0 !important;}
main.contain{min-height:0 !important;flex:1 1 auto !important;padding:0 !important;}
main.contain > .column{min-height:0 !important;flex:1 1 auto !important;display:flex !important;
  flex-direction:column !important;gap:5px !important;}

/* ================= SS2: hide footer entirely ================= */
footer, .gradio-container footer, .built-with, .show-api, .settings{display:none !important;}

/* ================= things that must NEVER shrink ================= */
.filterbar, .kpiwrap, .headrow, .footwrap{flex:0 0 auto !important;}

/* ================= slim top bar ================= */
.topbar-row{flex:0 0 auto !important;background:linear-gradient(180deg,#00205B,#001A4D) !important;border-radius:5px !important;
  padding:5px 16px !important;align-items:center !important;flex-wrap:nowrap !important;gap:10px !important;min-height:0 !important;}
.topbar-row > *{background:transparent !important;border:none !important;box-shadow:none !important;padding:0 !important;min-width:0 !important;}
.topbar-row .block{background:transparent !important;border:none !important;padding:0 !important;min-height:0 !important;}
.topbar-row > :first-child{flex:1 1 auto !important;}
.topbar-row > :last-child{flex:0 1 auto !important;text-align:right;}
.topbar{display:flex;align-items:baseline;gap:12px;color:#fff;}
.topbar h1{font-size:15px;font-weight:700;margin:0;color:#fff;white-space:nowrap;}
.topbar .sub{color:#AFC6E8;font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.filter-summary{font-size:11px;color:#CFE0F5;font-family:ui-monospace,Consolas,monospace;line-height:1.2;white-space:nowrap;}
.filter-summary b{color:#fff;font-weight:700;}
.filter-summary .dt{color:#fff;font-weight:600;}
.filter-summary .sep{margin:0 10px;color:#5F7FB0;}
.livedot{width:7px;height:7px;border-radius:50%;background:#4FD17A;display:inline-block;box-shadow:0 0 0 3px rgba(79,209,122,.25);margin-right:7px;}

/* ================= SS1: filter bar — one tidy row of pills, like the reference ================= */
.filterbar{background:#fff !important;border:1px solid #D7DEE6 !important;border-radius:6px !important;
  padding:5px 14px !important;gap:16px !important;align-items:center !important;flex-wrap:nowrap !important;}
.filterbar .form{flex:0 0 auto !important;display:flex !important;align-items:center !important;
  gap:18px !important;background:transparent !important;border:none !important;padding:0 !important;}
.filterbar .block, .filterbar fieldset{border:none !important;box-shadow:none !important;
  background:transparent !important;padding:0 !important;margin:0 !important;}
.filterbar span[data-testid="block-info"]{font-size:10.5px !important;font-weight:700 !important;
  letter-spacing:.04em;color:#5B6B7C !important;margin:0 8px 0 0 !important;text-transform:uppercase;}
.filterbar .yr{flex:0 0 auto !important;width:auto !important;min-width:auto !important;display:flex !important;
  align-items:center !important;gap:6px !important;}
.filterbar .yr .wrap{width:100px !important;min-width:100px !important;}
.gradio-container .icon-wrap{z-index:5 !important;}
.filterbar .yr input{height:32px !important;font-size:13.5px !important;padding:0 6px !important;min-width:0 !important;}
.filterbar .yr{padding:0 !important;min-height:0 !important;}
.filterbar .yr .container, .headrow .dd .container{display:flex !important;flex-direction:row !important;align-items:center !important;gap:8px !important;background:transparent !important;padding:0 !important;margin:0 !important;}
.filterbar .yr .container > span, .headrow .dd .container > span{margin:0 !important;white-space:nowrap;}
.filterbar .yr .wrap, .headrow .dd .wrap{background:#F3F5F7 !important;border-radius:5px !important;box-shadow:none !important;min-height:32px !important;height:32px !important;}
.filterbar .cg{flex:0 0 auto !important;width:auto !important;min-width:auto !important;
  max-width:none !important;overflow:visible !important;display:flex !important;align-items:center !important;}
.filterbar .cg > span[data-testid="block-info"]{margin-right:10px !important;}
.filterbar .cg .wrap{display:flex !important;flex-direction:row !important;flex-wrap:nowrap !important;
  gap:6px !important;padding:0 !important;width:auto !important;}
.filterbar .cg label{flex:0 0 auto !important;height:32px !important;padding:0 16px !important;
  display:inline-flex !important;align-items:center !important;justify-content:center !important;
  border-radius:999px !important;font-size:12.5px !important;font-weight:600 !important;white-space:nowrap;
  cursor:pointer !important;background:#EEF1F4;color:#5B6B7C;border:1px solid #E4E9EE;
  transition:background .12s,color .12s,border-color .12s;}
.filterbar .cg label input[type="checkbox"]{display:none !important;}
.filterbar .cg label span{pointer-events:none;}
.filterbar .cg label:has(input[name="Spring"]).selected,
.filterbar .cg label:has(input[name="Summer"]).selected,
.filterbar .cg label:has(input[name="Autumn"]).selected,
.filterbar .cg label:has(input[name="Winter"]).selected{background:#005EB8 !important;color:#fff !important;border-color:#005EB8 !important;}
.filterbar .cg label:has(input[name="Low"]).selected{background:#2E8540 !important;color:#fff !important;border-color:#2E8540 !important;}
.filterbar .cg label:has(input[name="Medium"]).selected{background:#C77700 !important;color:#fff !important;border-color:#C77700 !important;}
.filterbar .cg label:has(input[name="High"]).selected{background:#C81E0F !important;color:#fff !important;border-color:#C81E0F !important;}
.filterbar button.reset{height:32px !important;min-height:32px !important;padding:0 18px !important;
  font-size:13px !important;font-weight:600;border-radius:5px !important;white-space:nowrap;
  cursor:pointer !important;margin-left:auto !important;}

/* ================= tabs / pages ================= */
.tabswrap{flex:1 1 auto !important;min-height:0 !important;display:flex !important;
  flex-direction:column !important;overflow:hidden !important;}
.tabswrap > div[role="tablist"]{flex:0 0 auto !important;border-bottom:2px solid #D7DEE6 !important;margin-bottom:2px !important;}
.tabswrap button[role="tab"]{font-size:13px !important;font-weight:600 !important;padding:4px 16px !important;cursor:pointer !important;}
.tabswrap button[role="tab"][aria-selected="true"]{color:#005EB8 !important;border-color:#005EB8 !important;}
.tabswrap > .tabitem{flex:1 1 auto !important;min-height:0 !important;
  flex-direction:column !important;gap:5px !important;overflow:hidden !important;padding:0 !important;border:none !important;background:transparent !important;}
.tabswrap > .tabitem > .column{flex:1 1 auto !important;min-height:0 !important;display:flex !important;
  flex-direction:column !important;gap:5px !important;overflow:hidden !important;}

.tabswrap > .tab-wrapper{margin:0 0 4px 0 !important;padding:0 !important;flex:0 0 auto !important;}
.topbar-row > *{height:auto !important;}
.topbar-row .html-container, .topbar-row .prose{padding:0 !important;margin:0 !important;min-height:0 !important;}

/* the two-column row of charts inside a tab */
.tabrow{flex:1 1 auto !important;min-height:0 !important;overflow:hidden !important;}

/* each chart/table panel */
.panel, .tabrow > .column{background:#fff;border:1px solid #D7DEE6;border-radius:6px;padding:6px 10px !important;gap:2px !important;
  min-width:0;height:100% !important;display:flex !important;flex-direction:column !important;
  min-height:0 !important;overflow:hidden !important;}
.sec-title{font-size:13px;font-weight:700;color:#0B1F33;margin:0;}
.sec-sub{display:none;}
.headrow{align-items:flex-end !important;gap:10px !important;flex-wrap:nowrap !important;}
.headrow > .column{flex:1 1 0% !important;min-width:0 !important;}
.headrow .form{background:transparent !important;border:none !important;box-shadow:none !important;padding:0 !important;display:flex !important;gap:10px !important;flex:0 0 auto !important;}
.headrow .dd{flex:0 0 auto !important;width:auto !important;min-width:0 !important;padding:0 !important;min-height:0 !important;}
.headrow .dd .wrap{width:170px !important;}
.headrow .dd span[data-testid="block-info"]{font-size:11.5px !important;color:#5B6B7C !important;}
.headrow .dd input{height:30px !important;font-size:12.5px !important;}
.headrow{margin-bottom:2px !important;}

/* ================= KPI strip ================= */
.kpistrip{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));background:#fff;
  border:1px solid #D7DEE6;border-radius:6px;}
.kpi{padding:6px 12px;border-right:1px solid #E4E9EE;min-width:0;} .kpi:last-child{border-right:none;}
.klabel{font-size:10px;color:#5B6B7C;font-weight:600;margin-bottom:1px;}
.kval{font-family:ui-monospace,Consolas,monospace;font-size:17px;font-weight:700;color:#0B1F33;
  display:flex;align-items:baseline;gap:6px;}
.kunit{font-size:12px;color:#8494A5;font-weight:500;}
.kdelta{font-family:ui-monospace,Consolas,monospace;font-size:10px;margin-top:1px;font-weight:600;}
.kdelta.flat{color:#8494A5;} .kdelta.good{color:#2E8540;} .kdelta.bad{color:#C81E0F;}
.ksub{display:none;}
.badge{display:inline-block;font-family:ui-monospace,Consolas,monospace;font-size:14px;font-weight:700;
  padding:1px 10px;border-radius:3px;}
.badge-Low{background:#E4F3E6;color:#2E8540;} .badge-Medium{background:#FFF3DE;color:#C77700;}
.badge-High{background:#FCE7E4;color:#C81E0F;}
.footnote{font-size:10.5px;color:#8494A5;padding-top:2px;flex:0 0 auto !important;}
.globalfoot{padding:0 4px !important;margin:0 !important;font-size:10px !important;line-height:1.1 !important;}
.footwrap, .footwrap .html-container, .footwrap .prose{min-height:0 !important;height:auto !important;padding:0 !important;margin:0 !important;border:none !important;background:transparent !important;}

/* titles / footnotes keep their natural height */
.tabrow > .column > .block:not(.fit1):not(.fit2):not(.tbl){flex:0 0 auto !important;}

/* ================= charts + table fill whatever room is left, never get clipped ================= */
.fit1, .fit2{margin:0 !important;align-self:stretch !important;flex:1 1 auto !important;min-height:120px !important;height:auto !important;overflow:hidden !important;}
.fit1 > *, .fit2 > *,
.fit1 .js-plotly-plot, .fit2 .js-plotly-plot,
.fit1 .plot-container, .fit2 .plot-container,
.fit1 .svg-container, .fit2 .svg-container{height:100% !important;width:100% !important;}

/* table: fills the panel, scrolls inside itself */
.tbl{flex:1 1 0 !important;min-height:120px !important;height:auto !important;margin:0 !important;overflow:hidden !important;}


/* ================= PAGE 1 FIX: Overview charts get a definite height so they can never collapse ================= */
.tabrow.row1{flex:0 0 auto !important;overflow:visible !important;align-items:stretch !important;}
.tabrow.row1 > .column{height:auto !important;overflow:visible !important;}
.fit1{flex:none !important;height:calc(100dvh - 500px) !important;min-height:200px !important;overflow:hidden !important;}
.fit1 > *, .fit1 .js-plotly-plot, .fit1 .plot-container, .fit1 .svg-container{height:100% !important;width:100% !important;}


/* tighter Overview panels + safety net: if a window is extremely short the page scrolls instead of cutting the charts */
.tabrow.row1 > .column{gap:0 !important;padding-top:4px !important;padding-bottom:4px !important;}
.tabrow.row1 .headrow{margin-bottom:0 !important;}
.tabrow.row1 .headrow .dd .wrap{height:28px !important;min-height:28px !important;}
.tabswrap > .tabitem.tabitem{overflow-x:hidden !important;overflow-y:auto !important;}

/* ================= pointer / hand cursor everywhere a dropdown opens & closes on click ================= */
.gradio-container .icon-wrap, .gradio-container .icon-wrap *,
.gradio-container div[data-testid="dropdown"] input, .gradio-container input[role="combobox"],
.gradio-container ul.options li{cursor:pointer !important;}

/* ================= responsive ================= */
@media (max-width:1250px){
  .topbar .sub{display:none;}
}
@media (max-width:1150px){
  .filterbar{flex-wrap:wrap !important;row-gap:10px !important;}
  .filterbar button.reset{margin-left:0 !important;}
}
@media (max-width:900px), (max-height:640px){   /* phones / very short windows: allow scrolling instead of crushing content */
  html,body{overflow:auto !important;}
  .gradio-container{height:auto !important;min-height:100dvh !important;overflow:visible !important;}
  main.contain, main.contain > .column, .tabswrap, .tabswrap > .tabitem, .tabrow{min-height:0 !important;overflow:visible !important;}
  .fit1,.fit2,.tbl{height:340px !important;flex:none !important;}
  .headrow{flex-wrap:wrap !important;}
  .topbar .sub{display:none;}
  .filter-summary{white-space:normal;}
}
"""

# JS: (a) dropdown arrow opens on 1st click, closes on 2nd click (b) resize charts when a tab/page opens
JS = """
() => {
  if (window.__aeFix) return; window.__aeFix = true;
  // dropdown: 1st click opens, 2nd click (on the box or the arrow) closes
  document.addEventListener('mousedown', (e) => {
    const t = e.target;
    if (!t.closest) return;
    const wrap = t.closest('.secondary-wrap');
    const input = wrap && wrap.querySelector('input[role="combobox"]');
    if (!input) return;
    if (document.activeElement === input) { e.preventDefault(); e.stopPropagation(); input.blur(); }
  }, true);
  // keep every chart exactly the size of its box (fixes charts drawn while the page was still settling)
  // Overview charts: height = (window height) - (chart's own top edge) - (footer) - (panel padding/gaps). Deterministic, no feedback loop.
  const fitCharts = () => {
    if (window.innerWidth <= 900 || window.innerHeight <= 640) return;
    const els = [...document.querySelectorAll('.fit1')].filter(e => e.getBoundingClientRect().width > 50);
    if (!els.length) return;
    const foot = document.querySelector('.footwrap');
    const fh = foot ? foot.getBoundingClientRect().height : 16;
    const BOTTOM_RESERVE = 34;    // panel padding + container padding + gaps + safety  (raise if cut, lower if too much empty space)
    const top = Math.max(...els.map(e => e.getBoundingClientRect().top - e.getBoundingClientRect().height * 0 ));
    const h = Math.max(220, Math.floor(window.innerHeight - top - fh - BOTTOM_RESERVE));
    els.forEach(el => {
      if (Math.abs(el.getBoundingClientRect().height - h) <= 2) return;
      el.style.setProperty('height', h + 'px', 'important');
      [60, 250].forEach(ms => setTimeout(() => {
        const gd = el.querySelector('.js-plotly-plot');
        if (gd && window.Plotly) { try { window.Plotly.relayout(gd, {autosize: true, width: null, height: null}); window.Plotly.Plots.resize(gd); } catch (e) {} }
      }, ms));
    });
  };
  const refit = () => {
    fitCharts();
    if (!window.Plotly) return;
    document.querySelectorAll('.js-plotly-plot').forEach(gd => {
      const box = gd.parentElement; if (!box) return;
      const r = box.getBoundingClientRect();
      if (r.width < 50 || r.height < 50) return;
      const svg = gd.querySelector('svg.main-svg');
      const s = svg ? svg.getBoundingClientRect() : null;
      if (!s || Math.abs(s.width - r.width) > 3 || Math.abs(s.height - r.height) > 3) {
        try { window.Plotly.relayout(gd, {autosize: true, width: null, height: null}); window.Plotly.Plots.resize(gd); } catch (err) {}
      }
    });
  };
  let t = null;
  const later = () => { clearTimeout(t); t = setTimeout(refit, 120); };
  new MutationObserver(later).observe(document.body, {childList: true, subtree: true});
  window.addEventListener('resize', later);
  document.addEventListener('click', () => { [80, 300, 700, 1400].forEach(ms => setTimeout(refit, ms)); });
  const ro = new ResizeObserver(later);
  const watch = () => document.querySelectorAll('.fit1, .fit2').forEach(e => { if (!e.__ro) { e.__ro = 1; ro.observe(e); } });
  setInterval(() => { watch(); refit(); }, 700);
}
"""

HEADER = """<div class="topbar"><h1>A&amp;E Operational Risk Board</h1><span class="sub">A plain-English view of A&amp;E pressure, for managers</span></div>"""
sec = lambda t, s: gr.HTML(f'<p class="sec-title" title="{s}">{t}</p>')

with gr.Blocks(title="A&E Operational Risk Board") as demo:
    with gr.Row(elem_classes="topbar-row"):
        gr.HTML(HEADER)
        summary = gr.HTML()
    # ---- filter bar (single row, pill controls)
    with gr.Row(elem_classes="filterbar"):
        y_from = gr.Dropdown(YEARS, value=YEARS[0], label="PERIOD from", elem_classes="yr", scale=0, min_width=90, container=True)
        y_to = gr.Dropdown(YEARS, value=YEARS[-1], label="to", elem_classes="yr", scale=0, min_width=90, container=True)
        seasons = gr.CheckboxGroup(SEASONS, value=SEASONS, label="SEASON", elem_classes="cg", scale=0, min_width=1)
        risks = gr.CheckboxGroup(RISKS, value=RISKS, label="RISK LEVEL", elem_classes="cg", scale=0, min_width=1)
        reset = gr.Button("Reset filters", elem_classes="reset", scale=0, min_width=110)

    with gr.Tabs(elem_classes="tabswrap"):
        # ================= PAGE 1 : overview =================
        with gr.Tab("1 · Overview") as tab1:
            kpis = gr.HTML(elem_classes="kpiwrap")
            with gr.Row(equal_height=True, elem_classes=["tabrow", "row1"]):
                with gr.Column(scale=16, elem_classes="panel"):
                    with gr.Row(elem_classes="headrow"):
                        with gr.Column(scale=1):
                            sec("Trend over time", "Each dot is coloured by that month's risk level. Dashed line = 95% national target.")
                        metric = gr.Dropdown(list(TREND_METRICS), value="Attendances", label="Metric", elem_classes="dd", scale=0, container=True)
                    trend = gr.Plot(show_label=False, container=False, elem_classes="fit1")
                with gr.Column(scale=10, elem_classes="panel"):
                    sec("Which season is riskiest", "Number of months at each risk level, by season, in the current view.")
                    season = gr.Plot(show_label=False, container=False, elem_classes="fit1")

        # ================= PAGE 2 : drivers + explorer =================
        with gr.Tab("2 · Drivers & Explorer"):
            with gr.Row(equal_height=True, elem_classes="tabrow"):
                with gr.Column(scale=10, elem_classes="panel"):
                    sec("What tends to move with risk", "Risk comes from this month's attendances vs the 3-year seasonal baseline. Bars show which other figures move with high risk.")
                    drivers = gr.Plot(show_label=False, container=False, elem_classes="fit2")
                with gr.Column(scale=16, elem_classes="panel"):
                    with gr.Row(elem_classes="headrow"):
                        with gr.Column(scale=1):
                            sec("Feature explorer", "Pick any two figures. Each dot is one month, coloured by risk level.")
                        x_dd = gr.Dropdown(list(EXPLORER), value="Total attendances", label="Horizontal axis", elem_classes="dd", scale=0, container=True)
                        y_dd = gr.Dropdown(list(EXPLORER), value="4-hour performance", label="Vertical axis", elem_classes="dd", scale=0, container=True)
                    explorer = gr.Plot(show_label=False, container=False, elem_classes="fit2")

        # ================= PAGE 3 : high-risk table + outlook =================
        with gr.Tab("3 · High-risk & Outlook") as tab3:
            with gr.Row(equal_height=True, elem_classes="tabrow"):
                with gr.Column(scale=10, elem_classes="panel"):
                    sec("High-risk months in view", "Every month flagged High risk, most recent first.")
                    table = gr.Dataframe(interactive=False, wrap=True, elem_classes="tbl")
                with gr.Column(scale=14, elem_classes="panel"):
                    with gr.Row(elem_classes="headrow"):
                        with gr.Column(scale=1):
                            sec("Next month outlook", "Dotted = what the model expected; solid = what actually happened.")
                        window = gr.Dropdown(list(FORECAST_WINDOWS), value="Last 24 months", label="Window", elem_classes="dd", scale=0, container=True)
                    forecast = gr.Plot(show_label=False, container=False, elem_classes="fit2")

    gr.HTML('<div class="footnote globalfoot"><b>Data:</b> NHS England Monthly A&amp;E Time Series, Open Government Licence.</div>', elem_classes="footwrap")

    # ---- wiring
    ins = [y_from, y_to, seasons, risks, metric, x_dd, y_dd]
    outs = [summary, kpis, trend, drivers, season, explorer, table]
    for c in ins:
        c.change(update_all, ins, outs, show_progress="hidden")
    tab1.select(update_all, ins, outs, show_progress="hidden")   # redraw Overview charts when the page is shown
    tab3.select(update_all, ins, outs, show_progress="hidden")   # redraw the table once its page is visible
    window.change(forecast_fig, window, forecast, show_progress="hidden")
    reset.click(lambda: (YEARS[0], YEARS[-1], SEASONS, RISKS), None, [y_from, y_to, seasons, risks])
    demo.load(update_all, ins, outs)
    demo.load(forecast_fig, window, forecast)
    demo.load(None, None, None, js=JS)

if __name__ == "__main__":
    demo.launch(css=CSS, theme=gr.themes.Base(primary_hue="blue"), footer_links=[])