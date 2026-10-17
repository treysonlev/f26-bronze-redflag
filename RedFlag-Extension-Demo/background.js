const DEFAULTS = { enabled: true, autoScan: true };

chrome.runtime.onInstalled.addListener(async () => {
  const stored = await chrome.storage.local.get(Object.keys(DEFAULTS));
  await chrome.storage.local.set({ ...DEFAULTS, ...stored });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "REDFLAG_BADGE") {
    const tabId = sender.tab?.id;
    if (tabId == null) return;

    const count = Number(message.count) || 0;
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#dc2626" });
    chrome.action.setBadgeText({
      tabId,
      text: count ? String(Math.min(count, 99)) : ""
    });

    sendResponse({ ok: true });
    return;
  }

  if (message.type === "REDFLAG_ANALYZE") {
    fetch("http://127.0.0.1:5000/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: message.text })
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }
        return response.json();
      })
      .then(result => {
        console.log("RedFlag analysis response:", result)
        sendResponse(result)
      })
      .catch(error => {
        console.error("RedFlag backend request failed:", error)
        sendResponse({ error: error.message })
      });
    return true;
  }
});
