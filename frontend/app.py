import streamlit as st
import requests
import json
import os
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ── Config ─────────────────────────────────────────────────────────────────────
# Reads API_BASE from environment — works locally AND on Render
API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")

st.set_page_config(
    page_title="Dark Pattern Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
* { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.5rem; max-width: 1200px; }
[data-testid="stSidebar"] { background: #0d0d1a; border-right: 1px solid #1e1e3a; }

.hero { background: linear-gradient(135deg, #0d0d1a, #1a1a2e, #0d1a2e); border-radius: 20px; padding: 36px; margin-bottom: 24px; border: 1px solid #1e1e3a; text-align: center; }
.hero h1 { font-size: 2.2rem; font-weight: 700; margin: 0; background: linear-gradient(135deg, #a78bfa, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero p { color: #888; font-size: 1rem; margin: 10px 0 0; }

.score-card { background: linear-gradient(135deg, #0d0d1a, #1a1a2e); border-radius: 16px; padding: 24px; border: 1px solid #1e1e3a; text-align: center; }
.score-number { font-size: 3.5rem; font-weight: 700; line-height: 1; margin: 8px 0; }
.score-label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.15em; color: #888; }
.score-verdict { font-size: 1rem; font-weight: 600; margin-top: 8px; }

.pattern-critical { border-left: 4px solid #e74c3c; background: #1a0a0a; border-radius: 8px; padding: 14px 18px; margin: 8px 0; }
.pattern-high     { border-left: 4px solid #e67e22; background: #1a120a; border-radius: 8px; padding: 14px 18px; margin: 8px 0; }
.pattern-medium   { border-left: 4px solid #f39c12; background: #1a1a0a; border-radius: 8px; padding: 14px 18px; margin: 8px 0; }
.pattern-low      { border-left: 4px solid #3498db; background: #0a0f1a; border-radius: 8px; padding: 14px 18px; margin: 8px 0; }

.pattern-title    { font-weight: 600; font-size: 0.95rem; color: #f0f0f0; margin-bottom: 6px; }
.pattern-evidence { font-size: 0.82rem; color: #aaa; font-family: 'JetBrains Mono', monospace; margin: 6px 0; background: #111; padding: 8px 10px; border-radius: 6px; }
.pattern-meta     { font-size: 0.75rem; color: #666; margin-top: 6px; }

.badge-critical { background:#c0392b; color:white; padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:600; }
.badge-high     { background:#e67e22; color:white; padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:600; }
.badge-medium   { background:#f39c12; color:#111;  padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:600; }
.badge-low      { background:#3498db; color:white; padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:600; }

.positive-tag { background:#0d2e1a; border:1px solid #1e5c35; color:#52c97a; padding:5px 12px; border-radius:20px; font-size:0.82rem; display:inline-block; margin:4px; }
.rec-item     { background:#0d1a2e; border:1px solid #1e3a5c; border-radius:8px; padding:10px 16px; margin:5px 0; color:#93c5fd; font-size:0.88rem; }
.metric-card  { background:#0d0d1a; border:1px solid #1e1e3a; border-radius:12px; padding:18px; text-align:center; }
.metric-value { font-size:1.8rem; font-weight:700; color:#a78bfa; }
.metric-label { font-size:0.75rem; color:#666; text-transform:uppercase; letter-spacing:0.1em; margin-top:4px; }
.info-box     { background:#0d0d1a; border:1px solid #1e1e3a; border-radius:12px; padding:16px; }

#MainMenu {visibility:hidden;} footer {visibility:hidden;} .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def score_color(s):
    if s >= 80: return "#52c97a"
    if s >= 60: return "#f39c12"
    if s >= 40: return "#e67e22"
    return "#e74c3c"

def score_verdict(s):
    if s >= 80: return "✅ SAFE"
    if s >= 60: return "⚠️ CAUTION"
    if s >= 40: return "🚨 SUSPICIOUS"
    return "🔴 DANGEROUS"

def render_pattern(p):
    sev  = p.get("severity", "Low").lower()
    name = p.get("pattern_name", "Unknown Pattern")
    ev   = p.get("evidence", "No evidence")
    loc  = p.get("location_hint", "Unknown")
    imp  = p.get("user_impact", p.get("description", ""))
    conf = int(float(p.get("confidence_score", 0)) * 100)
    ptype = p.get("pattern_type", "").replace("_", " ").title()
    st.markdown(f"""
    <div class="pattern-{sev}">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div class="pattern-title">{name}</div>
        <span class="badge-{sev}">{sev.upper()}</span>
      </div>
      <div class="pattern-evidence">📍 {ev}</div>
      {"<div class='pattern-evidence' style='background:#0d1a0d;color:#7ec87e;'>💡 " + imp + "</div>" if imp else ""}
      <div class="pattern-meta">🏷️ {ptype} &nbsp;|&nbsp; 📌 {loc} &nbsp;|&nbsp; 🎯 {conf}% confidence</div>
    </div>""", unsafe_allow_html=True)

def api_call(endpoint, method="GET", data=None, timeout=60):
    try:
        url = f"{API_BASE}{endpoint}"
        r = requests.post(url, json=data, timeout=timeout) if method == "POST" else requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "❌ Cannot connect to backend API. Make sure FastAPI is running on port 8000."
    except requests.exceptions.Timeout:
        return None, "⏱️ Request timed out. The website may be slow."
    except requests.exceptions.HTTPError as e:
        try:    detail = e.response.json().get("detail", str(e))
        except: detail = str(e)
        return None, f"❌ {detail}"
    except Exception as e:
        return None, f"❌ {str(e)}"

def render_result(result):
    """Render full analysis result — shared by URL and Text pages"""
    score    = float(result.get("credibility_score", 0))
    patterns = result.get("dark_patterns", [])
    color    = score_color(score)
    verdict  = score_verdict(score)

    # ── Top row ──────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1.6, 1])

    with c1:
        st.markdown(f"""
        <div class="score-card">
          <div class="score-label">Credibility Score</div>
          <div class="score-number" style="color:{color};">{int(score)}</div>
          <div style="color:#555;font-size:0.72rem;">out of 100</div>
          <div class="score-verdict" style="color:{color};">{verdict}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card" style="margin-bottom:8px;">
          <div class="metric-value" style="color:#f87171;">{result.get('total_patterns_found',0)}</div>
          <div class="metric-label">Dark Patterns Found</div>
        </div>""", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="info-box">
          <div style="font-size:0.75rem;color:#555;margin-bottom:6px;">PAGE INFO</div>
          <div style="color:#ccc;font-size:0.88rem;">🌐 {result.get('domain','N/A')}</div>
          <div style="color:#777;font-size:0.8rem;margin-top:4px;">🏷️ {str(result.get('industry_category','unknown')).title()}</div>
          <div style="color:#777;font-size:0.8rem;">⏱️ {result.get('analysis_duration_seconds',0)}s analysis</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        sev_counts = {}
        for p in patterns:
            s = p.get("severity","Low")
            sev_counts[s] = sev_counts.get(s,0) + 1
        for sev, emoji, col in [("Critical","🔴","e74c3c"),("High","🟠","e67e22"),("Medium","🟡","f39c12"),("Low","🔵","3498db")]:
            ct = sev_counts.get(sev,0)
            st.markdown(f"""
            <div style="background:#0d0d1a;border:1px solid #1e1e3a;border-radius:8px;padding:9px 14px;margin-bottom:5px;display:flex;justify-content:space-between;">
              <span style="color:#888;font-size:0.83rem;">{emoji} {sev}</span>
              <span style="font-weight:700;color:#{col};">{ct}</span>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # Summary
    summary = result.get("summary","")
    if summary:
        st.info(f"**AI Assessment:** {summary}")

    # Report download buttons
    aid = result.get("analysis_id")
    if aid:
        backend_base = API_BASE.replace("/api", "")
        ca, cb = st.columns(2)
        with ca:
            st.markdown(f'<a href="{backend_base}/api/reports/{aid}/pdf" target="_blank"><button style="width:100%;background:#6d28d9;color:white;border:none;padding:9px;border-radius:8px;cursor:pointer;font-size:0.88rem;">📄 Download PDF Report</button></a>', unsafe_allow_html=True)
        with cb:
            st.markdown(f'<a href="{backend_base}/api/reports/{aid}/json" target="_blank"><button style="width:100%;background:#1e1e3a;color:white;border:1px solid #3d3d6a;padding:9px;border-radius:8px;cursor:pointer;font-size:0.88rem;">📋 View JSON Report</button></a>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Dark patterns
    if patterns:
        st.markdown(f"### ⚠️ Detected Patterns ({len(patterns)})")
        for p in patterns:
            render_pattern(p)
    else:
        st.success("✅ **No dark patterns detected.** This website appears to follow ethical design practices.")

    # Positives
    positives = result.get("positive_practices", [])
    if positives:
        st.markdown("### ✅ Positive Practices")
        for pos in positives:
            st.markdown(f'<span class="positive-tag">✓ {pos}</span>', unsafe_allow_html=True)

    # Recommendations
    recs = result.get("recommendations", [])
    if recs:
        st.markdown("### 💡 Recommendations")
        for rec in recs:
            st.markdown(f'<div class="rec-item">→ {rec}</div>', unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:16px 0 20px;">
      <div style="font-size:2rem;">🔍</div>
      <div style="font-weight:700;font-size:1rem;color:#a78bfa;">Dark Pattern Detector</div>
      <div style="font-size:0.72rem;color:#555;margin-top:3px;">AI-powered manipulation analysis</div>
    </div>""", unsafe_allow_html=True)

    page = st.radio("Navigation", [
    "🔎 Analyze Website",
    "📝 Paste Content",
    "📊 Analytics"
], label_visibility="collapsed")

    st.divider()
    st.markdown("""
    <div style="font-size:0.76rem;color:#555;line-height:1.9;">
    <b style="color:#888;">Dark Pattern Types</b><br>
    🚨 Fake Urgency<br>💰 Hidden Costs<br>❓ Trick Questions<br>
    🪤 Roach Motel<br>👁️ Misdirection<br>🔄 Forced Continuity<br>
    ⭐ Fake Social Proof<br>😔 Confirm Shaming<br>
    📢 Disguised Ads<br>🔒 Privacy Zuckering
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Analyze Website
# ══════════════════════════════════════════════════════════════════════════════
if page == "🔎 Analyze Website":
    st.markdown("""
    <div class="hero">
      <h1>🔍 Dark Pattern Detector</h1>
      <p>Expose manipulative UI patterns hiding in plain sight. Enter any URL for an AI-powered analysis.</p>
    </div>""", unsafe_allow_html=True)

    with st.form("url_form"):
        c1, c2 = st.columns([4,1])
        with c1:
            url_input = st.text_input("URL", placeholder="https://www.irctc.co.in/nget/train-search", label_visibility="collapsed")
        with c2:
            submitted = st.form_submit_button("🔍 Analyze", use_container_width=True, type="primary")

    st.markdown("<div style='font-size:0.78rem;color:#555;margin-top:-6px;'>Try: irctc.co.in &nbsp;|&nbsp; makemytrip.com &nbsp;|&nbsp; books.toscrape.com (scraping-friendly)</div>", unsafe_allow_html=True)

    if submitted:
        if not url_input.strip():
            st.error("Please enter a URL.")
        else:
            with st.spinner("🤖 Scraping website and running Gemini AI analysis..."):
                result, error = api_call("/analyze/url", "POST", {"url": url_input.strip()})
            if error:
                st.error(error)
                st.info("💡 **Tip:** Many large sites block scrapers (403 error). Use the **Paste Content** tab instead — copy-paste the page text there.")
            elif result:
                render_result(result)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Paste Content
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📝 Paste Content":
    st.markdown("## 📝 Analyze Pasted Content")
    st.markdown("*Site blocking scraping? Paste the visible page text or HTML source directly.*")

    with st.form("text_form"):
        url_hint = st.text_input("Website URL (optional — for context)", placeholder="https://amazon.in/checkout")
        content  = st.text_area(
            "Paste content here",
            height=220,
            placeholder="Paste the website text or HTML source here...\n\nTip: Right-click any page → View Page Source → Ctrl+A → Ctrl+C → paste here.",
            label_visibility="collapsed"
        )
        sub2 = st.form_submit_button("🔍 Analyze Content", type="primary")

    # Show sample
    with st.expander("📋 Load sample dark pattern text to test"):
        st.code("""FLASH SALE - Only 2 items left in stock! Order in the next 00:09:43 or lose this deal!
Price: Rs.1299  (was Rs.4999)  74% OFF

1847 people are viewing this right now. Selling fast!

CHECKOUT SUMMARY:
Item total:       Rs.1,299
Convenience fee:  Rs.99
Packaging charge: Rs.49
Platform fee:     Rs.29
Total:            Rs.1,476

[✓] Yes, donate Rs.10 to Relief Fund
[✓] I agree to receive promotional SMS and emails

PROCEED TO PAY

No thanks, I don't want to save money  ← (tiny grey decline text)""", language="text")
        if st.button("Use This Sample"):
            st.session_state["sample_loaded"] = True

    if sub2:
        if len(content.strip()) < 30:
            st.error("Please paste at least 30 characters of content.")
        else:
            with st.spinner("🤖 Running Gemini AI analysis on pasted content..."):
                result, error = api_call("/analyze/text", "POST", {
                    "content": content,
                    "url": url_hint.strip() or "manual-input"
                })
            if error:
                st.error(error)
            elif result:
                render_result(result)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Pattern Database
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗄️ Pattern Database":
    st.markdown("## 🗄️ Community Pattern Database")
    st.markdown("*Search past analyses or report patterns you've spotted.*")

    tab1, tab2, tab3 = st.tabs(["🔍 Search Domain", "📝 Submit Report", "📋 All Reports"])

    with tab1:
        q = st.text_input("Search domain", placeholder="amazon.in, swiggy.com, irctc.co.in")
        if q:
            data, err = api_call(f"/patterns/search?domain={q.strip()}")
            if err:
                st.error(err)
            elif data:
                st.markdown(f"**Results for:** `{data.get('domain', q)}`")
                for a in data.get("ai_analyses", []):
                    sc = a.get("credibility_score", 0)
                    col = score_color(sc)
                    st.markdown(f"""<div style="background:#0d0d1a;border:1px solid #1e1e3a;border-radius:8px;padding:10px 16px;margin:5px 0;display:flex;justify-content:space-between;">
                    <span style="color:#a78bfa;font-weight:600;">Analysis #{a.get('id')}</span>
                    <span><span style="color:{col};font-weight:700;">{sc}/100</span>
                    <span style="color:#555;font-size:0.78rem;margin-left:10px;">{a.get('patterns_found',0)} patterns · {str(a.get('date',''))[:10]}</span></span>
                    </div>""", unsafe_allow_html=True)
                if not data.get("ai_analyses"):
                    st.info("No analyses found. Try analyzing this domain first.")
                for r in data.get("community_reports", []):
                    st.markdown(f"""<div style="background:#0d1a0d;border:1px solid #1e3a1e;border-radius:8px;padding:10px 16px;margin:5px 0;">
                    <b>{r.get('pattern_type','').replace('_',' ').title()}</b><br>
                    <span style="font-size:0.83rem;color:#aaa;">{r.get('description','')}</span><br>
                    <span style="font-size:0.75rem;color:#555;">{'⭐'*r.get('severity',1)} · 👍 {r.get('upvotes',0)}</span>
                    </div>""", unsafe_allow_html=True)

    with tab2:
        st.markdown("**Spotted a dark pattern? Report it to help others.**")
        with st.form("report_form"):
            r_url  = st.text_input("Website URL*", placeholder="https://example.com/checkout")
            r_type = st.selectbox("Pattern Type*", [
                "fake_urgency","hidden_costs","trick_questions","roach_motel",
                "misdirection","forced_continuity","social_proof_manipulation",
                "confirm_shaming","disguised_ads","privacy_zuckering"
            ])
            r_desc = st.text_area("Describe what you found*", placeholder="Exactly what did you see and where?")
            r_sev  = st.slider("Severity (1=Mild, 5=Severe)", 1, 5, 3)
            r_sub  = st.form_submit_button("Submit Report", type="primary")
        if r_sub:
            if not r_url or not r_desc:
                st.error("Please fill in URL and description.")
            else:
                res, err = api_call("/patterns/report", "POST", {
                    "url": r_url, "reported_pattern_type": r_type,
                    "description": r_desc, "severity_rating": r_sev
                })
                if err: st.error(err)
                else:   st.success("✅ Report submitted! Thank you for helping the community.")

    with tab3:
        data, err = api_call("/patterns/reports?limit=20")
        if err:
            st.error(err)
        elif data:
            if data:
                for r in data:
                    c1, c2 = st.columns([5,1])
                    with c1:
                        st.markdown(f"""<div style="background:#0d0d1a;border:1px solid #1e1e3a;border-radius:8px;padding:11px 16px;margin:5px 0;">
                        <b style="color:#a78bfa;">{r.get('domain','N/A')}</b>
                        <span style="background:#1e1e3a;color:#888;padding:2px 8px;border-radius:4px;font-size:0.73rem;margin-left:8px;">{r.get('pattern_type','').replace('_',' ').title()}</span><br>
                        <span style="font-size:0.83rem;color:#aaa;">{str(r.get('description',''))[:120]}...</span><br>
                        <span style="font-size:0.73rem;color:#555;">{'⭐'*r.get('severity_rating',1)} · 👍 {r.get('upvotes',0)}</span>
                        </div>""", unsafe_allow_html=True)
                    with c2:
                        if st.button("👍", key=f"up_{r['id']}"):
                            api_call(f"/patterns/upvote/{r['id']}", "POST")
                            st.rerun()
            else:
                st.info("No community reports yet. Be the first to report a dark pattern!")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Analytics
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Analytics":
    st.markdown("## 📊 Analytics Dashboard")

    data, err = api_call("/analytics/summary")
    if err:
        st.error(err)
    elif data:
        totals = data.get("totals", {})

        # Metrics row
        c1, c2, c3, c4 = st.columns(4)
        for col, (val, label, color) in zip(
            [c1,c2,c3,c4],
            [
                (totals.get("analyses",0),          "Total Analyses",    "#a78bfa"),
                (totals.get("patterns_detected",0),  "Patterns Found",    "#f87171"),
                (totals.get("unique_domains",0),      "Domains Checked",   "#60a5fa"),
                (f"{totals.get('avg_credibility_score',0)}/100", "Avg Safety Score", "#52c97a"),
            ]
        ):
            with col:
                st.markdown(f"""<div class="metric-card">
                <div class="metric-value" style="color:{color};">{val}</div>
                <div class="metric-label">{label}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        cl, cr = st.columns(2)

        # Pattern type bar chart
        with cl:
            pd_data = data.get("pattern_type_distribution", [])
            if pd_data:
                df = pd.DataFrame(pd_data)
                fig = px.bar(df, x="count", y="pattern_type", orientation="h",
                             title="Most Common Dark Patterns",
                             color="count", color_continuous_scale=["#1e1e3a","#6d28d9","#a78bfa"])
                fig.update_layout(plot_bgcolor="#0a0a0f", paper_bgcolor="#0a0a0f",
                                  font_color="#888", title_font_color="#ccc",
                                  showlegend=False, coloraxis_showscale=False,
                                  margin=dict(l=0,r=0,t=40,b=0))
                fig.update_xaxes(gridcolor="#1e1e3a")
                fig.update_yaxes(gridcolor="#1e1e3a")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Analyze some websites to see pattern distribution.")

        # Severity pie chart
        with cr:
            sv_data = data.get("severity_breakdown", [])
            if sv_data:
                df2 = pd.DataFrame(sv_data)
                cmap = {"Critical":"#e74c3c","High":"#e67e22","Medium":"#f39c12","Low":"#3498db"}
                fig2 = px.pie(df2, values="count", names="severity",
                              title="Pattern Severity Distribution",
                              color="severity", color_discrete_map=cmap, hole=0.5)
                fig2.update_layout(plot_bgcolor="#0a0a0f", paper_bgcolor="#0a0a0f",
                                   font_color="#888", title_font_color="#ccc",
                                   legend=dict(font=dict(color="#888")))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No severity data yet.")

        # Industry chart
        ind_data = data.get("industry_breakdown", [])
        if ind_data:
            df3 = pd.DataFrame(ind_data)
            fig3 = px.bar(df3, x="industry", y="count", title="Analyses by Industry",
                          color="count", color_continuous_scale=["#1e1e3a","#7c3aed","#c4b5fd"])
            fig3.update_layout(plot_bgcolor="#0a0a0f", paper_bgcolor="#0a0a0f",
                               font_color="#888", title_font_color="#ccc",
                               showlegend=False, coloraxis_showscale=False)
            fig3.update_xaxes(gridcolor="#1e1e3a")
            fig3.update_yaxes(gridcolor="#1e1e3a")
            st.plotly_chart(fig3, use_container_width=True)

    


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Worst Offenders
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏆 Worst Offenders":
    st.markdown("## 🏆 Worst Offenders Leaderboard")
    st.markdown("*Domains with the most detected dark patterns*")

    data, err = api_call("/patterns/leaderboard")
    if err:
        st.error(err)
    elif data:
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("### 🤖 AI-Detected Offenders")
            offenders = data.get("ai_detected_offenders", [])
            if offenders:
                for i, o in enumerate(offenders, 1):
                    sc  = o.get("avg_credibility_score")
                    col = score_color(sc) if sc else "#888"
                    medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"#{i}"
                    st.markdown(f"""<div style="background:#1a0a0a;border:1px solid #3a1a1a;border-radius:10px;padding:12px 16px;margin:7px 0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>{medal} <span style="color:#f0f0f0;font-weight:600;margin-left:6px;">{o.get('domain','N/A')}</span></div>
                    <div style="text-align:right;"><div style="color:#f87171;font-weight:700;">{o.get('patterns_detected',0)} patterns</div>
                    {f'<div style="color:{col};font-size:0.78rem;">Score: {sc}/100</div>' if sc else ''}</div>
                    </div></div>""", unsafe_allow_html=True)
            else:
                st.info("No data yet. Analyze some websites to populate the leaderboard!")

        with c2:
            st.markdown("### 👥 Community-Reported Offenders")
            community = data.get("community_reported_offenders", [])
            if community:
                for i, o in enumerate(community, 1):
                    medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"#{i}"
                    avg   = o.get("avg_severity_rating", 0)
                    stars = "⭐" * round(avg) if avg else ""
                    st.markdown(f"""<div style="background:#0d1a0d;border:1px solid #1a3a1a;border-radius:10px;padding:12px 16px;margin:7px 0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>{medal} <span style="color:#f0f0f0;font-weight:600;margin-left:6px;">{o.get('domain','N/A')}</span></div>
                    <div style="text-align:right;"><div style="color:#52c97a;font-weight:700;">{o.get('community_reports',0)} reports</div>
                    <div style="font-size:0.8rem;">{stars}</div></div>
                    </div></div>""", unsafe_allow_html=True)
            else:
                st.info("No community reports yet.")

        # Score distribution
        st.divider()
        st.markdown("### 📊 Overall Safety Distribution")
        dist_d, _ = api_call("/analytics/credibility-distribution")
        if dist_d:
            dist  = dist_d.get("distribution", {})
            total = dist_d.get("total", 1) or 1
            cols  = st.columns(4)
            for col, (label, key, color, emoji) in zip(cols, [
                ("Safe",       "safe",       "#52c97a", "✅"),
                ("Caution",    "caution",    "#f39c12", "⚠️"),
                ("Suspicious", "suspicious", "#e67e22", "🚨"),
                ("Dangerous",  "dangerous",  "#e74c3c", "🔴"),
            ]):
                count = dist.get(key, 0)
                pct   = round(count / total * 100, 1)
                with col:
                    st.markdown(f"""<div class="metric-card">
                    <div style="font-size:1.4rem;">{emoji}</div>
                    <div class="metric-value" style="color:{color};font-size:1.4rem;">{pct}%</div>
                    <div class="metric-label">{label}</div>
                    <div style="color:#444;font-size:0.73rem;">{count} sites</div>
                    </div>""", unsafe_allow_html=True)
        else:
            st.info("Analyze more websites to see the safety distribution.")
