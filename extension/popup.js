/**
 * Wahaj / وَهَج — Lightweight Popup Controller
 * Sole Responsibility: Toggle Web Highlighting ON / OFF and report Server Health.
 */

const API_BASE = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", async () => {
  const toggle = document.getElementById("extensionToggle");
  const desc = document.getElementById("toggleDesc");

  // 1. Load saved toggle state (default is true)
  chrome.storage.local.get({ wahaj_enabled: true }, (result) => {
    toggle.checked = result.wahaj_enabled;
    updateToggleText(result.wahaj_enabled);
  });

  // 2. Listen for toggle changes
  toggle.addEventListener("change", () => {
    const isEnabled = toggle.checked;
    chrome.storage.local.set({ wahaj_enabled: isEnabled }, () => {
      updateToggleText(isEnabled);
      // Notify active tab safely
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs && tabs[0] && tabs[0].id) {
          chrome.tabs.sendMessage(
            tabs[0].id,
            {
              action: "toggleHighlighting",
              enabled: isEnabled,
            },
            () => {
              // Silently ignore if active tab is not an injectable page (e.g. chrome://extensions)
              if (chrome.runtime.lastError) {
                // No-op
              }
            }
          );
        }
      });
    });
  });

  // 3. Check backend server health
  await checkHealth();
});

function updateToggleText(isEnabled) {
  const desc = document.getElementById("toggleDesc");
  if (isEnabled) {
    desc.textContent = "التظليل والتحليل مفعّل ✓";
    desc.classList.remove("disabled");
  } else {
    desc.textContent = "التظليل معطّل مؤقتاً ✕";
    desc.classList.add("disabled");
  }
}

async function checkHealth() {
  const dot = document.getElementById("statusDot");
  const text = document.getElementById("statusText");
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2500) });
    if (res.ok) {
      dot.classList.add("online");
      text.textContent = "الخادم متصل وجاهز للتحليل ✓";
    } else {
      throw new Error("unhealthy");
    }
  } catch {
    dot.classList.remove("online");
    text.textContent = "الخادم غير متصل — شغّل run.py";
  }
}
