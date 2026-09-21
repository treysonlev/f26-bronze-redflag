from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "RedFlag backend is running!"

@app.route("/analyze",methods=["POST"])
def analyze():
    data = request.get_json()

    claim = data.get("claim", "")

    return jsonify({
        "claim": claim,
        "flagged": True,
        "label": "Backend analysis",
        "reason": "This claim should be verified."
    })

if __name__ == "__main__":
    app.run(debug=True)