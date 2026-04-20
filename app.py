import json
import re
import time
from html import escape

import streamlit as st

from crew_setup import crew


TRACE_PATTERN = re.compile(
    r"^\s*(Thought|Action Input|Action|Observation)\s*:\s*(.*)$",
    re.IGNORECASE,
)
TRACE_ICONS = {
    "Thought": "🧠",
    "Action": "⚙️",
    "Action Input": "📥",
    "Observation": "👀",
}


def normalize_message_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content or "")


def format_tool_call(tool_call):
    function_data = tool_call.get("function", {}) if isinstance(tool_call, dict) else {}
    name = function_data.get("name") or tool_call.get("name") or "tool_call"
    arguments = function_data.get("arguments") or tool_call.get("input") or ""
    if isinstance(arguments, dict):
        args_text = json.dumps(arguments, ensure_ascii=False)
    else:
        args_text = str(arguments).strip()
        if args_text.startswith("{") and args_text.endswith("}"):
            try:
                args_text = json.dumps(json.loads(args_text), ensure_ascii=False)
            except json.JSONDecodeError:
                pass
    return f"{name}({args_text})" if args_text else name


def extract_trace_steps(text):
    steps = []
    current_step = None
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = TRACE_PATTERN.match(line)
        if match:
            label = match.group(1).strip().title()
            if label == "Action Input":
                label = "Action Input"
            current_step = {"label": label, "content": match.group(2).strip()}
            steps.append(current_step)
            continue
        if current_step:
            current_step["content"] = "\n".join(
                part for part in [current_step["content"], line] if part
            )
    return steps


def extract_trace_from_messages(messages):
    steps = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role == "assistant":
            content = normalize_message_content(message.get("content"))
            if content:
                steps.extend(extract_trace_steps(content))
            for tool_call in message.get("tool_calls", []):
                steps.append({"label": "Action", "content": format_tool_call(tool_call)})
        elif role == "tool":
            observation = normalize_message_content(message.get("content"))
            if observation:
                steps.append({"label": "Observation", "content": observation})
    return steps


def collect_trace_sections(result):
    sections = []
    for task_output in getattr(result, "tasks_output", []) or []:
        trace_steps = extract_trace_steps(getattr(task_output, "raw", ""))
        if not trace_steps:
            trace_steps = extract_trace_from_messages(getattr(task_output, "messages", []))
        if trace_steps:
            sections.append({"agent": getattr(task_output, "agent", "Agent"), "steps": trace_steps})
    if not sections:
        fallback_steps = extract_trace_steps(getattr(result, "raw", ""))
        if fallback_steps:
            sections.append({"agent": "Crew", "steps": fallback_steps})
    return sections


def render_trace_content(text):
    return escape(text).replace("\n", "<br>")


st.set_page_config(
    page_title="Sports Planning Assistant",
    page_icon="🏆",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
    --c1: #051F20;
    --c2: #0B2B26;
    --c3: #163832;
    --c4: #235347;
    --c5: #8EB69B;
    --c6: #DAF1DE;
}

*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
section.main > div { background: var(--c1) !important; }

[data-testid="stHeader"] { background: transparent !important; display: none; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

/* ── Animated background ── */
.bg-canvas {
    position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none;
}
.orb {
    position: absolute; border-radius: 50%;
    filter: blur(90px); opacity: 0.5;
    animation: orbFloat linear infinite;
}
.orb1 {
    width: 600px; height: 600px;
    background: radial-gradient(circle, var(--c4) 0%, transparent 70%);
    top: -150px; left: -150px; animation-duration: 20s;
}
.orb2 {
    width: 450px; height: 450px;
    background: radial-gradient(circle, var(--c5) 0%, transparent 70%);
    top: 35%; right: -120px; opacity: 0.3; animation-duration: 25s; animation-delay: -8s;
}
.orb3 {
    width: 350px; height: 350px;
    background: radial-gradient(circle, var(--c3) 0%, transparent 70%);
    bottom: -100px; left: 25%; animation-duration: 18s; animation-delay: -14s;
}
.orb4 {
    width: 220px; height: 220px;
    background: radial-gradient(circle, var(--c6) 0%, transparent 70%);
    top: 15%; left: 60%; opacity: 0.12; animation-duration: 30s; animation-delay: -5s;
}
@keyframes orbFloat {
    0%   { transform: translate(0,0) scale(1); }
    25%  { transform: translate(45px,35px) scale(1.07); }
    50%  { transform: translate(20px,-45px) scale(0.94); }
    75%  { transform: translate(-35px,22px) scale(1.05); }
    100% { transform: translate(0,0) scale(1); }
}

.grid-overlay {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
        linear-gradient(rgba(142,182,155,0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(142,182,155,0.045) 1px, transparent 1px);
    background-size: 54px 54px;
    animation: gridDrift 35s linear infinite;
}
@keyframes gridDrift {
    from { background-position: 0 0; }
    to   { background-position: 54px 54px; }
}

.particles { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
.particle {
    position: absolute; border-radius: 50%;
    background: var(--c5); opacity: 0;
    animation: particleRise linear infinite;
}
@keyframes particleRise {
    0%   { transform: translateY(100vh) translateX(0px); opacity: 0; }
    8%   { opacity: 0.55; }
    92%  { opacity: 0.3; }
    100% { transform: translateY(-8vh) translateX(50px); opacity: 0; }
}

/* ── All content above bg ── */
.block-container { position: relative; z-index: 1 !important; }
[data-testid="stVerticalBlock"] { position: relative; z-index: 1; }

/* ── Hero ── */
.hero {
    text-align: center; padding: 48px 0 36px;
    animation: heroIn 1s cubic-bezier(.22,1,.36,1) both;
}
@keyframes heroIn {
    from { opacity: 0; transform: translateY(36px); }
    to   { opacity: 1; transform: translateY(0); }
}
.hero-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(142,182,155,0.1);
    border: 1px solid rgba(142,182,155,0.28);
    border-radius: 100px; padding: 7px 22px;
    font-family: 'Outfit', sans-serif; font-size: 11px;
    font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--c5); margin-bottom: 26px;
    animation: badgePulse 3.5s ease-in-out infinite;
}
@keyframes badgePulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(142,182,155,0.25); }
    50%       { box-shadow: 0 0 0 10px rgba(142,182,155,0); }
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: clamp(68px, 10vw, 112px);
    line-height: 0.9; color: var(--c6);
    letter-spacing: 0.04em; margin-bottom: 14px;
    text-shadow: 0 0 80px rgba(218,241,222,0.1);
}
.hero-title .accent {
    color: var(--c5);
    animation: shimmer 4s ease-in-out infinite;
}
@keyframes shimmer {
    0%, 100% { text-shadow: 0 0 40px rgba(142,182,155,0.3); }
    50%       { text-shadow: 0 0 90px rgba(142,182,155,0.75), 0 0 140px rgba(142,182,155,0.3); }
}
.cursor {
    display: inline-block; width: 4px; height: 0.8em;
    background: var(--c5); margin-left: 6px;
    vertical-align: middle; border-radius: 2px;
    animation: cursorBlink 1.1s step-end infinite;
}
@keyframes cursorBlink { 0%,100%{opacity:1} 50%{opacity:0} }
.hero-sub {
    font-family: 'Outfit', sans-serif; font-size: 16px;
    font-weight: 300; color: rgba(218,241,222,0.38); letter-spacing: 0.02em;
}

/* ── Divider ── */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(142,182,155,0.28), transparent);
    margin: 28px 0; position: relative; overflow: visible;
}
.divider::after {
    content: ''; position: absolute; top: -1px; left: 0;
    width: 28%; height: 3px;
    background: linear-gradient(90deg, transparent, var(--c5), transparent);
    animation: scanLine 4.5s ease-in-out infinite;
}
@keyframes scanLine {
    0%   { left: -28%; }
    100% { left: 100%; }
}

/* ── Stats ── */
.stats-row {
    display: grid; grid-template-columns: repeat(4,1fr);
    gap: 14px; margin: 24px 0 32px;
    animation: fadeUp 0.8s 0.25s cubic-bezier(.22,1,.36,1) both;
}
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
.stat-chip {
    background: rgba(11,43,38,0.6);
    border: 1px solid rgba(142,182,155,0.1);
    border-radius: 18px; padding: 20px 14px;
    text-align: center; backdrop-filter: blur(10px);
    animation: chipGlow 4s ease-in-out infinite;
    transition: transform 0.3s;
}
.stat-chip:nth-child(1){animation-delay:0s}
.stat-chip:nth-child(2){animation-delay:1s}
.stat-chip:nth-child(3){animation-delay:2s}
.stat-chip:nth-child(4){animation-delay:3s}
@keyframes chipGlow {
    0%,100%{ border-color:rgba(142,182,155,0.1); box-shadow:none; }
    50%    { border-color:rgba(142,182,155,0.35); box-shadow:0 0 22px rgba(142,182,155,0.1); }
}
.stat-val {
    font-family:'Bebas Neue',sans-serif; font-size:34px;
    color:var(--c5); letter-spacing:0.04em; line-height:1;
}
.stat-lbl {
    font-family:'Outfit',sans-serif; font-size:10px;
    letter-spacing:0.14em; text-transform:uppercase;
    color:rgba(218,241,222,0.28); margin-top:5px;
}

/* ── Input card ── */
.input-card {
    background: rgba(11,43,38,0.55);
    border: 1px solid rgba(142,182,155,0.14);
    border-radius: 24px; padding: 32px 32px 28px;
    backdrop-filter: blur(18px);
    position: relative; overflow: hidden;
    animation: cardIn 0.8s 0.45s cubic-bezier(.22,1,.36,1) both;
}
@keyframes cardIn {
    from { opacity:0; transform:translateY(22px); }
    to   { opacity:1; transform:translateY(0); }
}
.input-card::before {
    content:''; position:absolute;
    top:0; left:-100%; width:300%; height:2px;
    background: linear-gradient(90deg, transparent, var(--c5), var(--c6), var(--c5), transparent);
    animation: borderSweep 4s linear infinite;
}
@keyframes borderSweep { from{left:-100%} to{left:100%} }
.input-card::after {
    content:''; position:absolute; inset:0; border-radius:24px;
    background: radial-gradient(ellipse 60% 40% at 50% 0%, rgba(142,182,155,0.07), transparent 70%);
    pointer-events:none;
}

.input-label {
    font-family:'Outfit',sans-serif; font-size:11px; font-weight:600;
    letter-spacing:0.16em; text-transform:uppercase;
    color:var(--c5); margin-bottom:12px;
    display:flex; align-items:center; gap:8px;
}
.dot {
    width:7px; height:7px; background:var(--c5);
    border-radius:50%; animation:dotBlink 1.6s ease-in-out infinite;
}
@keyframes dotBlink { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.25;transform:scale(0.55)} }

[data-testid="stTextInput"] input {
    background: rgba(5,31,32,0.85) !important;
    border: 1px solid rgba(142,182,155,0.2) !important;
    border-radius: 14px !important; color: var(--c6) !important;
    font-family: 'Outfit', sans-serif !important; font-size: 16px !important;
    padding: 16px 20px !important; caret-color: var(--c5) !important;
    transition: border-color 0.3s, box-shadow 0.3s !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: rgba(142,182,155,0.5) !important;
    box-shadow: 0 0 0 3px rgba(142,182,155,0.1), 0 0 28px rgba(142,182,155,0.08) !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder { color: rgba(218,241,222,0.2) !important; }
[data-testid="stTextInput"] label { display: none !important; }

[data-testid="stToggle"] {
    background: rgba(5,31,32,0.6) !important;
    border: 1px solid rgba(142,182,155,0.15) !important;
    border-radius: 100px !important; padding: 8px 18px !important;
}
[data-testid="stToggle"] label {
    color: rgba(218,241,222,0.6) !important;
    font-family: 'Outfit', sans-serif !important; font-size: 13px !important;
}

/* ── Button ── */
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, var(--c4) 0%, var(--c3) 55%, var(--c2) 100%) !important;
    border: 1px solid rgba(142,182,155,0.3) !important;
    border-radius: 16px !important; color: var(--c6) !important;
    font-family: 'Bebas Neue', sans-serif !important; font-size: 22px !important;
    letter-spacing: 0.14em !important; padding: 16px 32px !important;
    width: 100% !important;
    transition: transform 0.2s, filter 0.2s, box-shadow 0.2s !important;
    animation: btnPulse 3.2s ease-in-out infinite !important;
}
@keyframes btnPulse {
    0%,100%{ box-shadow: 0 4px 30px rgba(35,83,71,0.5), 0 0 0 0 rgba(142,182,155,0.25); }
    50%    { box-shadow: 0 8px 50px rgba(35,83,71,0.7), 0 0 0 8px rgba(142,182,155,0); }
}
[data-testid="stButton"] > button:hover {
    transform: translateY(-3px) !important;
    filter: brightness(1.18) !important;
    box-shadow: 0 14px 54px rgba(35,83,71,0.75), 0 0 44px rgba(142,182,155,0.18) !important;
}
[data-testid="stButton"] > button:active { transform: translateY(0) !important; }

/* ── Progress ── */
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--c4), var(--c5), var(--c6), var(--c5), var(--c4)) !important;
    background-size: 300% 100% !important;
    border-radius: 4px !important;
    animation: progressFlow 2s linear infinite !important;
}
@keyframes progressFlow {
    0%   { background-position: 100% 0; }
    100% { background-position: -200% 0; }
}
[data-testid="stProgress"] { background: rgba(142,182,155,0.08) !important; border-radius: 4px !important; }

/* ── Results ── */
.section-head {
    display:flex; align-items:center; gap:16px;
    margin: 36px 0 18px;
    animation: fadeUp 0.6s cubic-bezier(.22,1,.36,1) both;
}
.section-head-line {
    flex:1; height:1px;
    background: linear-gradient(90deg, rgba(142,182,155,0.3), transparent);
}
.section-head-title {
    font-family:'Bebas Neue',sans-serif; font-size:26px;
    color:var(--c5); letter-spacing:0.1em; white-space:nowrap;
}

.success-pill {
    display:inline-flex; align-items:center; gap:10px;
    background: rgba(22,56,50,0.7);
    border: 1px solid rgba(142,182,155,0.35);
    border-radius:100px; padding:10px 26px;
    font-family:'Outfit',sans-serif; font-size:13px;
    font-weight:600; color:var(--c5); margin-bottom:24px;
    letter-spacing:0.07em;
    animation: successAppear 0.5s cubic-bezier(.22,1,.36,1) both, successGlow 2s 0.5s ease-in-out infinite;
}
@keyframes successAppear { from{opacity:0;transform:scale(0.8)} to{opacity:1;transform:scale(1)} }
@keyframes successGlow {
    0%,100%{ box-shadow:0 0 0 0 rgba(142,182,155,0.3); }
    50%    { box-shadow:0 0 0 10px rgba(142,182,155,0); }
}

[data-testid="stAlert"] {
    background: rgba(11,43,38,0.65) !important;
    border: 1px solid rgba(142,182,155,0.18) !important;
    border-left: 3px solid var(--c5) !important;
    border-radius: 16px !important;
    color: rgba(218,241,222,0.88) !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 15px !important; line-height: 1.78 !important;
    backdrop-filter: blur(8px) !important;
    animation: alertSlide 0.5s cubic-bezier(.22,1,.36,1) both !important;
}
@keyframes alertSlide { from{opacity:0;transform:translateX(-14px)} to{opacity:1;transform:translateX(0)} }
[data-testid="stAlert"] svg { display:none !important; }
[data-testid="stAlert"][kind="warning"] { border-left-color:#b8b020 !important; color:rgba(230,225,130,0.9) !important; }
[data-testid="stAlert"][kind="error"]   { border-left-color:#a03535 !important; color:rgba(240,145,145,0.9) !important; }

/* ── Trace ── */
.trace-wrap { margin-top:32px; animation:fadeUp 0.6s 0.1s both; }
.trace-head {
    font-family:'Bebas Neue',sans-serif; font-size:22px;
    color:rgba(218,241,222,0.38); letter-spacing:0.14em;
    margin-bottom:16px; display:flex; align-items:center; gap:12px;
}
.trace-bar {
    width:4px; height:22px;
    background:linear-gradient(180deg, var(--c5), var(--c4));
    border-radius:2px; animation:barPulse 2.2s ease-in-out infinite;
}
@keyframes barPulse { 0%,100%{opacity:1} 50%{opacity:0.35} }

.trace-card {
    background: rgba(5,31,32,0.72);
    border: 1px dashed rgba(142,182,155,0.2);
    border-radius: 18px; padding: 24px; backdrop-filter: blur(10px);
}
.trace-section + .trace-section {
    margin-top:20px; padding-top:20px;
    border-top: 1px solid rgba(142,182,155,0.07);
}
.trace-agent {
    font-family:'Bebas Neue',sans-serif; font-size:14px;
    letter-spacing:0.14em; color:var(--c5);
    padding:6px 14px;
    background: rgba(35,83,71,0.35);
    border-radius:8px; display:inline-block;
    margin-bottom:14px;
    animation: agentSlide 0.4s cubic-bezier(.22,1,.36,1) both;
}
@keyframes agentSlide { from{opacity:0;transform:translateX(-10px)} to{opacity:1;transform:translateX(0)} }
.trace-step {
    font-family:'Outfit',sans-serif;
    color:rgba(218,241,222,0.55);
    line-height:1.72; margin:10px 0; font-size:14px;
    padding:10px 16px;
    background: rgba(11,43,38,0.45);
    border-radius:10px;
    border-left:2px solid rgba(142,182,155,0.22);
    animation: stepIn 0.4s cubic-bezier(.22,1,.36,1) both;
}
@keyframes stepIn { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:translateX(0)} }
.trace-step strong { color:rgba(218,241,222,0.9); font-weight:600; }

/* ── Spinner ── */
[data-testid="stSpinner"] { color:var(--c5) !important; }

/* ── Columns ── */
[data-testid="column"] { padding: 0 8px !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(142,182,155,0.2); border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:rgba(142,182,155,0.42); }
</style>

<!-- Animated BG layers -->
<div class="bg-canvas">
    <div class="orb orb1"></div>
    <div class="orb orb2"></div>
    <div class="orb orb3"></div>
    <div class="orb orb4"></div>
</div>
<div class="grid-overlay"></div>
<div class="particles" id="spa-particles"></div>

<script>
(function(){
    var p = document.getElementById('spa-particles');
    if (!p) return;
    for (var i = 0; i < 32; i++) {
        var d = document.createElement('div');
        d.className = 'particle';
        d.style.left = (Math.random() * 100) + 'vw';
        d.style.animationDuration = (9 + Math.random() * 16) + 's';
        d.style.animationDelay = (-Math.random() * 22) + 's';
        var sz = (1.5 + Math.random() * 3.5) + 'px';
        d.style.width = sz; d.style.height = sz;
        p.appendChild(d);
    }
})();
</script>
""", unsafe_allow_html=True)

# ── Hero ──
st.markdown("""
<div class="hero">
    <div class="hero-badge">🏆 &nbsp; Multi-Agent AI System</div>
    <div class="hero-title">
        Sports<br><span class="accent">Planning</span><br>Assistant<span class="cursor"></span>
    </div>
    <p class="hero-sub">AI-powered analysis, strategy &amp; performance insights for every sport</p>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)

# ── Stats ──
st.markdown("""
<div class="stats-row">
    <div class="stat-chip"><div class="stat-val">50+</div><div class="stat-lbl">Sports Covered</div></div>
    <div class="stat-chip"><div class="stat-val">AI</div><div class="stat-lbl">Multi-Agent</div></div>
    <div class="stat-chip"><div class="stat-val">Live</div><div class="stat-lbl">Data Analysis</div></div>
    <div class="stat-chip"><div class="stat-val">&#8734;</div><div class="stat-lbl">Goal Types</div></div>
</div>
""", unsafe_allow_html=True)

# ── Input ──
st.markdown('<div class="input-card">', unsafe_allow_html=True)
st.markdown('<div class="input-label"><span class="dot"></span> Your Sports Goal</div>', unsafe_allow_html=True)

col1, col2 = st.columns([5, 1])
with col1:
    goal = st.text_input(
        "goal_input",
        placeholder="e.g. Analyze Lakers performance in NBA or create IPL strategy for CSK",
        label_visibility="collapsed",
    )
with col2:
    show_trace = st.toggle("🧠 Reasoning", value=False)

st.markdown("</div>", unsafe_allow_html=True)

generate_clicked = st.button("🚀  GENERATE PLAN", use_container_width=True)

# ── Logic ──
if generate_clicked:
    if goal.strip() == "":
        st.warning("⚠️  Please enter a sports goal to continue.")
    else:
        progress = st.progress(0, text="Warming up agents…")
        for i in range(100):
            time.sleep(0.01)
            progress.progress(i + 1, text=f"Agents thinking… 🤖  ({i + 1}%)")

        try:
            with st.spinner("🔍  Agents are analyzing sports data…"):
                result = crew.kickoff(inputs={"goal": goal})
                final_output = getattr(result, "raw", "")
                trace_sections = collect_trace_sections(result)

            st.markdown('<div class="success-pill">✅ &nbsp; Analysis Complete</div>', unsafe_allow_html=True)

            st.markdown("""
            <div class="section-head">
                <div class="section-head-title">📊 Sports Analysis</div>
                <div class="section-head-line"></div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class="section-head">
                <div class="section-head-title">🏁 Final Insights</div>
                <div class="section-head-line"></div>
            </div>
            """, unsafe_allow_html=True)

            if "Final Answer:" in final_output:
                final_answer = final_output.split("Final Answer:")[-1].strip()
            else:
                final_answer = final_output.strip()

            st.success(final_answer or final_output)

            if show_trace:
                st.markdown('<div class="trace-wrap">', unsafe_allow_html=True)
                st.markdown(
                    '<div class="trace-head"><div class="trace-bar"></div>Agent Reasoning Process</div>',
                    unsafe_allow_html=True,
                )

                if trace_sections:
                    html_parts = ['<div class="trace-card">']
                    for section in trace_sections:
                        html_parts.append('<div class="trace-section">')
                        html_parts.append(f'<div class="trace-agent">&#9658; &nbsp;{escape(section["agent"])}</div>')
                        for step in section["steps"]:
                            icon = TRACE_ICONS.get(step["label"], "•")
                            content = render_trace_content(step["content"])
                            html_parts.append(
                                f'<div class="trace-step">{icon} &nbsp;<strong>{step["label"]}:</strong>&nbsp; {content}</div>'
                            )
                        html_parts.append("</div>")
                    html_parts.append("</div>")
                    st.markdown("".join(html_parts), unsafe_allow_html=True)
                else:
                    st.info(
                        "Reasoning was enabled, but this run only returned the final answer without intermediate trace steps."
                    )

                st.markdown("</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error("❌  An error occurred during analysis.")
            st.code(str(e))