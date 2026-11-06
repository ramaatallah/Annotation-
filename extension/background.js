/**
 * Wahaj / وَهَج — Background Service Worker
 * Handles context menu integration and messaging between popup ↔ content scripts.
 */

const API_BASE = "http://127.0.0.1:8000";

/* ─── Context Menu: Right-click → Analyze with Wahaj ─── */
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "wahaj-analyze-selection",
    title: "🌟 حلّل بـ وَهَج (Wahaj)",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "wahaj-analyze-selection" && info.selectionText && tab && tab.id) {
    chrome.tabs.sendMessage(
      tab.id,
      {
        action: "triggerAnalysis",
        text: info.selectionText,
        url: tab.url,
        pageTitle: tab.title,
      },
      () => {
        if (chrome.runtime.lastError) {
          // Tab does not support content script
        }
      }
    );
  }
});

/* ─── Message Router ─── */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "analyzeText") {
    analyzeText(message.text, message.url, message.pageTitle)
      .then((result) => sendResponse({ success: true, data: result }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // Keep message channel open for async response
  }

  if (message.action === "saveAnnotation") {
    saveAnnotation(message.payload)
      .then((result) => sendResponse({ success: true, data: result }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (message.action === "updateAnnotation") {
    updateAnnotation(message.id, message.payload)
      .then((result) => sendResponse({ success: true, data: result }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (message.action === "deleteAnnotation") {
    deleteAnnotation(message.id)
      .then(() => sendResponse({ success: true }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (message.action === "getAnnotations") {
    getAnnotations(message.url)
      .then((result) => sendResponse({ success: true, data: result }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true;
  }
});

/* ─── API Calls ─── */
async function analyzeText(text, url, pageTitle) {
  const res = await fetch(`${API_BASE}/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, url, page_title: pageTitle }),
  });
  if (!res.ok) throw new Error(`Analysis failed (${res.status})`);
  return res.json();
}

async function saveAnnotation(payload) {
  const res = await fetch(`${API_BASE}/v1/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Save failed (${res.status})`);
  return res.json();
}

async function updateAnnotation(id, payload) {
  const res = await fetch(`${API_BASE}/v1/annotations/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Update failed (${res.status})`);
  return res.json();
}

async function deleteAnnotation(id) {
  const res = await fetch(`${API_BASE}/v1/annotations/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Delete failed (${res.status})`);
  return res.json();
}

async function getAnnotations(url) {
  const res = await fetch(
    `${API_BASE}/v1/annotations?url=${encodeURIComponent(url)}`
  );
  if (!res.ok) throw new Error(`Fetch failed (${res.status})`);
  return res.json();
}
