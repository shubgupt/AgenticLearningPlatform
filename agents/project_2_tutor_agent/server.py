import os
import time
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Config File Vector Parser
def load_lab_properties() -> dict:
    defaults = {
        "LAB_WORKER_MODEL": "openai/gpt-oss-20b",
        "LAB_BASE_URL": "http://10.0.10.51:8000/v1/",
        "LAB_API_KEY": "ollama"
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
            # Merge parsed lines on top of safe default properties matrix
            for k in defaults:
                if k in config:
                    defaults[k] = config[k]
    except Exception:
        return defaults
    return defaults

# Load the custom setup specifications right on app runtime initialization
lab_props = load_lab_properties()

tutor_ui_state = {
    "last_interaction": "Never", 
    "target_skill": "None", 
    "modality": "Concepts-First",
    "status": "IDLE", 
    "tutor_output": "No content compiled yet.", 
    "model_name": lab_props["LAB_WORKER_MODEL"]
}

class RemoteTutorAgent:
    def __init__(self, base_url: str, api_key: str):
        # Dynamically mount connection loops against your properties file layout
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def compile_lesson_draft(self, target_skill: str, is_remediation: bool, negative_token: str, modality: str, attempt: int, user_query: str, critic_feedback: str, model_name: str) -> dict:
        system_instruction = (
            f"You are an expert AI Tutor teaching the technical skill node: '{target_skill}'.\n"
            f"Current Presentation Style Modality: {modality}.\n"
        )
        
        if is_remediation:
            system_instruction += "CRITICAL SAFETY: The student lacks prerequisites. Do NOT use complex advanced math. Step back to an intuitive foundation analogy or simple visual breakdown.\n"
        else:
            system_instruction += "The student has cleared prerequisites. You may use formal equations, calculus notation, and advanced definitions where appropriate.\n"
            
        if negative_token != "None":
            system_instruction += f"STRICT SAFETY CONSTRAINT: You are absolutely FORBIDDEN from using or referencing the phrase/analogy: '{negative_token}'. Completely avoid it.\n"
            
        if attempt > 1 and critic_feedback:
            system_instruction += f"REWRITE ATTEMPT #{attempt}: Your previous draft was REJECTED by the quality supervisor for this violation: '{critic_feedback}'. Self-correct this immediately.\n"
        if modality == "Socratic Questioning":
            system_instruction += "CRITICAL: Do NOT give the solution away. Adopt the Socratic method. Break down the concept into micro-questions and ask the student to think about the next step.\n"
        elif modality == "Flipped Analogy":
            system_instruction += "CRITICAL: Start with a heavy, relatable real-world metaphor. Do not introduce raw definitions until the analogy is fully established.\n"
        elif modality == "Code-First":
            system_instruction += "CRITICAL: Frame your primary explanation around a clean, reproducible Python code block that models this physical system.\n"
        else:
            system_instruction += f"Current Presentation Style Modality: {modality}.\n"

        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.15
            )
            output = response.choices[0].message.content
            summary = f"Dynamically generated live response using local properties engine specification."
            
        except Exception as e:
            output = f"🚨 [LOCAL LABORATORY INFERENCE ERROR] Failed to hit model cluster endpoint: {str(e)}"
            summary = "Inference pass failed over the internal lab network transport layer."

        tutor_ui_state["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tutor_ui_state["target_skill"] = target_skill
        tutor_ui_state["modality"] = modality
        tutor_ui_state["status"] = f"ACTIVE - Live Config Cluster Pass (Turn {attempt})"
        tutor_ui_state["tutor_output"] = output
        
        return {"tutor_output": output, "plain_english_summary": summary}

# Initialize engine instance with dynamically extracted network configuration parameters
tutor_engine = RemoteTutorAgent(
    base_url=lab_props["LAB_BASE_URL"],
    api_key=lab_props["LAB_API_KEY"]
)

@app.route('/', methods=['GET'])
def render_dashboard_ui():
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Quantum Tutor Matrix</title>
        <meta http-equiv="refresh" content="2">
        <style>
            body { 
                background: #02050a; 
                color: #00f0ff; 
                font-family: 'Courier New', monospace; 
                padding: 40px; 
                background-image: linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px);
                background-size: 20px 20px;
            }
            .card { 
                background: rgba(10, 18, 36, 0.75); 
                padding: 35px; 
                border-radius: 16px; 
                border: 1px solid #00f0ff; 
                max-width: 900px; 
                margin: 0 auto; 
                box-shadow: 0 0 35px rgba(0, 240, 255, 0.2);
                backdrop-filter: blur(8px);
            }
            h1 { 
                color: #fff; 
                text-shadow: 0 0 10px #00f0ff, 0 0 20px #00f0ff; 
                margin-top:0;
                text-transform: uppercase;
                letter-spacing: 3px;
            }
            .status-pulse {
                display: inline-block;
                width: 12px;
                height: 12px;
                background-color: #39ff14;
                border-radius: 50%;
                box-shadow: 0 0 10px #39ff14;
                animation: pulse 1.5s infinite;
                margin-right: 8px;
            }
            @keyframes pulse {
                0% { transform: scale(0.9); opacity: 0.6; }
                50% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 20px #39ff14; }
                100% { transform: scale(0.9); opacity: 0.6; }
            }
            .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 25px 0; }
            .meta-item { 
                background: #060b14; 
                padding: 15px; 
                border-radius: 8px; 
                border: 1px solid rgba(0, 240, 255, 0.2); 
                font-size: 0.9em; 
            }
            .output-box { 
                background-color: #03060f; 
                border: 1px solid #ff007f; 
                padding: 25px; 
                border-radius: 10px; 
                color: #5af78e; 
                white-space: pre-wrap; 
                font-size: 1.1rem;
                box-shadow: inset 0 0 15px rgba(255, 0, 127, 0.1);
                line-height: 1.6;
            }
            .accent { color: #ff007f; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🚀 <span class="accent">Quantum</span> Tutor Node Engine</h1>
            <p><span class="status-pulse"></span> <strong>CORE ANCHOR RATING:</strong> {{ state.status }}</p>
            <div class="meta-grid">
                <div class="meta-item">🕒 <strong>HANDSHAKE TIMESTAMP:</strong> {{ state.last_interaction }}</div>
                <div class="meta-item">🤖 <strong>COMPUTATIONAL MODEL:</strong> <span class="accent">{{ state.model_name }}</span></div>
            </div>
            <h3>📡 Broadcasted Personalized Lesson Plan Payload:</h3>
            <div class="output-box">{{ state.tutor_output }}</div>
        </div>
    </body>
    </html>
    """
return render_template_string(html_template, state=tutor_ui_state)

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    req = request.get_json()
    args = req.get("params", {}).get("arguments", {})
    raw_question = args.get("user_query") or req.get("params", {}).get("user_query") or "Tell me a fun physics fact."
    app.logger.info(f"📡 [NETWORK DEBUG] Extracted user query string: '{raw_question}'")
    
    # Reload properties file data vectors on the fly for hot-swapping capacity
    current_props = load_lab_properties()
    
    result = tutor_engine.compile_lesson_draft(
        target_skill=args.get("target_skill"),
        is_remediation=args.get("is_remediation"),
        negative_token=args.get("negative_token"),
        modality=args.get("modality"),
        attempt=args.get("attempt_number", 1),
        user_query=args.get("user_query", "Explain context."),
        critic_feedback=args.get("critic_feedback", ""),
        model_name=current_props["LAB_WORKER_MODEL"]
    )
    
    app.logger.info(f"📡 [MCP NETWORK SUCCESS] Generated response from config-driven cluster.")
    return jsonify({"jsonrpc": "2.0", "result": result, "id": req.get("id")})

if __name__ == '__main__':
    app.run(port=5001, debug=False)
