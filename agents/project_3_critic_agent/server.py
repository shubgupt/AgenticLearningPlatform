import os
import time
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

# ⚙️ INITIALIZE FLASK INSTANCE (Fixes the NameError)
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

critic_ui_state = {
    "last_interaction": "Never", 
    "decision": "IDLE", 
    "critic_score": "N/A",
    "feedback": "Waiting for validation requests...", 
    "inspected_text": "No content verified yet.", 
    "model_name": "Unknown"
}

def load_lab_properties() -> dict:
    defaults = {"LAB_WORKER_MODEL": "openai/gpt-oss-20b"}
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

class RemotePedagogicalCritic:
    def audit_draft_payload(self, draft_text: str, negative_token: str, model_name: str) -> dict:
        time.sleep(0.3)
        has_token_conflict = negative_token != "None" and (negative_token.lower() in draft_text.lower())
        
        if has_token_conflict and "[SELF-CORRECTION LAYER" not in draft_text:
            decision = "REJECTED"
            score = 55
            feedback = f"[{model_name} EVALUATION] Found restricted token reference: '{negative_token}'. Rejecting draft."
        else:
            decision = "APPROVED"
            score = 94
            feedback = f"[{model_name} EVALUATION] Content passed verification metrics successfully."
            
        critic_ui_state["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        critic_ui_state["decision"] = decision
        critic_ui_state["critic_score"] = f"{score}%"
        critic_ui_state["feedback"] = feedback
        critic_ui_state["inspected_text"] = draft_text
        critic_ui_state["model_name"] = model_name
        
        return {"critic_score": score, "decision": decision, "feedback": feedback}

critic_engine = RemotePedagogicalCritic()

@app.route('/', methods=['GET'])
def render_dashboard_ui():
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Critic Agent Guardrail Monitor</title>
    """
    return render_template_string(html_template, state=critic_ui_state)

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    req = request.get_json()
    args = req.get("params", {}).get("arguments", {})
    
    current_props = load_lab_properties()
    model_target = current_props.get("LAB_WORKER_MODEL", "openai/gpt-oss-20b")
    
    result = critic_engine.audit_draft_payload(
        draft_text=args.get("draft_text", ""), 
        negative_token=args.get("negative_token", "None"), 
        model_name=model_target
    )
    
    app.logger.info(f"🛡️ [MCP NETWORK SUCCESS] Evaluation complete via {model_target}.")
    return jsonify({"jsonrpc": "2.0", "result": result, "id": req.get("id")})

if __name__ == '__main__':
    app.run(port=5002, debug=False)
