from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib.parse import quote
import hashlib
import json
import re
import os
from difflib import SequenceMatcher
from functools import lru_cache
from dotenv import load_dotenv
import requests

from db import get_connection, init_db
import llm
load_dotenv()
app = Flask(__name__)
CORS(app)

# BiasStar stays hardcoded: a deterministic regex check (no LLM call) so the
# divisive-topic highlight is instant and identical on every scan.
BIASSTAR_RULES = [
    {
        "pattern": re.compile(r"(?:artifical intelligence|\bai\b|data center|llms?)", re.IGNORECASE),
        "label": "Controversial Topic",
        "reason": "LLMs (also referred to as Artificial Intelligence) are a divisive topic with strong opinions on both sides.",
        "flagtype": "biasstar",
    }
]

@app.route("/")
def home():
    return "RedFlag backend is running!"


def _normalize_for_hash(text):
    """Canonical form of analyzed text so trivially different whitespace
    still hits the claims cache."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _text_hash(text):
    return hashlib.sha256(_normalize_for_hash(text).encode("utf-8")).hexdigest()


def _cache_lookup(text):
    """Return previously persisted findings for this exact text, or None.
    A stored empty-claim row means the LLM previously cleared this text, so
    an empty list (not None) is returned and no LLM call is needed.
    Raises on DB errors so the caller can log and continue without cache."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT claim, label, reason, flagtype, sources FROM claims "
                "WHERE text_hash = %s ORDER BY id",
                (_text_hash(text),),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    if not rows:
        return None
    return [
        {
            "flagged": True,
            "claim": r[0],
            "label": r[1] or "Potential misinformation",
            "reason": r[2] or "The analysis service marked this claim for verification.",
            "flagtype": r[3] if r[3] in llm.SUPPORTED_FLAGTYPES else "redflag",
            "sources": r[4] if isinstance(r[4], list) else [],
        }
        for r in rows
        if r[0]  # empty claim = "analyzed, nothing flagged" marker row
    ]


def _persist_finding(text, finding):
    """Store one LLM-verified finding for caching. DB failures must never
    break the response, so callers wrap this in try/except."""
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO claims (claim, label, reason, text_hash, flagtype, sources) "
                "VALUES (%s, %s, %s, %s, %s, %s::jsonb)",
                (
                    finding.get("claim", ""),
                    finding.get("label", ""),
                    finding.get("reason", ""),
                    _text_hash(text),
                    finding.get("flagtype", "redflag"),
                    json.dumps(finding.get("sources", [])),
                ),
            )
    finally:
        conn.close()


def _analyze_response(findings):
    """Shape findings the way FRONTEND_INTEGRATION.md specifies."""
    if not findings:
        return jsonify({"flagged": False})
    findings = _add_sources(findings)
    if len(findings) == 1:
        return jsonify(findings[0])
    return jsonify({"findings": findings})


# Where a reader can verify a claim. Built deterministically from the claim
# text; used when the LLM cites no specific article that checks out.
SOURCE_SEARCHES = [
    ("Google", "https://www.google.com/search?q={q}+fact+check"),
    ("Reuters Fact Check", "https://www.reuters.com/site-search/?query={q}"),
    ("AP Fact Check", "https://apnews.com/search?q={q}"),
]

# LLMs often invent plausible URLs, so a cited article link is only trusted
# if it actually resolves. Results are memoized to avoid re-checking repeats.
_url_ok_cache = {}


def _url_resolves(url):
    if url in _url_ok_cache:
        return _url_ok_cache[url]
    try:
        resp = requests.head(url, allow_redirects=True, timeout=4,
                             headers={"User-Agent": "Mozilla/5.0"})
        # Some sites reject HEAD outright; try a small GET before giving up.
        if resp.status_code >= 400:
            resp = requests.get(url, allow_redirects=True, timeout=4,
                                headers={"User-Agent": "Mozilla/5.0"}, stream=True)
            resp.close()
        ok = resp.status_code < 400
    except requests.RequestException:
        ok = False
    _url_ok_cache[url] = ok
    return ok


def _search_sources(claim):
    query = quote(f'"{claim}"' if len(claim) <= 80 else claim)
    return [
        {"name": name, "url": template.format(q=query)}
        for name, template in SOURCE_SEARCHES
    ]

# Search published fact-check articles using Google's API.
# Cache results to avoid repeated calls for the same claim.
@lru_cache(maxsize=512)
def _google_fact_check_sources(claim):
    api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")

    if not api_key:
        return []

    try:
        response = requests.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params={
                "key": api_key,
                "query": claim[:300],
                "languageCode": "en",
                "pageSize": 10,
            },
            timeout=6,
        )

        response.raise_for_status()
        data = response.json()

    except (requests.RequestException, ValueError) as error:
        app.logger.warning(
            "Google Fact Check lookup failed: %s", error
        )
        return []

    sources = []
    seen_urls = set()

    for result in data.get("claims", []):
        reviewed_claim = result.get("text", "")

        if not reviewed_claim:
            continue

        # Basic relevance screening.
        # Similar wording does not guarantee identical meaning.
        similarity = SequenceMatcher(
            None,
            claim.lower().strip(),
            reviewed_claim.lower().strip()
        ).ratio()

        if similarity < 0.55:
            continue

        for review in result.get("claimReview", []):
            url = review.get("url", "")

            if (
                not isinstance(url, str)
                or not url.startswith("https://")
                or url in seen_urls
            ):
                continue

            seen_urls.add(url)

            publisher = review.get(
                "publisher", {}
            ).get("name", "Fact checker")

            rating = review.get(
                "textualRating", "Unrated"
            )

            sources.append({
                "name": f"Fact check: {publisher} ({rating})",
                "url": url,
                "reviewed_claim": reviewed_claim,
                "rating": rating,
            })

            if len(sources) == 3:
                return sources

    return sources


# Wikipedia has a free search API, so we can look up the actual article for a
# claim instead of trusting the LLM's memory. Results are memoized per claim.
_wiki_cache = {}

# Words too generic to prove an article is about the claim.
_WIKI_STOPWORDS = {
    "that", "this", "the", "with", "from", "have", "been", "were", "they",
    "their", "about", "into", "over", "after", "before", "said", "says",
    "claims", "claim", "told", "wrote", "posted", "post", "people",
    "readers", "followers", "account", "officials", "experts", "study",
}


def _wiki_relevant(claim, title, snippet):
    """Keep a Wikipedia hit when a distinctive claim word appears in the
    article title, or at least two appear (as whole words) in the snippet.
    This rejects vague matches like 'force majeure' hitting an unrelated
    war timeline while keeping e.g. 'vaccines...' -> a vaccine article."""
    import html as htmllib
    words = [w for w in re.findall(r"[a-z0-9']+", claim.lower())
             if len(w) > 3 and w not in _WIKI_STOPWORDS]
    if not words:
        return False
    title_l = title.lower()
    if any(w in title_l or w.rstrip("s") in title_l for w in words):
        return True
    text = htmllib.unescape(re.sub(r"<[^>]+>", " ", snippet)).lower()
    hits = sum(1 for w in words
               if re.search(r"\b(%s|%s)\b" % (re.escape(w), re.escape(w.rstrip("s"))), text))
    return hits >= 2


def _wikipedia_source(claim):
    if claim in _wiki_cache:
        return _wiki_cache[claim]
    source = None
    try:
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query", "list": "search", "format": "json",
                "srsearch": claim, "srlimit": 3,
            },
            timeout=4,
            headers={"User-Agent": "RedFlag-Extension/1.0"},
        )
        resp.raise_for_status()
        for hit in resp.json().get("query", {}).get("search", []):
            title = hit["title"]
            if _wiki_relevant(claim, title, hit.get("snippet", "")):
                source = {
                    "name": f"Wikipedia: {title}",
                    "url": "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_")),
                }
                break
    except (requests.RequestException, ValueError, KeyError):
        source = None
    _wiki_cache[claim] = source
    return source



def _add_sources(findings):
    """Find verification links for each RedFlag claim."""

    for finding in findings:

        # Only misinformation flags need fact-check links.
        if finding.get("flagtype") != "redflag":
            finding["sources"] = []
            continue

        claim = finding["claim"]

        # PRIORITY 1: Google Fact Check API
        google_sources = _google_fact_check_sources(claim)

        if google_sources:
            finding["sources"] = google_sources
            continue

        # PRIORITY 2: Existing LLM-provided links
        cited = [
            s for s in finding.get("sources", [])
            if isinstance(s, dict)
            and isinstance(s.get("url"), str)
            and s["url"].startswith(("https://", "http://"))
            and _url_resolves(s["url"])
        ]

        # PRIORITY 3: Wikipedia
        wiki = _wikipedia_source(claim)

        if wiki and not any(
            s["url"] == wiki["url"] for s in cited
        ):
            cited.append(wiki)

        # PRIORITY 4: Search links as a fallback
        finding["sources"] = (
            cited[:3] or _search_sources(claim)
        )

    return findings



# The frontend highlights only the first finding per passage, so the most
# important type must come first.
_FLAGTYPE_PRIORITY = {"redflag": 0, "biasstar": 1, "signal": 2}


def _sort_findings(findings):
    return sorted(findings, key=lambda f: _FLAGTYPE_PRIORITY.get(f["flagtype"], 3))


def _biasstar_findings(text):
    """Hardcoded regex BiasStar check; returns findings for divisive topics."""
    findings = []
    for rule in BIASSTAR_RULES:
        match = rule["pattern"].search(text)
        if match:
            findings.append({
                "flagged": True,
                "claim": match.group(0).strip(),
                "label": rule["label"],
                "reason": rule["reason"],
                "flagtype": rule["flagtype"],
            })
    return findings


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "Request body must include a non-empty 'text' string."}), 400

    # 1) BiasStar: hardcoded regex, always runs, no LLM needed.
    findings = _biasstar_findings(text)

    # 2) Cache: this exact text was already screened by the LLM, reuse it.
    try:
        cached = _cache_lookup(text)
    except Exception as error:
        print("Cache lookup failed:", error)
        cached = None
    if cached is not None:
        findings.extend(cached)
    else:
        # 3) The LLM screens the whole passage and decides what else to flag.
        try:
            findings.extend(llm.analyze_text(text))
        except Exception as error:
            print("LLM analysis failed:", error)
            if findings:
                # Regex BiasStar still has something to report even w/o LLM.
                return _analyze_response(_sort_findings(findings))
            return jsonify({"error": f"LLM analysis failed: {error}"}), 502

        # 4) Persist LLM results so repeat scans hit the cache. An empty
        # result is stored as a marker row (empty claim) so clean text isn't
        # re-analyzed either. BiasStar rows are not persisted: the regex is
        # deterministic and re-runs on every request.
        try:
            if cached is None:
                if findings:
                    for finding in findings:
                        if finding["flagtype"] != "biasstar":
                            _persist_finding(text, finding)
                else:
                    _persist_finding(text, {"claim": "", "label": "", "reason": "", "flagtype": ""})
        except Exception as error:
            print("Database write failed:", error)

    # Dedupe by claim (LLM may also report a BiasStar phrase) and order.
    unique = []
    seen = set()
    for finding in findings:
        key = finding["claim"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return _analyze_response(_sort_findings(unique))

# Standalone endpoint that makes a real call to ODU's LLM.
# Run curl -X POST http://127.0.0.1:5000/llm_test -H "Content-Type: application/json" -d '{"prompt":"Say hi"}'
# /analyze sends passages to the LLM itself; this endpoint is a raw connectivity test.
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
    # Best-effort schema upgrade; the server still runs without the database.
    try:
        init_db()
    except Exception as error:
        print("Database init skipped:", error)
    app.run(debug=True)