from flask import Flask, request, jsonify
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

RULES = [
    {
        "pattern": re.compile(r"the earth is flat", re.IGNORECASE),
        "label": "Known false claim",
        "reason": "Modern observations, satellite data, and centuries of measurement show that Earth is an oblate spheroid.",
        "flagtype": "redflag"
    },
    {
        "pattern": re.compile(r"vaccines? (?:contain|have) microchips?", re.IGNORECASE),
        "label": "Known false claim",
        "reason": "Authorized vaccine ingredient lists do not include tracking microchips.",
        "flagtype": "redflag"
    },
    {
        "pattern": re.compile(r"5g (?:causes|created|spreads?) (?:covid|coronavirus)", re.IGNORECASE),
        "label": "Known false claim",
        "reason": "Radio waves cannot create or transmit a biological virus.",
        "flagtype": "redflag"
    },
    {
        "pattern": re.compile(r"(?:drink|drinking) bleach (?:cures?|prevents?|treats?)", re.IGNORECASE),
        "label": "Dangerous false claim",
        "reason": "Swallowing bleach is poisonous and is not a medical treatment.",
        "flagtype": "redflag"
    },
    {
        "pattern": re.compile(r"the moon landing was (?:fake|faked|staged)", re.IGNORECASE),
        "label": "Known false claim",
        "reason": "Independent tracking, returned lunar material, imagery, and later observations corroborate the Apollo landings.",
        "flagtype": "redflag"
    },
    {
        "pattern": re.compile(r"doctors? (?:do not|don['’]t) want you to know", re.IGNORECASE),
        "label": "Manipulative wording",
        "reason": "This phrase discourages checking qualified medical sources and provides no evidence by itself.",
        "flagtype": "redflag"
    },
    {
        "pattern": re.compile(r"share (?:this )?before (?:it['’]s|(?:it|this)) (?:is|gets) deleted", re.IGNORECASE),
        "label": "Urgency tactic",
        "reason": "Pressure to share immediately is a common signal that a claim should be verified first.",
        "flagtype": "signal"
    },
    {
        "pattern": re.compile(r"(?:100%|completely) guaranteed", re.IGNORECASE),
        "label": "Absolute claim",
        "reason": "Absolute guarantees require unusually strong evidence. Check the original source and supporting data.",
        "flagtype": "signal"
    },
    {
        "pattern": re.compile(r"mainstream media (?:won['’]t|will not|doesn['’]t) tell you", re.IGNORECASE),
        "label": "Conspiracy framing",
        "reason": "This wording attacks possible sources without supplying evidence for the claim.",
        "flagtype": "signal"
    },
    {
        "pattern": re.compile(r"miracle (?:cure|treatment|solution)", re.IGNORECASE),
        "label": "Extraordinary claim",
        "reason": "Medical miracle claims need strong clinical evidence and confirmation from reliable health authorities.",
        "flagtype": "signal"
    },
    {
        "pattern": re.compile(r"(?:artifical intelligence| ai |data center|llm)", re.IGNORECASE),
        "label": "Controversial Topic",
        "reason": "LLMs (aslo referred to as Artifical Intelligence) is a very divisive topic with strong opinion on both sides.",
        "flagtype": "biasstar",
    }
]

@app.route("/")
def home():
    return "RedFlag backend is running!"

@app.route("/analyze",methods=["POST"])
def analyze():
    data = request.get_json()

    text = data.get("text", "")

    for rule in RULES:
        if rule["pattern"].search(text):
            return jsonify({
                "pattern": rule["pattern"].pattern,
                "flagged": True,
                "label": rule["label"],
                "reason": rule["reason"],
                "flagtype": rule["flagtype"]
            })
    
    return jsonify({
        "flagged": False,
    })

if __name__ == "__main__":
    app.run(debug=True)