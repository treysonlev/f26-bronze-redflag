const DEFAULTS = { enabled: true, autoScan: true };

chrome.runtime.onInstalled.addListener(async () => {
  const stored = await chrome.storage.local.get(Object.keys(DEFAULTS));
  await chrome.storage.local.set({ ...DEFAULTS, ...stored });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "REDFLAG_BADGE") return;
  const tabId = sender.tab?.id;
  if (tabId == null) return;

  const count = Number(message.count) || 0;
  chrome.action.setBadgeBackgroundColor({ tabId, color: "#dc2626" });
  chrome.action.setBadgeText({ tabId, text: count ? String(Math.min(count, 99)) : "" });
  sendResponse({ ok: true });
});
