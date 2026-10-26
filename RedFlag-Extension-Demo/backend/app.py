from flask import Flask, request, jsonify
from flask_cors import CORS
import re

from db import get_connection
import llm

app = Flask(__name__)
CORS(app)

RULES = [
    {
        "pattern": re.compile(r"the earth is flat", re.IGNORECASE),
        "label": "Known false claim",
        "reason": "Modern observations, satellite data, and centuries of measurement show that Earth is an oblate spheroid.",
        "flagtype": "redflag",
        "result": "false"
    },
    {
        "pattern": re.compile(r"vaccines? (?:contain|have) microchips?", re.IGNORECASE),
        "label": "Known false claim",
        "reason": "Authorized vaccine ingredient lists do not include tracking microchips.",
        "flagtype": "redflag",
        "result": "false"
    },
    {
        "pattern": re.compile(r"5g (?:causes|created|spreads?) (?:covid|coronavirus)", re.IGNORECASE),
        "label": "Known false claim",
        "reason": "Radio waves cannot create or transmit a biological virus.",
        "flagtype": "redflag",
        "result": "false"
    },
    {
        "pattern": re.compile(r"(?:drink|drinking) bleach (?:cures?|prevents?|treats?)", re.IGNORECASE),
        "label": "Dangerous false claim",
        "reason": "Swallowing bleach is poisonous and is not a medical treatment.",
        "flagtype": "redflag",
        "result": "false"
    },
    {
        "pattern": re.compile(r"the moon landing was (?:fake|faked|staged)", re.IGNORECASE),
        "label": "Known false claim",
        "reason": "Independent tracking, returned lunar material, imagery, and later observations corroborate the Apollo landings.",
        "flagtype": "redflag",
        "result": "false"
    },
    {
        "pattern": re.compile(r"doctors? (?:do not|don['’]t) want you to know", re.IGNORECASE),
        "label": "Manipulative wording",
        "reason": "This phrase discourages checking qualified medical sources and provides no evidence by itself.",
        "flagtype": "redflag",
        "result": "unable_to_verify"
    },
    {
        "pattern": re.compile(r"share (?:this )?before (?:it['’]s|(?:it|this)) (?:is|gets) deleted", re.IGNORECASE),
        "label": "Urgency tactic",
        "reason": "Pressure to share immediately is a common signal that a claim should be verified first.",
        "flagtype": "signal",
        "result": "unable_to_verify"
    },
    {
        "pattern": re.compile(r"(?:100%|completely) guaranteed", re.IGNORECASE),
        "label": "Absolute claim",
        "reason": "Absolute guarantees require unusually strong evidence. Check the original source and supporting data.",
        "flagtype": "signal",
        "result": "unable_to_verify"
    },
    {
        "pattern": re.compile(r"mainstream media (?:won['’]t|will not|doesn['’]t) tell you", re.IGNORECASE),
        "label": "Conspiracy framing",
        "reason": "This wording attacks possible sources without supplying evidence for the claim.",
        "flagtype": "signal",
        "result": "unable_to_verify"
    },
    {
        "pattern": re.compile(r"miracle (?:cure|treatment|solution)", re.IGNORECASE),
        "label": "Extraordinary claim",
        "reason": "Medical miracle claims need strong clinical evidence and confirmation from reliable health authorities.",
        "flagtype": "signal",
        "result": "unable_to_verify"
    },
    {
        "pattern": re.compile(r"(?:artifical intelligence| ai |data center|llm)", re.IGNORECASE),
        "label": "Controversial Topic",
        "reason": "LLMs (aslo referred to as Artifical Intelligence) is a very divisive topic with strong opinion on both sides.",
        "flagtype": "biasstar",
        "result": "unable_to_verify"
    }
]

@app.route("/")
def home():
    return "RedFlag backend is running!"

@app.route("/analyze",methods=["POST"])
def analyze():
    data = request.get_json()

    text = data.get("text", "")

    # save claims, but if database is not up let it still run
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO claims (claim, label, reason) VALUES (%s, %s, %s)",
            (text, "", ""),
        )
        conn.commit()
        conn.close()
    except Exception as error:
        print("Database write failed:", error)

    for rule in RULES:
        if rule["pattern"].search(text):
            return jsonify({
                "pattern": rule["pattern"].pattern,
                "flagged": True,
                "label": rule["label"],
                "reason": rule["reason"],
                "flagtype": rule["flagtype"],
                "result": rule["result"]
            })
    
    return jsonify({
        "flagged": False,
        "result": "unable_to_verify",
        "label": "No matching rule",
        "reason": "This did not match any of the current demo rules."
    })

# Standalone endpoint that makes a real call to ODU's LLM.
# Run curl -X POST http://127.0.0.1:5000/llm_test -H "Content-Type: application/json" -d '{"prompt":"Say hi"}'
# /analyze is still regex-only; wiring the LLM into it is a follow-up.
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