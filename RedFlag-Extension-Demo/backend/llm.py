# Functions for calling llm endpoint, and setting up model
import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

# Make sure you've got your .env, and never ever commit it since it has
# a literal key for llm api.
load_dotenv()

# We can change the model at any time, qwen for now is pretty good.
DEFAULT_MODEL = os.getenv("LLM_MODEL", "qwen3-8-flash-next")


# Connect to the actual llm endpoint, it'll raise an error if it's not working
def get_client():
    api_url = os.getenv("LLM_API_URL")
    api_key = os.getenv("LLM_API_KEY")
    if not api_url or not api_key:
        raise RuntimeError(
            "LLM_API_URL/LLM_API_KEY not set, look at README"
        )
    return OpenAI(base_url=api_url, api_key=api_key)

# The system tells it what it's personality is.
# Temperature defines how creative the output is, 
# 0 is not creative 1 is very creative

# Max tokens defines how big the returned text can be,
# if you're running into issues with nothing coming back try
# increasing it

def chat(prompt, system="You exist", temperature=0.7, max_tokens=300):
    client = get_client() #connects to the endpoint
    response = client.chat.completions.create( #This is the actual prompt
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content #Returns response from prompt


# The contract /analyze relies on. The model must answer with one JSON object
# so the backend can turn it straight into the frontend response.
ANALYZE_SYSTEM_PROMPT = """You are RedFlag, a misinformation analyst. Examine the user's passage and return ONLY a JSON object, no prose and no markdown fences:

{"flagged": true or false, "findings": [{"claim": "...", "label": "...", "reason": "...", "flagtype": "redflag" | "biasstar" | "signal", "result": "true" | "false" | "unable_to_verify"}]}

Rules:
- "claim" MUST be a verbatim substring copied word-for-word from the passage (a phrase or one sentence, not the whole passage). It is used to highlight the text, so any paraphrase breaks it.
- "flagtype": "redflag" for a false or misleading factual claim; "biasstar" for loaded/controversial-topic wording; "signal" for softer warning signs (urgency to share, absolute guarantees, conspiracy framing, unverifiable specifics).
- "result": your verdict on the claim's truth: "true", "false", or "unable_to_verify".
- "label" is 2-5 words; "reason" is one or two plain-English sentences a reader can act on.
- Flag every distinct suspicious claim in the passage, including ones that only seem mildly dubious. If the passage contains no claim worth flagging, return {"flagged": false, "findings": []}.
- Escape every double quote inside string values as \\" so the JSON parses.
"""

SUPPORTED_FLAGTYPES = {"redflag", "biasstar", "signal"}
SUPPORTED_RESULTS = {"true", "false", "unable_to_verify"}


def _extract_json(text):
    """Pull the first JSON object out of a model reply, tolerating stray
    prose or ```json fences around it."""
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in model reply")
    return json.loads(match.group(0))


def _clean_finding(finding, source_text):
    """Normalise one LLM finding; drop it if the claim is not a verbatim
    substring (the frontend highlights by exact match)."""
    if not isinstance(finding, dict):
        return None
    claim = str(finding.get("claim", "")).strip()
    if not claim or claim not in source_text:
        return None
    flagtype = str(finding.get("flagtype", "redflag")).lower()
    result = str(finding.get("result", "unable_to_verify")).lower().strip()
    return {
        "flagged": True,
        "claim": claim,
        "label": str(finding.get("label", "Needs verification"))[:120],
        "reason": str(finding.get("reason", "The analysis service marked this claim for verification."))[:600],
        "flagtype": flagtype if flagtype in SUPPORTED_FLAGTYPES else "redflag",
        "result": result if result in SUPPORTED_RESULTS else "unable_to_verify",
    }


def analyze_text(text):
    """Send a passage to the LLM and return a list of cleaned findings.
    Raises on LLM/parse failure so /analyze can answer 502."""
    text = text[:4000]
    messages = [
        {"role": "system", "content": ANALYZE_SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    client = get_client()
    findings = None
    # qwen sometimes spends its budget on hidden reasoning (empty content) or
    # emits malformed JSON; one retry with a bigger budget + quoting reminder
    # fixes most cases.
    for attempt, (max_tokens, extra) in enumerate([(1200, ""), (2000, ' Remember: valid JSON only, escape every double quote inside strings as \\".')]):
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages + ([{"role": "user", "content": extra.strip()}] if extra else []),
            temperature=0,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            continue
        try:
            data = _extract_json(content)
        except (ValueError, json.JSONDecodeError):
            continue
        raw = data.get("findings")
        if raw is None and data.get("flagged"):
            raw = [data]  # Model returned a single finding object directly.
        if raw is None:
            raw = []
        if not isinstance(raw, list):
            continue
        findings = [f for f in (_clean_finding(item, text) for item in raw) if f]
        break
    if findings is None:
        raise ValueError("LLM did not return parseable JSON after retries")
    return findings
