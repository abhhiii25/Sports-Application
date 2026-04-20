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

            current_step = {
                "label": label,
                "content": match.group(2).strip(),
            }
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
                steps.append(
                    {
                        "label": "Action",
                        "content": format_tool_call(tool_call),
                    }
                )

        elif role == "tool":
            observation = normalize_message_content(message.get("content"))
            if observation:
                steps.append(
                    {
                        "label": "Observation",
                        "content": observation,
                    }
                )

    return steps


def collect_trace_sections(result):
    sections = []

    for task_output in getattr(result, "tasks_output", []) or []:
        trace_steps = extract_trace_steps(getattr(task_output, "raw", ""))

        if not trace_steps:
            trace_steps = extract_trace_from_messages(getattr(task_output, "messages", []))

        if trace_steps:
            sections.append(
                {
                    "agent": getattr(task_output, "agent", "Agent"),
                    "steps": trace_steps,
                }
            )

    if not sections:
        fallback_steps = extract_trace_steps(getattr(result, "raw", ""))
        if fallback_steps:
            sections.append({"agent": "Crew", "steps": fallback_steps})

    return sections


def render_trace_content(text):
    return escape(text).replace("\n", "<br>")


st.set_page_config(
    page_title="Sports Planning Assistant!",
    page_icon="🏆",
    layout="wide",
)

st.markdown(
    """
<style>
.main-title {
    font-size: 42px;
    font-weight: 700;
    color: #ffffff;
}

.subtitle {
    font-size: 18px;
    color: #bbbbbb;
    margin-bottom: 20px;
}

.trace-card {
    background-color: #020617;
    padding: 18px;
    border-radius: 12px;
    border: 1px dashed #334155;
    margin-top: 12px;
}

.trace-section + .trace-section {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid rgba(148, 163, 184, 0.18);
}

.trace-agent {
    color: #e2e8f0;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 10px;
}

.trace-step {
    color: #cbd5e1;
    line-height: 1.65;
    margin: 8px 0;
}

.success-box {
    background-color: #052e16;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #16a34a;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-title">🏆 Sports Planning Assistant</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle">AI-powered multi-agent system for sports analysis, planning & insights</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns([4, 1])

with col1:
    goal = st.text_input(
        "🎯 Enter your sports goal",
        placeholder="e.g. Analyze Lakers performance in NBA or create IPL strategy for CSK",
    )

with col2:
    show_trace = st.toggle("🧠 Show Reasoning")


if st.button("🚀 Generate Plan", use_container_width=True):
    if goal.strip() == "":
        st.warning("⚠️ Please enter a goal")
    else:
        progress = st.progress(0, text="Initializing agents...")

        for i in range(100):
            time.sleep(0.01)
            progress.progress(i + 1, text="Agents thinking... 🤖")

        try:
            with st.spinner("🔍 Agents analyzing sports data..."):
                result = crew.kickoff(inputs={"goal": goal})
                final_output = getattr(result, "raw", "")
                trace_sections = collect_trace_sections(result)

            st.markdown(
                '<div class="success-box">✅ Analysis Complete</div>',
                unsafe_allow_html=True,
            )

            st.markdown("## 📊 Sports Analysis")

            if "Final Answer:" in final_output:
                final_answer = final_output.split("Final Answer:")[-1].strip()
            else:
                final_answer = final_output.strip()

            st.markdown("### 🏁 Final Insights")
            with st.container():
                st.success(final_answer or final_output)

            if show_trace:
                st.markdown("## 🧠 Agent Thinking Process")

                if trace_sections:
                    trace_html = ['<div class="trace-card">']
                    for section in trace_sections:
                        trace_html.append('<div class="trace-section">')
                        trace_html.append(
                            f'<div class="trace-agent">{escape(section["agent"])}</div>'
                        )

                        for step in section["steps"]:
                            icon = TRACE_ICONS.get(step["label"], "•")
                            content = render_trace_content(step["content"])
                            trace_html.append(
                                f'<div class="trace-step">{icon} <strong>{step["label"]}:</strong> {content}</div>'
                            )

                        trace_html.append("</div>")

                    trace_html.append("</div>")
                    st.markdown("".join(trace_html), unsafe_allow_html=True)
                else:
                    st.info(
                        "Reasoning was enabled, but this run only returned the final answer without intermediate trace steps."
                    )

        except Exception as e:
            st.error("❌ Error occurred")
            st.code(str(e))