(() => {
  if (window.__redflagLoaded) return;
  window.__redflagLoaded = true;

  const EXACT_RULES = [
    { pattern: /the earth is flat/i, label: "Known false claim", reason: "Modern observations, satellite data, and centuries of measurement show that Earth is an oblate spheroid." },
    { pattern: /vaccines? (?:contain|have) microchips?/i, label: "Known false claim", reason: "Authorized vaccine ingredient lists do not include tracking microchips." },
    { pattern: /5g (?:causes|created|spreads?) (?:covid|coronavirus)/i, label: "Known false claim", reason: "Radio waves cannot create or transmit a biological virus." },
    { pattern: /(?:drink|drinking) bleach (?:cures?|prevents?|treats?)/i, label: "Dangerous false claim", reason: "Swallowing bleach is poisonous and is not a medical treatment." },
    { pattern: /the moon landing was (?:fake|faked|staged)/i, label: "Known false claim", reason: "Independent tracking, returned lunar material, imagery, and later observations corroborate the Apollo landings." }
  ];

  const SIGNAL_RULES = [
    { pattern: /doctors? (?:do not|don['’]t) want you to know/i, label: "Manipulative wording", reason: "This phrase discourages checking qualified medical sources and provides no evidence by itself." },
    { pattern: /share (?:this )?before (?:it['’]s|it is|this gets|it gets) deleted/i, label: "Urgency tactic", reason: "Pressure to share immediately is a common signal that a claim should be verified first." },
    { pattern: /(?:100%|completely) guaranteed/i, label: "Absolute claim", reason: "Absolute guarantees require unusually strong evidence. Check the original source and supporting data." },
    { pattern: /mainstream media (?:won['’]t|will not|doesn['’]t) tell you/i, label: "Conspiracy framing", reason: "This wording attacks possible sources without supplying evidence for the claim." },
    { pattern: /miracle (?:cure|treatment|solution)/i, label: "Extraordinary claim", reason: "Medical miracle claims need strong clinical evidence and confirmation from reliable health authorities." }
  ];

  const BIAS_RULES = [
    { pattern: /(?:artifical intelligence| ai |data center|llm)/i, label: "Controversial topic", reason: "LLMs (aslo referred to as Artifical Intelligence) is a very divisive topic with strong opinion on both sides." }
  ]

  const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA", "INPUT", "SELECT", "OPTION", "CODE", "PRE"]);
  let enabled = true;
  let findings = [];
  let scanTimer;
  let scanning = false;
  let observer;

  function getRule(text) {
    return [...EXACT_RULES, ...SIGNAL_RULES, ...BIAS_RULES].find(rule => rule.pattern.test(text));
  }

  function eligible(node) {
    const parent = node.parentElement;
    if (!parent || !node.nodeValue?.trim()) return false;
    if (SKIP_TAGS.has(parent.tagName)) return false;
    if (parent.closest("#redflag-panel, #redflag-launcher, .redflag-highlight, .biasstar-hightlight")) return false;
    if (parent.isContentEditable || parent.closest("[contenteditable='true']")) return false;
    if (node.nodeValue.trim().length < 12 || node.nodeValue.length > 1000) return false;
    return Boolean(parent.offsetParent || parent.getClientRects().length);
  }

  function clearHighlights() {
    document.querySelectorAll(".redflag-highlight, .biasstar-highlight").forEach(span => span.replaceWith(document.createTextNode(span.textContent)));
    document.body?.normalize();
    findings = [];
    updateUI();
  }

  function flagTextNode(node, rule) {
    const text = node.nodeValue;
    const match = text.match(rule.pattern);
    if (!match || match.index == null) return;

    const before = text.slice(0, match.index);
    const matched = text.slice(match.index, match.index + match[0].length);
    const after = text.slice(match.index + match[0].length);
    const fragment = document.createDocumentFragment();
    if (before) fragment.append(document.createTextNode(before));

    const span = document.createElement("span");
    

    if (BIAS_RULES.includes(rule))
      span.className = "biasstar-highlight"
    if (EXACT_RULES.includes(rule))
      span.className = "redflag-highlight";
    if (SIGNAL_RULES.includes(rule))
      span.className = "signalwarning-highlight"
    span.textContent = matched;
    span.title = `${rule.label}: ${rule.reason}`;
    const findingIndex = findings.length;
    span.dataset.redflagIndex = String(findingIndex);
    span.addEventListener("click", () => openPanel(findingIndex));
    fragment.append(span);
    if (after) fragment.append(document.createTextNode(after));
    node.replaceWith(fragment);

    findings.push({ claim: matched, label: rule.label, reason: rule.reason });
  }

  function scanPage() {
    if (!enabled || !document.body || scanning) return;
    scanning = true;
    observer?.disconnect();
    clearHighlights();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) if (eligible(walker.currentNode)) nodes.push(walker.currentNode);
    for (const node of nodes.slice(0, 5000)) {
      const rule = getRule(node.nodeValue);
      if (rule) flagTextNode(node, rule);
    }
    updateUI();
    observer?.observe(document.documentElement, { childList: true, subtree: true });
    scanning = false;
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
      <div class="rf-summary"></div><div class="rf-list"></div>
      <div class="rf-disclaimer">Demo screening only. A flag means “verify this claim,” not an automatic final verdict.</div>`;
    panel.querySelector(".rf-close").addEventListener("click", () => panel.classList.remove("rf-open"));
    document.documentElement.append(panel, launcher);
    updateUI();
  }

  function openPanel(index) {
    const panel = document.getElementById("redflag-panel");
    panel?.classList.add("rf-open");
    if (Number.isInteger(index)) panel?.querySelectorAll(".rf-item, .bs-item, .sw-item")[index]?.scrollIntoView({ block: "nearest" });
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
      : "No matching warning signals found on this page.";
    panel.querySelector(".rf-list").innerHTML = findings.length
      ? findings.map((item, index) => 
      {
        const rule = getRule(item.claim)
        const itemClass =  EXACT_RULES.includes(rule) ? "rf" : BIAS_RULES.includes(rule) ? "bs" : SIGNAL_RULES.includes(rule) ? "sw" : "";
      return `<article class="${itemClass}-item" data-index="${index}"><div class="${itemClass}-item-title">${escapeHTML(item.label)}</div><div class="rf-claim">“${escapeHTML(item.claim)}”</div><div class="rf-reason">${escapeHTML(item.reason)}</div></article>`}).join("")
      : `<div class="rf-empty">RedFlag did not find any claims covered by the current demo rules.</div>`;
    chrome.runtime.sendMessage({ type: "REDFLAG_BADGE", count: findings.length }).catch(() => {});
  }

  function escapeHTML(value) {
    return value.replace(/[&<>"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[char]));
  }

  function scheduleScan() {
    if (!enabled) return;
    clearTimeout(scanTimer);
    scanTimer = setTimeout(scanPage, 700);
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === "REDFLAG_SCAN") {
      scanPage();
      sendResponse({ count: findings.length });
    }
    if (message.type === "REDFLAG_SET_ENABLED") {
      enabled = Boolean(message.enabled);
      if (enabled) scanPage(); else clearHighlights();
      updateUI();
      sendResponse({ enabled, count: findings.length });
    }
    if (message.type === "REDFLAG_STATUS") sendResponse({ enabled, count: findings.length });
    return true;
  });

  chrome.storage.local.get({ enabled: true, autoScan: true }).then(settings => {
    enabled = settings.enabled;
    makeUI();
    if (enabled && settings.autoScan) scanPage();
  });

  observer = new MutationObserver(mutations => {
    if (!scanning && mutations.some(m => !m.target.parentElement?.closest?.("#redflag-panel, #redflag-launcher"))) scheduleScan();
  });
  if (document.documentElement) observer.observe(document.documentElement, { childList: true, subtree: true });
})();
