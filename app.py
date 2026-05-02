import json
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from main import (
    run_agents, validate_input, sanitize_input, regenerate_section,
    _get_serpapi_key, _MODEL_CHAIN, get_competitor_data,
    TONE_PROMPTS, LANGUAGES, EXAMPLE_PROMPTS, SECTIONS,
)
from pdf_generator import generate_pdf_bytes
from exporters import generate_txt_bytes, generate_docx_bytes
from auth import register_user, login_user, save_strategy, get_user_strategies, delete_strategy

st.set_page_config(page_title="AI Marketing Strategy Generator",
                   page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*,html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:radial-gradient(ellipse at top left,#1a0533 0%,#0d1b3e 40%,#0a0a1a 100%);min-height:100vh;}
.hero{text-align:center;padding:3.5rem 1rem 1.5rem;}
.hero h1{font-size:clamp(2rem,5vw,3.4rem);font-weight:900;
  background:linear-gradient(100deg,#c084fc,#818cf8,#38bdf8,#34d399);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.15;margin-bottom:.6rem;}
.hero .sub{color:#94a3b8;font-size:1.05rem;}.hero .sub strong{color:#c084fc;}
.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1.5rem 0;}
.stat-card{background:linear-gradient(135deg,rgba(124,58,237,.15),rgba(37,99,235,.1));
  border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:1.2rem;text-align:center;transition:transform .2s,border-color .2s;}
.stat-card:hover{transform:translateY(-3px);border-color:rgba(192,132,252,.4);}
.stat-card .val{font-size:1.9rem;font-weight:800;color:#c084fc;}
.stat-card .lbl{font-size:.78rem;color:#64748b;margin-top:4px;letter-spacing:.04em;text-transform:uppercase;}
.input-wrap{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);
  border-radius:18px;padding:2rem 2rem 1.5rem;backdrop-filter:blur(12px);margin-bottom:1.5rem;}
.input-label{color:#e2e8f0;font-size:1rem;font-weight:600;margin-bottom:.6rem;}
.stTextArea textarea{background:rgba(255,255,255,.07)!important;border:1px solid rgba(255,255,255,.12)!important;
  border-radius:10px!important;color:#f1f5f9!important;font-size:.97rem!important;}
.stTextArea textarea:focus{border-color:rgba(192,132,252,.6)!important;box-shadow:0 0 0 3px rgba(192,132,252,.12)!important;}
.stButton>button{background:linear-gradient(90deg,#7c3aed,#2563eb)!important;color:#fff!important;
  border:none!important;border-radius:10px!important;padding:.65rem 2rem!important;
  font-size:.97rem!important;font-weight:700!important;width:100%!important;transition:opacity .2s,transform .15s!important;}
.stButton>button:hover{opacity:.85!important;transform:translateY(-1px)!important;}
.stDownloadButton>button{background:linear-gradient(90deg,#059669,#0891b2)!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-weight:700!important;width:100%!important;padding:.65rem 2rem!important;}
.s-card{border-left:3px solid;border-radius:12px;padding:1.2rem 1.5rem 1rem;margin-bottom:1rem;transition:transform .18s;}
.s-card:hover{transform:translateX(5px);}
.s-badge{display:inline-block;padding:2px 11px;border-radius:999px;font-size:.7rem;font-weight:700;
  letter-spacing:.06em;text-transform:uppercase;margin-bottom:.6rem;}
.s-body{color:#cbd5e1;font-size:.91rem;line-height:1.9;}
.s-body-line{margin-bottom:.38rem;display:block;}
.s-body-bullet{margin-bottom:.38rem;display:block;padding-left:.2rem;}
.auth-wrap{max-width:440px;margin:0 auto;background:rgba(255,255,255,.04);
  border:1px solid rgba(255,255,255,.09);border-radius:18px;padding:2rem;backdrop-filter:blur(12px);}
.stProgress>div>div{background:linear-gradient(90deg,#7c3aed,#38bdf8)!important;border-radius:4px!important;}
hr{border-color:rgba(255,255,255,.07)!important;}
::-webkit-scrollbar{width:5px;}::-webkit-scrollbar-thumb{background:#4c1d95;border-radius:3px;}
section[data-testid="stSidebar"]{background:rgba(15,12,41,.95)!important;}
</style>""", unsafe_allow_html=True)

SECTION_META = {
    "Market Analysis":    ("📊", "#60a5fa", "rgba(30,58,95,0.5)"),
    "STP Model":          ("🎯", "#c084fc", "rgba(59,31,110,0.5)"),
    "Value Proposition":  ("💡", "#fbbf24", "rgba(74,48,0,0.5)"),
    "4Ps Strategy":       ("🔄", "#34d399", "rgba(6,78,59,0.5)"),
    "Marketing Channels": ("📡", "#f472b6", "rgba(80,7,36,0.5)"),
    "Content Strategy":   ("✍️",  "#fb923c", "rgba(67,20,7,0.5)"),
    "Budget Plan":        ("💰", "#4ade80", "rgba(5,46,22,0.5)"),
    "Execution Plan":     ("🗓️",  "#38bdf8", "rgba(12,42,62,0.5)"),
    "Expected Results":   ("📈", "#e879f9", "rgba(59,7,100,0.5)"),
}

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("user", None), ("history", []), ("current_result", None),
              ("current_product", ""), ("checklist", {}),
              ("tone", "Professional"), ("language", "English")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not st.session_state.user:
    st.markdown("""
    <div style="text-align:center;padding:3rem 1rem 1.5rem;">
      <div style="font-size:3.5rem;">🚀</div>
      <h2 style="color:#e2e8f0;font-weight:800;margin:.5rem 0 .3rem;">Marketing Strategy AI</h2>
      <p style="color:#64748b;font-size:.95rem;">Sign in to generate &amp; save your strategies</p>
    </div>""", unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
        tab_in, tab_reg = st.tabs(["🔑 Sign In", "📝 Create Account"])

        with tab_in:
            uid = st.text_input("Username or Email", key="li_id", placeholder="your@email.com")
            upw = st.text_input("Password", type="password", key="li_pw", placeholder="••••••••")
            if st.button("Sign In", key="btn_login", use_container_width=True):
                if not uid or not upw:
                    st.warning("Please fill in all fields.")
                else:
                    ok, msg, user_data = login_user(uid, upw)
                    if ok:
                        st.session_state.user = user_data
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_reg:
            ru  = st.text_input("Username",         key="rg_u",  placeholder="yourname")
            re_ = st.text_input("Email",             key="rg_e",  placeholder="your@email.com")
            rp  = st.text_input("Password",          key="rg_p",  type="password", placeholder="Min 6 characters")
            rp2 = st.text_input("Confirm Password",  key="rg_p2", type="password", placeholder="Repeat password")
            if st.button("Create Account", key="btn_reg", use_container_width=True):
                if not all([ru, re_, rp, rp2]):
                    st.warning("Please fill in all fields.")
                elif rp != rp2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = register_user(ru, re_, rp)
                    if ok:
                        st.success(msg + " Please sign in.")
                    else:
                        st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

user = st.session_state.user

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👋 {user['username']}")
    if st.button("🚪 Sign Out", use_container_width=True):
        for k in ["user","current_result","current_product","checklist","history"]:
            st.session_state[k] = None if k in ("user","current_result","current_product") else []
        st.rerun()
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    industry = st.selectbox("Industry", ["Auto-detect","E-commerce","EdTech","HealthTech","SaaS",
                                          "Food & Beverage","Fashion","Finance","Travel","Other"])
    budget_range = st.select_slider("Monthly Budget",
        options=["< $100","$100–300","$300–500","$500–1000","$1000+"], value="$100–300")
    st.session_state.tone = st.selectbox("Tone", list(TONE_PROMPTS.keys()),
        index=list(TONE_PROMPTS.keys()).index(st.session_state.tone))
    st.session_state.language = st.selectbox("Language", list(LANGUAGES.keys()),
        index=list(LANGUAGES.keys()).index(st.session_state.language))
    st.markdown("---")
    st.markdown("### 🕓 My Saved Strategies")
    saved = get_user_strategies(user["id"])
    if saved:
        for entry in saved[:5]:
            label = entry["product"][:38] + ("…" if len(entry["product"]) > 38 else "")
            c1, c2 = st.columns([5, 1])
            if c1.button(f"📄 {label}", key=f"sv_{entry['id']}"):
                st.session_state.current_result  = json.loads(entry["result"])
                st.session_state.current_product = entry["product"]
                st.session_state.tone     = entry.get("tone", "Professional")
                st.session_state.language = entry.get("language", "English")
            if c2.button("🗑", key=f"del_{entry['id']}"):
                delete_strategy(entry["id"], user["id"])
                st.rerun()
    else:
        st.caption("No saved strategies yet.")
    st.markdown("---")
    if _get_serpapi_key():
        st.success("🌐 Real market data: ON", icon="✅")
    else:
        st.info("🌐 Real market data: OFF", icon="ℹ️")

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🚀 AI Marketing Strategy Generator</h1>
  <p class="sub">Powered by <strong>Groq + LLaMA 3.1</strong> &nbsp;·&nbsp; Agentic AI &nbsp;·&nbsp; Built for startups & students</p>
</div>""", unsafe_allow_html=True)

st.markdown("""<div class="stat-grid">
  <div class="stat-card"><div class="val">9</div><div class="lbl">Strategy Sections</div></div>
  <div class="stat-card"><div class="val">STP+4Ps</div><div class="lbl">Frameworks</div></div>
  <div class="stat-card"><div class="val">&lt;30s</div><div class="lbl">Generation Time</div></div>
  <div class="stat-card"><div class="val">Free</div><div class="lbl">Cost</div></div>
</div>""", unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="input-wrap">', unsafe_allow_html=True)
st.markdown('<div class="input-label">💬 Describe your product or business idea</div>', unsafe_allow_html=True)
st.markdown("**Try an example:**")
ex_cols = st.columns(len(EXAMPLE_PROMPTS))
for i, ex in enumerate(EXAMPLE_PROMPTS):
    if ex_cols[i].button(f"💡 {ex[:26]}…", key=f"ex_{i}", use_container_width=True):
        st.session_state["_prefill"] = ex
prefill = st.session_state.pop("_prefill", "")
product = st.text_area("idea", label_visibility="collapsed", value=prefill,
    placeholder="e.g. An online tutoring app for school students in rural areas via WhatsApp...", height=100)
col_btn, col_tip = st.columns([2, 3])
with col_btn:
    generate = st.button("⚡ Generate My Marketing Strategy")
with col_tip:
    clr = "#34d399" if len(product) <= 1500 else "#f87171"
    st.markdown(f'<div style="color:{clr};font-size:.8rem;padding-top:.6rem;">'
                f'{len(product)}/1500 &nbsp;·&nbsp; Tone: <b style="color:#c084fc">{st.session_state.tone}</b>'
                f' &nbsp;·&nbsp; {st.session_state.language}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Generation ────────────────────────────────────────────────────────────────
if generate:
    err = validate_input(product)
    if err:
        st.warning(f"⚠️ {err}")
    else:
        cleaned, _ = sanitize_input(product.strip())
        enriched = cleaned
        if industry != "Auto-detect":
            enriched += f"\n\nIndustry: {industry}"
        enriched += f"\nMonthly marketing budget: {budget_range}"
        with st.spinner("⚡ Running 9 AI agents in parallel..."):
            result = run_agents(enriched, st.session_state.tone, st.session_state.language)
        st.session_state.current_result  = result
        st.session_state.current_product = product.strip()
        st.session_state.checklist       = {}
        save_strategy(user["id"], product.strip(), result,
                      st.session_state.tone, st.session_state.language)
        history = st.session_state.history
        if not history or history[-1]["product"] != product.strip():
            history.append({"product": product.strip(), "result": result})
            st.session_state.history = history[-5:]
        st.success("✅ Strategy generated and saved!")

# ── Render ────────────────────────────────────────────────────────────────────
result          = st.session_state.current_result
product_display = st.session_state.current_product

def _body_html(content):
    out = []
    for line in [l.strip() for l in content.split("\n") if l.strip()]:
        s = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        if line.startswith(("- ","• ","* ")):
            out.append(f'<span class="s-body-bullet">• {s[2:]}</span>')
        elif line.startswith(("**","__")):
            out.append(f'<span class="s-body-line"><strong>{s.replace("**","").replace("__","")}</strong></span>')
        else:
            out.append(f'<span class="s-body-line">{s}</span>')
    return "".join(out)

def render_card(section, content):
    icon, accent, bg = SECTION_META.get(section, ("📌","#94a3b8","rgba(30,41,59,0.5)"))
    st.markdown(f"""
    <div class="s-card" style="border-color:{accent};background:{bg};">
        <span class="s-badge" style="background:{accent}22;color:{accent};">{icon} {section}</span>
        <div class="s-body">{_body_html(content)}</div>
    </div>""", unsafe_allow_html=True)
    ca, cb = st.columns(2)
    ca.download_button("📋 Copy Text", data=content.encode(),
        file_name=f"{section.lower().replace(' ','_')}.txt",
        mime="text/plain", key=f"copy_{section}", use_container_width=True)
    if cb.button("🔄 Regenerate", key=f"regen_{section}", use_container_width=True):
        with st.spinner(f"Regenerating {section}..."):
            new = regenerate_section(product_display, section,
                                     st.session_state.tone, st.session_state.language)
        result[section] = new
        st.session_state.current_result = result
        st.rerun()

if result:
    st.markdown("---")
    st.markdown("### 📋 Your Complete Marketing Strategy")
    if product_display:
        st.caption(f"💼 {product_display[:120]}  ·  {st.session_state.tone}  ·  {st.session_state.language}")
    items = [(k,v) for k,v in result.items() if not k.startswith("_meta")]
    col_l, col_r = st.columns(2, gap="large")
    with col_l:
        for s, c in items[:5]: render_card(s, c)
    with col_r:
        for s, c in items[5:]: render_card(s, c)

    # ── Charts ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Analytics Dashboard")
    ch1, ch2, ch3 = st.columns(3, gap="large")
    with ch1:
        st.markdown("**📈 Projected Growth**")
        months = ["M1","M2","M3","M4","M5","M6"]
        fig, ax = plt.subplots(figsize=(5,4))
        fig.patch.set_facecolor("#0d1117"); ax.set_facecolor("#0d1117")
        for data, clr, lbl, mkr in [
            ([5,18,35,52,68,82],"#c084fc","Awareness","o"),
            ([2,8,18,30,45,60],"#60a5fa","Leads","s"),
            ([0,2,5,10,18,28],"#34d399","Conversions","^"),
        ]:
            ax.plot(months,data,marker=mkr,color=clr,linewidth=2.2,label=lbl,markersize=5)
            ax.fill_between(months,data,alpha=0.07,color=clr)
        ax.set_ylim(0,100); ax.yaxis.set_major_formatter(mticker.PercentFormatter())
        ax.tick_params(colors="#64748b",labelsize=8)
        for sp in ax.spines.values(): sp.set_visible(False)
        ax.grid(axis="y",linestyle="--",alpha=0.12,color="#94a3b8")
        ax.legend(facecolor="#0d1117",edgecolor="#1e293b",labelcolor="#94a3b8",fontsize=7)
        plt.tight_layout(); st.pyplot(fig); plt.close(fig)

    with ch2:
        st.markdown("**💰 Budget Allocation**")
        fig2, ax2 = plt.subplots(figsize=(5,4))
        fig2.patch.set_facecolor("#0d1117"); ax2.set_facecolor("#0d1117")
        _,_,ats = ax2.pie([35,25,20,12,8],
            labels=["Social Ads","Content","SEO/Tools","Email","Misc"],
            colors=["#c084fc","#60a5fa","#34d399","#fbbf24","#f472b6"],
            autopct="%1.0f%%",startangle=140,
            wedgeprops=dict(width=0.55,edgecolor="#0d1117",linewidth=2),
            textprops=dict(color="#94a3b8",fontsize=8))
        for at in ats: at.set_color("#fff"); at.set_fontsize(8)
        plt.tight_layout(); st.pyplot(fig2); plt.close(fig2)

    with ch3:
        st.markdown("**🎯 Competitor Radar**")
        with st.spinner("Analyzing..."): comp_data = get_competitor_data(product_display)
        dims        = comp_data.get("dimensions",["Price","Features","Reach","Brand","Support"])
        competitors = comp_data.get("competitors",[])
        your_scores = comp_data.get("your_scores",[5,5,5,5,5])
        your_name   = comp_data.get("your_product","Your Product")
        N = len(dims)
        angles = np.linspace(0,2*np.pi,N,endpoint=False).tolist()+[0]
        fig3, ax3 = plt.subplots(figsize=(5,4),subplot_kw=dict(polar=True))
        fig3.patch.set_facecolor("#0d1117"); ax3.set_facecolor("#0d1117")
        ax3.set_theta_offset(np.pi/2); ax3.set_theta_direction(-1)
        ax3.set_ylim(0,10); ax3.set_yticks([2,4,6,8,10])
        ax3.set_yticklabels(["2","4","6","8","10"],color="#475569",fontsize=6)
        ax3.set_xticks(angles[:-1]); ax3.set_xticklabels(dims,color="#94a3b8",fontsize=7)
        ax3.spines["polar"].set_color("#1e293b"); ax3.grid(color="#1e293b",linewidth=0.8)
        for i, comp in enumerate(competitors):
            c = ["#f472b6","#60a5fa","#fbbf24"][i%3]
            vals = comp["scores"]+comp["scores"][:1]
            ax3.plot(angles,vals,color=c,linewidth=1.6,label=comp["name"])
            ax3.fill(angles,vals,color=c,alpha=0.06)
        yv = your_scores+your_scores[:1]
        ax3.plot(angles,yv,color="#34d399",linewidth=2.4,linestyle="--",label=f"✦ {your_name}",zorder=5)
        ax3.fill(angles,yv,color="#34d399",alpha=0.12)
        ax3.legend(loc="upper right",bbox_to_anchor=(1.4,1.15),
                   facecolor="#0d1117",edgecolor="#1e293b",labelcolor="#e2e8f0",fontsize=7)
        plt.tight_layout(); st.pyplot(fig3); plt.close(fig3)

    your_avg = sum(your_scores)/len(your_scores)
    best_dim = dims[your_scores.index(max(your_scores))]
    weak_dim = dims[your_scores.index(min(your_scores))]
    sc1,sc2,sc3 = st.columns(3)
    for col,val,lbl,clr in [
        (sc1,f"{your_avg:.1f}/10","Overall Score","#c084fc"),
        (sc2,f"✅ {best_dim}","Strongest Area","#34d399"),
        (sc3,f"⚠️ {weak_dim}","Needs Improvement","#fbbf24"),
    ]:
        col.markdown(f'<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);'
                     f'border-radius:10px;padding:1rem;text-align:center;">'
                     f'<div style="font-size:1.1rem;font-weight:700;color:{clr};">{val}</div>'
                     f'<div style="font-size:.75rem;color:#64748b;margin-top:4px;text-transform:uppercase;'
                     f'letter-spacing:.05em;">{lbl}</div></div>', unsafe_allow_html=True)

    # ── Execution Checklist ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ✅ Execution Checklist")
    exec_tasks = [l.strip().lstrip("-•* ") for l in result.get("Execution Plan","").split("\n")
                  if l.strip() and len(l.strip()) > 10][:12]
    if exec_tasks:
        for i, task in enumerate(exec_tasks):
            key = f"chk_{i}"
            st.session_state.checklist[key] = st.checkbox(
                task, value=st.session_state.checklist.get(key, False), key=key)
        done_count = sum(st.session_state.checklist.values())
        st.progress(done_count/len(exec_tasks), text=f"{done_count}/{len(exec_tasks)} tasks completed")

    # ── Strategy Comparison ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ⚖️ Strategy Comparison")
    other_tones = [t for t in TONE_PROMPTS if t != st.session_state.tone]
    compare_tone = st.selectbox("Compare with tone:", other_tones, key="compare_tone")
    if st.button("🔀 Generate Comparison Strategy"):
        enriched2 = product_display
        if industry != "Auto-detect": enriched2 += f"\n\nIndustry: {industry}"
        enriched2 += f"\nMonthly marketing budget: {budget_range}"
        with st.spinner(f"Generating {compare_tone} version..."):
            st.session_state["compare_result"]      = run_agents(enriched2, compare_tone, st.session_state.language)
            st.session_state["compare_tone_label"]  = compare_tone
    if "compare_result" in st.session_state:
        r2    = st.session_state["compare_result"]
        tone2 = st.session_state.get("compare_tone_label","Alternative")
        cmp_sec = st.selectbox("Section to compare:", list(SECTIONS.keys()), key="cmp_sec")
        cc1, cc2 = st.columns(2, gap="large")
        with cc1:
            st.markdown(f"**{st.session_state.tone}**")
            render_card(cmp_sec, result.get(cmp_sec,""))
        with cc2:
            st.markdown(f"**{tone2}**")
            render_card(cmp_sec, r2.get(cmp_sec,""))

    # ── Export ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📥 Export Your Strategy")
    model_used    = result.get("_meta_model", _MODEL_CHAIN[0])
    has_real_data = bool(_get_serpapi_key())
    bm1, bm2 = st.columns(2)
    bm1.markdown(f'<div style="background:rgba(124,58,237,.15);border:1px solid rgba(124,58,237,.3);'
                 f'border-radius:8px;padding:.5rem 1rem;font-size:.82rem;color:#c084fc;">'
                 f'🤖 Model: <b>{model_used}</b></div>', unsafe_allow_html=True)
    bm2.markdown(f'<div style="background:{"rgba(5,150,105,.15)" if has_real_data else "rgba(100,116,139,.1)"};'
                 f'border:1px solid {"rgba(5,150,105,.3)" if has_real_data else "rgba(100,116,139,.2)"};'
                 f'border-radius:8px;padding:.5rem 1rem;font-size:.82rem;'
                 f'color:{"#34d399" if has_real_data else "#64748b"};">'
                 f'{"🌐 Real market data active" if has_real_data else "🌐 Add SERPAPI_KEY for real data"}'
                 f'</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        st.download_button("📄 Download PDF", data=generate_pdf_bytes(result, product_display[:60]),
            file_name="marketing_strategy.pdf", mime="application/pdf", use_container_width=True)
    with dl2:
        st.download_button("📝 Download Word", data=generate_docx_bytes(result, product_display[:60]),
            file_name="marketing_strategy.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True)
    with dl3:
        st.download_button("📋 Download Text", data=generate_txt_bytes(result, product_display[:60]),
            file_name="marketing_strategy.txt", mime="text/plain", use_container_width=True)

    st.markdown('<div style="text-align:center;color:#334155;font-size:.78rem;margin-top:1.5rem;">'
                'AI Marketing Strategy Generator &nbsp;·&nbsp; Groq + LLaMA 3.1 &nbsp;·&nbsp; Agentic AI'
                '</div>', unsafe_allow_html=True)
