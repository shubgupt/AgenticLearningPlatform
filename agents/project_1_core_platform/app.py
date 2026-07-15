import streamlit as st
import time
import requests
import os
from datetime import datetime
from streamlit.runtime.scriptrunner import add_script_run_ctx

import streamlit as st

# 🚀 INJECT ADVANCED CYBERPUNK HUD CUSTOM CSS
st.markdown("""
<style>
    /* Global Dashboard Canvas Background */
    .stApp {
        background: radial-gradient(circle at 50% 50%, #0a0f1d 0%, #040712 100%) !important;
        color: #00f0ff !important;
        font-family: 'Courier New', Courier, monospace !important;
    }
    
    /* Innovation Title Header */
    .cyber-title {
        font-size: 2.8rem !important;
        font-weight: 900;
        text-transform: uppercase;
        background: linear-gradient(45deg, #00f0ff, #ff007f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
        letter-spacing: 2px;
        margin-bottom: 20px;
        border-bottom: 2px dashed rgba(0, 240, 255, 0.2);
        padding-bottom: 10px;
    }
    
    /* Glassmorphism Control Cards */
    div[data-testid="stForm"] {
        background: rgba(16, 24, 48, 0.65) !important;
        border: 1px solid rgba(0, 240, 255, 0.3) !important;
        border-radius: 16px !important;
        box-shadow: 0 0 25px rgba(0, 240, 255, 0.15), inset 0 0 15px rgba(0, 240, 255, 0.05) !important;
        padding: 30px !important;
        backdrop-filter: blur(12px);
    }
    
    /* Interactive Glowing Form Controls */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #060b16 !important;
        border: 1px solid #1e3f66 !important;
        color: #5af78e !important;
        border-radius: 8px !important;
        font-family: monospace !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #ff007f !important;
        box-shadow: 0 0 12px rgba(255, 0, 127, 0.5) !important;
    }
    
    /* Quantum Sliders Modification */
    div[data-testid="stSlider"] {
        color: #00f0ff !important;
    }
    
    /* Kinetic Action Button */
    button[kind="primaryFormSubmit"] {
        background: linear-gradient(135deg, #ff007f 0%, #7b00ff 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: bold !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        box-shadow: 0 0 15px rgba(255, 0, 127, 0.4) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        border-radius: 8px !important;
    }
    button[kind="primaryFormSubmit"]:hover {
        transform: translateY(-2px) scale(1.01);
        box-shadow: 0 0 25px rgba(255, 0, 127, 0.8) !important;
    }
    
    /* Holographic Terminal Console Log Cards */
    .console-card {
        background: rgba(5, 8, 16, 0.85);
        border-left: 5px solid #00f0ff;
        padding: 15px;
        margin: 10px 0;
        border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
</style>
""", unsafe_allow_html=True)

# Replace your standard title with this gorgeous styled wrapper
st.markdown('<h1 class="cyber-title">🤖 Quantum Multi-Runtime Agent Cluster</h1>', unsafe_allow_html=True)


class MCPNetworkClient:
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url

    def call_remote_agent(self, tool_name: str, arguments: dict) -> dict:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": int(time.time())
        }
        try:
            # 🕒 UPGRADE THIS LINE: Change timeout from 5 to 30 to allow the LLM time to generate text
            response = requests.post(self.endpoint_url, json=payload, timeout=120)
            if response.status_code == 200:
                return response.json().get("result", {})
        except Exception as e:
            return {"error": True, "message": f"Connection failure: {str(e)}"}
        return {"error": True, "message": "Malformed remote protocol reply."}

# Safe File-Parser Configuration Loader
def load_lab_properties() -> dict:
    defaults = {
        "LAB_WORKER_MODEL": "openai/gpt-oss-20b",
        "TUTOR_SERVER_URL": "http://127.0.0.1:5001/mcp",
        "CRITIC_SERVER_URL": "http://127.0.0.1:5002/mcp",
        "SKILL_MASTERY_THRESHOLD": "0.80"
    }
    try:
        target_path = os.path.abspath("lab_config.properties")
        if os.path.exists(target_path):
            config = {}
            with open(target_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip()
            return config if config else defaults
    except Exception:
        return defaults
    return defaults

st.set_page_config(page_title="ADK 2.0 Config Cluster", layout="wide")
st.title("🎓 Production Multi-Runtime Agent Cluster")
st.caption("SupportVectors AI Lab — Configuration-Driven Orchestration Shell")

if "trace_logs" not in st.session_state: st.session_state.trace_logs = []
if "last_results" not in st.session_state: st.session_state.last_results = None

# Dynamically source configuration vectors
lab_props = load_lab_properties()
TUTOR_SERVER_URL = lab_props.get("TUTOR_SERVER_URL")
CRITIC_SERVER_URL = lab_props.get("CRITIC_SERVER_URL")
mastery_gate = float(lab_props.get("SKILL_MASTERY_THRESHOLD", 0.80))

with st.sidebar:
    st.header("🔬 Infrastructure Status")
    st.text_input("Active Worker Model", value=lab_props.get("LAB_WORKER_MODEL"), disabled=True)
    st.text_input("Tutor Server Target Node", value=TUTOR_SERVER_URL, disabled=True)
    st.text_input("Critic Server Target Node", value=CRITIC_SERVER_URL, disabled=True)

panel, diagnostics = st.columns([3, 2])

with panel:
    st.subheader("Dynamic Multi-Agent Parameters")
    with st.form("agent_matrix_form"):
        form_skill = st.text_input("Target Skill Node Identifier:", value="sci.physics.kinematics.acceleration_vectors")
        form_mastery = st.slider("Simulated Student Mastery Score:", 0.0, 1.0, 0.45, step=0.05)
        form_threshold = st.slider("Required Prerequisite Gate:", 0.0, 1.0, mastery_gate, step=0.05)
        form_negative_token = st.text_input(
            "Strict Negative Constraint Token (Leave blank or type 'None' if none):", 
            value="None"
        )
        form_modality = st.selectbox( "Presentation Modality Style:", ["Concepts-First", "Examples-First", "Socratic Questioning", "Flipped Analogy", "Code-First", "Story-Based"])
        with st.expander("🎨 Student Personalization Profile (Optional)", expanded=False):
            fav_sport = st.text_input("Favorite Sport / Game:", value="Cricket")
            fav_player = st.text_input("Favorite Athlete / Player:", value="Virat Kohli")
            fav_character = st.text_input("Favorite Pop Culture Character:", value="Spider-Man")
            hobbies_input = st.text_input("Hobbies / Interests:", value="Gaming, Astrophysics")
            friends_input = st.text_input("Friends' Names (Comma separated):", value="Alex, Sam")
            student_age = st.number_input("Student Age:", min_value=5, max_value=100, value=17)
        user_prompt = st.text_area("Input active lesson query payload:", value="Can you use a pizza slices example to explain vector offsets?")
        submit_button = st.form_submit_button("Execute Automated Pipeline", type="primary")

    if submit_button and user_prompt:
        st.session_state.trace_logs = []
        def write_trace(text): st.session_state.trace_logs.append(text)
        import threading
        add_script_run_ctx(threading.current_thread())
       
        clean_negative_token = form_negative_token.strip() if form_negative_token.strip() else "None" 
        is_remediation = form_mastery < form_threshold
        tutor_client = MCPNetworkClient(TUTOR_SERVER_URL)
        critic_client = MCPNetworkClient(CRITIC_SERVER_URL)
        
        max_attempts = 3
        current_attempt = 1
        approved = False
        critic_feedback = ""
        
        write_trace("⚙️ [SUPERVISOR] Initializing config-driven multi-turn graph execution.")
        
        while current_attempt <= max_attempts and not approved:
            write_trace(f"🔄 [LOOP TURN {current_attempt}/{max_attempts}] Dispatching variables to Tutor Runtime...")
            tutor_response = tutor_client.call_remote_agent("compile_lesson_draft", {
                "target_skill": form_skill, "is_remediation": is_remediation, 
                "negative_token": clean_negative_token, "modality": form_modality,
                "critic_feedback": critic_feedback, 
                "attempt_number": current_attempt, 
                "user_query": user_prompt,
                "student_profile": {
                    "sport": fav_sport,
                    "player": fav_player,
                    "character": fav_character,
                    "hobbies": hobbies_input,
                    "friends": friends_input,
                    "age": student_age
                }
            })
            
            if tutor_response.get("error"):
                write_trace(f"🚨 [TUTOR ERROR] {tutor_response['message']}")
                st.error(tutor_response['message'])
                break
                
            write_trace("📥 [MCP INBOUND] Tutor Server returned content draft. Forwarding to Critic...")
            critic_response = critic_client.call_remote_agent("audit_draft_payload", {
                "draft_text": tutor_response["tutor_output"], "current_skill": form_skill, "negative_token": form_negative_token
            })
            
            if critic_response.get("error"):
                write_trace(f"🚨 [CRITIC ERROR] {critic_response['message']}")
                st.error(critic_response['message'])
                break
                
            write_trace(f"📋 [CRITIC ASSESSMENT] Score: {critic_response['critic_score']}% | Decision: {critic_response['decision']}")
            
            if critic_response["decision"] == "APPROVED":
                approved = True
                write_trace("✅ [GRAPH UNLOCKED] Critic passed content payload.")
                st.session_state.last_results = {
                    "tutor_output": tutor_response["tutor_output"],
                    "plain_english_summary": tutor_response["plain_english_summary"],
                    "score": critic_response["critic_score"],
                    "turns": current_attempt
                }
            else:
                write_trace("⚠️ [REJECTION TRIGGERED] Retrying and passing critique parameters down the pipe...")
                critic_feedback = critic_response["feedback"]
                current_attempt += 1
                time.sleep(0.5)

    if st.session_state.last_results:
        st.markdown(f"### 💬 Validated Lesson Output (Final Score: {st.session_state.last_results['score']}% over {st.session_state.last_results['turns']} turns)")
        if "Blocked" in st.session_state.last_results["tutor_output"] or "❌" in st.session_state.last_results["tutor_output"]:
            st.error(st.session_state.last_results["tutor_output"])
        else:
            st.info(st.session_state.last_results["tutor_output"])
        st.markdown("### 📝 Plain English Summary")
        st.markdown(f'<div style="background-color:#1E1E2F; padding:20px; border-radius:10px; border-left:5px solid #4CAF50;">{st.session_state.last_results["plain_english_summary"]}</div>', unsafe_allow_html=True)

with diagnostics:
    st.subheader("🕵️ MCP Network Interaction Console")
    with st.container(height=650, border=True):
        if st.session_state.trace_logs:
            for trace in st.session_state.trace_logs:
                if "🚨" in trace or "⚠️" in trace: st.error(trace)
                elif "🔌" in trace or "🔄" in trace: st.info(trace)
                elif "✅" in trace or "📋" in trace: st.success(trace)
                else: st.code(trace, language="bash")
