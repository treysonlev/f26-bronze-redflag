const enabledInput = document.getElementById("enabled");
const scanButton = document.getElementById("scan");
const title = document.getElementById("status-title");
const copy = document.getElementById("status-copy");
const icon = document.getElementById("status-icon");

async function currentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function messageTab(message) {
  const tab = await currentTab();
  if (!tab?.id) throw new Error("No active tab");
  return chrome.tabs.sendMessage(tab.id, message);
}

function showCount(count) {
  icon.textContent = String(count);
  title.textContent = count ? `${count} flag${count === 1 ? "" : "s"} found` : "No flags found";
  copy.textContent = count ? "Open the floating RedFlag button on the page for details." : "No claims matched the current demo rules.";
}

async function load() {
  const settings = await chrome.storage.local.get({ enabled: true });
  enabledInput.checked = settings.enabled;
  scanButton.disabled = !settings.enabled;
  try {
    const status = await messageTab({ type: "REDFLAG_STATUS" });
    showCount(status.count);
  } catch {
    icon.textContent = "!";
    title.textContent = "Page not supported";
    copy.textContent = "Open a normal webpage, then try again.";
    scanButton.disabled = true;
  }
}

enabledInput.addEventListener("change", async () => {
  const enabled = enabledInput.checked;
  await chrome.storage.local.set({ enabled });
  scanButton.disabled = !enabled;
  try {
    const result = await messageTab({ type: "REDFLAG_SET_ENABLED", enabled });
    showCount(result.count);
  } catch {}
});

scanButton.addEventListener("click", async () => {
  scanButton.disabled = true;
  scanButton.textContent = "Scanning…";
  try {
    const result = await messageTab({ type: "REDFLAG_SCAN" });
    showCount(result.count);
  } catch {
    title.textContent = "Unable to scan this page";
  } finally {
    scanButton.disabled = !enabledInput.checked;
    scanButton.textContent = "Scan this page now";
  }
});

load();
