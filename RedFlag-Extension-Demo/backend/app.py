from flask import Flask, request, jsonify
from flask_cors import CORS

from db import get_connection
import llm

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "RedFlag backend is running!"

@app.route("/analyze", methods=["POST"])
def analyze():
    """Send the passage to ODU's LLM and return its findings. No regex:
    the LLM decides what is suspicious and quotes the claim verbatim so the
    extension can highlight it."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "Request body must include a non-empty 'text' string."}), 400

    try:
        findings = llm.analyze_text(text)
    except Exception as error:
        # Missing .env, LLM down, unparseable reply: report it, keep serving.
        print("LLM analysis failed:", error)
        return jsonify({"error": f"LLM analysis failed: {error}"}), 502

    if not findings:
        return jsonify({
            "flagged": False,
            "result": "unable_to_verify",
            "label": "No suspicious claims",
            "reason": "The analysis found no claim in this passage worth flagging."
        })
    if len(findings) == 1:
        return jsonify(findings[0])
    return jsonify({"flagged": True, "findings": findings})

# Standalone endpoint that makes a real call to ODU's LLM.
# Run curl -X POST http://127.0.0.1:5000/llm_test -H "Content-Type: application/json" -d '{"prompt":"Say hi"}'
@app.route("/llm_test", methods=["POST"])
def llm_test():
    data = request.get_json(silent=True) or {}

    prompt = data.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "Request body must include a non-empty 'prompt' string."}), 400

    try:
        answer = llm.chat(
            prompt,
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 300),
        )
        return jsonify({"response": answer})
    except Exception as error:
        # Missing .env, network failure, LLM down: report it but keep the server running.
        return jsonify({"error": str(error)}), 502

# Simple call to check if the backend can reach the database.
# Run curl http://127.0.0.1:5000/db_check to test
@app.route("/db_check") 
def db_check():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        return jsonify({"db": "ok"})
    except Exception as error:
        return jsonify({"db": "unreachable", "error": str(error)}), 500

# Another simple call that will pull back claims once we actually insert them into the DB
# Currently returns nothing unless claims added
# Run curl http://127.0.0.1:5000/claims
@app.route("/claims")
def claims():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, claim, label, reason FROM claims ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()
        conn.close()
        return jsonify([
            {"id": r[0], "claim": r[1], "label": r[2], "reason": r[3]} for r in rows
        ])
    except Exception as error:
        return jsonify({"db": "unreachable", "error": str(error)}), 500


if __name__ == "__main__":
    app.run(debug=True)