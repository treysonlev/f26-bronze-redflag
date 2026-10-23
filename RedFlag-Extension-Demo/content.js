(() => {
  if (window.__redflagLoaded) return;
  window.__redflagLoaded = true;

  // Frontend only: the backend team is responsible for forwarding /analyze
  // requests to ODU's LLM endpoint. Never put an LLM API key here.
  const ANALYZE_URL = "http://127.0.0.1:5000/analyze";
  const MAX_TEXT_NODES_PER_SCAN = 50; // Bound LLM requests on large websites.
  const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA", "INPUT", "SELECT", "OPTION", "CODE", "PRE"]);
  const HIGHLIGHT_CLASSES = ".redflag-highlight, .biasstar-highlight, .signalwarning-highlight";

  let enabled = true;
  let findings = [];
  let scanTimer;
  let scanning = false;
  let observer;
  let scanStatus = "Not scanned yet.";
  let latestExchange = null;
  const responseCache = new Map();

  async function analyze(text) {
    // Reuse analysis for unchanged text (avoids repeated LLM requests on rescan).
    if (responseCache.has(text)) return responseCache.get(text);

    const response = await fetch(ANALYZE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    if (!response.ok) throw new Error(`Analysis endpoint returned HTTP ${response.status}`);

    const result = await response.json();

    console.log("RedFlag backend response:", result)
    responseCache.set(text, result);
    if (responseCache.size > 200) responseCache.delete(responseCache.keys().next().value);
    return result;
  }

  // Handle a normal Flask JSON response or an LLM response wrapped in
  // {response: ...}, {result: ...}, {analysis: ...}, or OpenAI-style choices.
  function parseLLMJSON(value) {
    if (typeof value !== "string") return value;
    const trimmed = value.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
    try { return JSON.parse(trimmed); } catch { return value; }
  }

  function unwrapAnalysis(value) {
    let result = parseLLMJSON(value);
    for (let i = 0; i < 4; i++) {
      if (!result || typeof result !== "object" || Array.isArray(result)) break;
      const wrapped = result.choices?.[0]?.message?.content
        ?? result.result ?? result.data ?? result.response
        ?? (typeof result.analysis === "object" ? result.analysis : null)
        ?? result.output;
      if (wrapped == null) break;
      const next = parseLLMJSON(wrapped);
      if (next && typeof next === "object") result = next;
      else break; // Plain-text LLM output is displayed, not treated as a flag.
    }
    return result;
  }

  function extractFindings(serverReply) {
    const data = unwrapAnalysis(serverReply);
    const items = Array.isArray(data) ? data
      : Array.isArray(data?.findings) ? data.findings
      : Array.isArray(data?.flags) ? data.flags
      : Array.isArray(data?.results) ? data.results
      : Array.isArray(data?.claims) ? data.claims
      : data && (data.flagged === true || data.is_misinformation === true) ? [data]
      : [];

    return items.filter(item => item && typeof item === "object" && item.flagged !== false)
      .map(item => ({
        claim: String(item.matched_text ?? item.claim ?? item.phrase ?? item.quote ?? ""),
        pattern: typeof item.pattern === "string" ? item.pattern : "",
        label: String(item.label ?? item.category ?? item.classification ?? "Needs verification"),
        reason: String(item.reason ?? item.explanation ?? item.rationale ?? item.details ??
          "The analysis service marked this claim for verification."),
        flagtype: normalizeFlagType(item.flagtype ?? item.flag_type ?? item.type),
        result: normalizeVerdict(item.result ?? item.verdict)
      }));
  }

  function normalizeFlagType(type) {
    const name = String(type ?? "redflag").toLowerCase();
    if (name === "biasstar" || name === "bias") return "biasstar";
    if (name === "signal" || name === "warning") return "signal";
    return "redflag";
  }

  function normalizeVerdict(value) {
    const verdict = String(value ?? "unable_to_verify").toLowerCase().trim();

    if (verdict === "true") return "true";
    if (verdict === "false") return "false";

    return "unable_to_verify";
  }

  function displayResponse(reply) {
    // Prefer the human-readable LLM response when present; show JSON otherwise.
    const humanText = reply?.choices?.[0]?.message?.content
      ?? (typeof reply?.response === "string" ? reply.response : null)
      ?? (typeof reply?.output === "string" ? reply.output : null);
    const text = typeof reply === "string" ? reply
      : humanText != null ? humanText
      : JSON.stringify(reply, null, 2);
    return String(text ?? "(empty response)").slice(0, 5000);
  }

  function eligible(node) {
    const parent = node.parentElement;
    if (!parent || !node.nodeValue?.trim()) return false;
    if (SKIP_TAGS.has(parent.tagName)) return false;
    if (parent.closest("#redflag-panel, #redflag-launcher, .redflag-highlight, .biasstar-highlight, .signalwarning-highlight")) return false;
    if (parent.isContentEditable || parent.closest("[contenteditable='true']")) return false;
    if (node.nodeValue.trim().length < 12 || node.nodeValue.length > 1000) return false;
    return Boolean(parent.offsetParent || parent.getClientRects().length);
  }

  function clearHighlights() {
    document.querySelectorAll(HIGHLIGHT_CLASSES).forEach(span =>
      span.replaceWith(document.createTextNode(span.textContent)));
    document.body?.normalize();
    findings = [];
    updateUI();
  }

  function showFinding(node, finding) {
    const text = node.nodeValue;
    let index = -1;
    let matched = "";

    // The LLM can return an exact matched phrase. No regex is required.
    if (finding.claim) {
      index = text.toLowerCase().indexOf(finding.claim.toLowerCase());
      if (index >= 0) matched = text.slice(index, index + finding.claim.length);
    }

    // Preserve compatibility with the existing rule-based Flask response.
    if (index < 0 && finding.pattern) {
      try {
        const match = new RegExp(finding.pattern, "i").exec(text);
        if (match) { index = match.index; matched = match[0]; }
      } catch { /* Invalid regex from service: use full analyzed text. */ }
    }

    // The LLM may flag a passage without returning an exact phrase.
    // In that case highlight the analyzed text node instead of ignoring it.
    if (index < 0) { index = 0; matched = text; }

    const fragment = document.createDocumentFragment();
    if (index > 0) fragment.append(document.createTextNode(text.slice(0, index)));
    const span = document.createElement("span");
    span.className = finding.flagtype === "biasstar" ? "biasstar-highlight"
      : finding.flagtype === "signal" ? "signalwarning-highlight" : "redflag-highlight";
    span.textContent = matched;
    span.title = `${finding.label}: ${finding.reason}`;
    const findingIndex = findings.length;
    span.dataset.redflagIndex = String(findingIndex);
    span.addEventListener("click", () => openPanel(findingIndex));
    fragment.append(span);
    if (index + matched.length < text.length)
      fragment.append(document.createTextNode(text.slice(index + matched.length)));
    node.replaceWith(fragment);
    findings.push({ ...finding, claim: matched.trim() });
  }

  async function scanPage() {
    if (!enabled || !document.body || scanning) return findings.length;
    scanning = true;
    observer?.disconnect();
    clearHighlights();
    scanStatus = "Sending page text for analysis…";
    latestExchange = null;
    updateUI();

    try {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode() && nodes.length < MAX_TEXT_NODES_PER_SCAN) {
        if (eligible(walker.currentNode)) nodes.push(walker.currentNode);
      }

      for (const node of nodes) {
        if (!enabled) break;
        const input = node.nodeValue;
        const serverReply = await analyze(input);
        if (!enabled) break;
        const received = extractFindings(serverReply);
        // Show an actual request and response, preferring one with a finding.
        if (!latestExchange || received.length) {
          latestExchange = { query: input, reply: displayResponse(serverReply) };
        }
        if (received.length) {
          showFinding(node, received[0]);
          // Any extra results are still shown in the panel.
          for (const extra of received.slice(1)) {
            findings.push({ ...extra, claim: extra.claim || input.trim() });
          }
        }
        updateUI();
      }
      scanStatus = `Analysis complete (${nodes.length} text passages checked).`;
    } catch (error) {
      scanStatus = `Analysis failed: ${error.message}`;
      console.error("RedFlag analysis request failed:", error);
    } finally {
      scanning = false;
      if (enabled) observer?.observe(document.documentElement, { childList: true, subtree: true });
      updateUI();
    }
    return findings.length;
  }

  function makeUI() {
    if (document.getElementById("redflag-launcher")) return;
    const launcher = document.createElement("button");
    launcher.id = "redflag-launcher";
    launcher.type = "button";
    launcher.setAttribute("aria-label", "Open RedFlag results");
    launcher.innerHTML = `<span aria-hidden="true">⚑</span><span>RedFlag</span><span class="rf-count">0</span>`;
    launcher.addEventListener("click", () => openPanel());

    const panel = document.createElement("aside");
    panel.id = "redflag-panel";
    panel.setAttribute("aria-label", "RedFlag scan results");
    panel.innerHTML = `
      <div class="rf-panel-head"><div class="rf-brand"><span aria-hidden="true">⚑</span> RedFlag</div><button class="rf-close" aria-label="Close results">×</button></div>
      <div class="rf-summary"></div>
      <section class="rf-exchange" aria-label="Example analysis request and response">
        <h3>Example analysis request and response</h3>
        <strong>Text sent to backend</strong><pre class="rf-query">No request yet.</pre>
        <strong>Response received</strong><pre class="rf-response">No response yet.</pre>
        <p class="rf-scan-status" role="status"></p>
      </section>
      <div class="rf-list"></div>
      <div class="rf-disclaimer">Demo screening only. A flag means “verify this claim,” not an automatic final verdict.</div>`;
    panel.querySelector(".rf-close").addEventListener("click", () => panel.classList.remove("rf-open"));
    document.documentElement.append(panel, launcher);
    updateUI();
  }

  function openPanel(index) {
    const panel = document.getElementById("redflag-panel");
    panel?.classList.add("rf-open");
    if (Number.isInteger(index)) {
      panel?.querySelectorAll(".rf-item, .bs-item, .sw-item")[index]
        ?.scrollIntoView({ block: "nearest" });
    }
  }

  function updateUI() {
    const launcher = document.getElementById("redflag-launcher");
    const panel = document.getElementById("redflag-panel");
    if (!launcher || !panel) return;
    launcher.style.display = enabled ? "flex" : "none";
    if (!enabled) panel.classList.remove("rf-open");
    launcher.querySelector(".rf-count").textContent = String(findings.length);
    panel.querySelector(".rf-summary").textContent = findings.length
      ? `${findings.length} claim${findings.length === 1 ? "" : "s"} may need verification on this page.`
      : scanning ? "Analyzing visible page text…" : "No claims were flagged by the analysis response.";

    panel.querySelector(".rf-list").innerHTML = findings.length
      ? findings.map((item, index) => {
          const itemClass = item.flagtype === "biasstar" ? "bs" : item.flagtype === "signal" ? "sw" : "rf";
          return `<article class="${itemClass}-item" data-index="${index}">
            <div class="${itemClass}-item-title">${escapeHTML(item.label)}</div>
            <div class="rf-result"> ${escapeHTML(
              item.result === "true" ? "True" :
              item.result === "false" ? "False" :
              "Unable to verify"
            )}</div>
            <div class="rf-claim">"${escapeHTML(item.claim)}"</div>
            <div class="rf-reason">${escapeHTML(item.reason)}</div>
          </article>`;
        }).join("")
      : `<div class="rf-empty">Results returned by the analysis service appear here.</div>`;

    panel.querySelector(".rf-query").textContent = latestExchange?.query ?? "No request yet.";
    panel.querySelector(".rf-response").textContent = latestExchange?.reply ?? "No response yet.";
    panel.querySelector(".rf-scan-status").textContent = scanStatus;
    chrome.runtime.sendMessage({ type: "REDFLAG_BADGE", count: findings.length }).catch(() => {});
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g,
      char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  }

  function scheduleScan() {
    if (!enabled) return;
    clearTimeout(scanTimer);
    scanTimer = setTimeout(scanPage, 700);
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "REDFLAG_SCAN") {
      scanPage().then(count => sendResponse({ count, status: scanStatus }));
      return true; // Asynchronous response after the scan finishes.
    }
    if (message.type === "REDFLAG_SET_ENABLED") {
      enabled = Boolean(message.enabled);
      if (enabled) scanPage();
      else { clearHighlights(); scanStatus = "Protection is off."; updateUI(); }
      sendResponse({ enabled, count: findings.length });
      return false;
    }
    if (message.type === "REDFLAG_STATUS") {
      sendResponse({ enabled, count: findings.length, scanning, status: scanStatus });
      return false;
    }
  });

  chrome.storage.local.get({ enabled: true, autoScan: true }).then(settings => {
    enabled = settings.enabled;
    makeUI();
    if (enabled && settings.autoScan) scanPage();
  });

  observer = new MutationObserver(mutations => {
    if (!scanning && mutations.some(m =>
      !m.target.parentElement?.closest?.("#redflag-panel, #redflag-launcher"))) scheduleScan();
  });
  if (document.documentElement)
    observer.observe(document.documentElement, { childList: true, subtree: true });
})();
