/**
 * Wahaj / وَهَج — Content Script
 * Enterprise Arabic Web Annotation & NLP Engine.
 *
 * Card Layout (As requested):
 * 1. 📖 النص المظلل (Selected Text)
 * 2. 📌 الملاحظة المكتوبة (Note - directly underneath)
 * 3. 🏷️ الكيانات والمفاهيم المكتشفة (Entities)
 * 4. 🔤 الجذور الصرفية الثلاثية (Trilateral Roots)
 * 5. أزرار التحكم (تعديل، حذف، إغلاق)
 */

(() => {
  "use strict";

  // State
  let isHighlightingEnabled = true;
  let activePopup = null;
  let activeTooltip = null;
  let currentAnnotations = [];
  let currentSelectedRange = null;

  /* ═══════════════════════════════════════════════
     0. CANONICAL URL & STRING NORMALIZATION
     ═══════════════════════════════════════════════ */
  function canonicalizeUrl(rawUrl) {
    if (!rawUrl) return "";
    try {
      let u = decodeURI(rawUrl).trim();
      if (u.includes("#")) {
        u = u.split("#")[0];
      }
      return u.replace(/\/+$/, "");
    } catch (e) {
      return (rawUrl || "").trim().split("#")[0].replace(/\/+$/, "");
    }
  }

  function normalizeArabicChar(ch) {
    const code = ch.charCodeAt(0);

    // 1. Skip Arabic Harakat (diacritics), Tatweel, and invisible control characters
    // Harakat: \u064B (fathatan) to \u0652 (sukun), \u0670 (dagger alif), \u0671 (wasla), \u0640 (tatweel)
    if (
      (code >= 0x064b && code <= 0x0652) ||
      code === 0x0670 ||
      code === 0x0671 ||
      code === 0x0640 ||
      (code >= 0x200b && code <= 0x200f) ||
      code === 0xfeff ||
      code === 0x00ad
    ) {
      return null; // Strip completely
    }

    // 2. Unify Alef forms
    if (ch === "أ" || ch === "إ" || ch === "آ" || ch === "ٱ") return "ا";

    // 3. Unify Taa Marbuta
    if (ch === "ة") return "ه";

    // 4. Unify Yaa / Alef Maksura
    if (ch === "ى") return "ي";

    // 5. Quotes, brackets, citations -> convert to space for uniform word boundaries
    if (
      ch === "«" ||
      ch === "»" ||
      ch === "“" ||
      ch === "”" ||
      ch === '"' ||
      ch === "'" ||
      ch === "(" ||
      ch === ")" ||
      ch === "[" ||
      ch === "]" ||
      ch === "{" ||
      ch === "}"
    ) {
      return " ";
    }

    // 6. Punctuation (Arabic & Latin) -> convert to space
    if (
      ch === "\u060C" || // Arabic comma ،
      ch === "\u061B" || // Arabic semicolon ؛
      ch === "\u061F" || // Arabic question mark ؟
      ch === "." ||
      ch === "," ||
      ch === ";" ||
      ch === ":" ||
      ch === "!" ||
      ch === "?" ||
      ch === "-" ||
      ch === "—" ||
      ch === "–" ||
      ch === "/" ||
      ch === "\\"
    ) {
      return " ";
    }

    // 7. Whitespace (including non-breaking spaces \u00A0) -> convert to space
    if (/\s/.test(ch) || code === 0x00a0) {
      return " ";
    }

    return ch.toLowerCase();
  }

  function normalizeStringForMatching(str) {
    if (!str) return "";
    let out = "";
    let inSpace = false;
    for (let i = 0; i < str.length; i++) {
      const n = normalizeArabicChar(str[i]);
      if (n === null) continue;
      if (n === " ") {
        if (!inSpace) {
          out += " ";
          inSpace = true;
        }
      } else {
        out += n;
        inSpace = false;
      }
    }
    return out.trim();
  }

  /* ═══════════════════════════════════════════════
     1. INITIALIZATION & LIFECYCLE
     ═══════════════════════════════════════════════ */
  async function init() {
    chrome.storage.local.get({ wahaj_enabled: true }, (res) => {
      isHighlightingEnabled = res.wahaj_enabled;
    });

    // Run immediate restoration from local cache & backend
    await restoreHighlights();

    // Staggered retries to guarantee restoration after async page hydration / DOM rendering
    [300, 800, 1800, 3500].forEach((delay) => {
      setTimeout(() => restoreHighlights(), delay);
    });

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => restoreHighlights());
    }
    window.addEventListener("pageshow", () => restoreHighlights());

    // Observe dynamic SPA content changes
    setupMutationWatcher();

    setupSelectionListener();
    setupMessageListener();
  }

  let mutationDebounceTimer = null;
  function setupMutationWatcher() {
    try {
      const observer = new MutationObserver(() => {
        clearTimeout(mutationDebounceTimer);
        mutationDebounceTimer = setTimeout(() => {
          if (currentAnnotations.length > 0) {
            applyAnnotationsToDom(currentAnnotations);
          }
        }, 500);
      });

      const target = document.body || document.documentElement;
      if (target) {
        observer.observe(target, { childList: true, subtree: true });
      }
    } catch (e) {}
  }

  /* ═══════════════════════════════════════════════
     2. SELECTION LISTENER (Captures DOM Range & Text)
     ═══════════════════════════════════════════════ */
  function setupSelectionListener() {
    document.addEventListener("mouseup", (e) => {
      if (!isHighlightingEnabled) return;

      if (
        e.target.closest(".wahaj-selection-popup") ||
        e.target.closest(".wahaj-tooltip-card") ||
        e.target.closest(".wahaj-highlight")
      ) {
        return;
      }

      const selection = window.getSelection();
      const selectedText = selection.toString().trim();

      const arabicPattern = /[\u0600-\u06FF]/g;
      const arabicMatches = selectedText.match(arabicPattern);

      if (selectedText.length >= 3 && arabicMatches && arabicMatches.length >= 2) {
        const range = selection.getRangeAt(0);
        currentSelectedRange = range.cloneRange();
        const rect = range.getBoundingClientRect();
        showSelectionPopup(selectedText, rect);
      } else {
        removePopup();
        currentSelectedRange = null;
      }
    });

    document.addEventListener("mousedown", (e) => {
      if (activePopup && !activePopup.contains(e.target) && !e.target.closest(".wahaj-highlight")) {
        removePopup();
      }
      if (activeTooltip && !activeTooltip.contains(e.target) && !e.target.closest(".wahaj-highlight")) {
        removeTooltip();
      }
    });
  }

  /* ═══════════════════════════════════════════════
     3. SELECTION POPUP (In-Page Note Box)
     ═══════════════════════════════════════════════ */
  function showSelectionPopup(text, rect) {
    removePopup();
    removeTooltip();

    const popup = document.createElement("div");
    popup.className = "wahaj-selection-popup notranslate";
    popup.setAttribute("translate", "no");

    popup.innerHTML = `
      <div class="wahaj-popup-header">
        <span class="wahaj-popup-title">🌟 وَهَج — تظليل نص عربي</span>
        <button class="wahaj-popup-close" id="wahajPopupClose">✕</button>
      </div>
      <div class="wahaj-selected-preview">${text}</div>
      <textarea class="wahaj-note-input" id="wahajNoteInput" placeholder="✏️ اكتب ملاحظتك على هذا النص (اختياري)..." rows="3"></textarea>
      <div class="wahaj-popup-actions">
        <button class="wahaj-btn wahaj-btn-save" id="wahajSaveBtn">
          💾 حفظ واستخراج الكيانات والجذور
        </button>
        <button class="wahaj-btn wahaj-btn-cancel" id="wahajCancelBtn">
          إلغاء
        </button>
      </div>
    `;

    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    popup.style.top = `${rect.bottom + scrollY + 10}px`;
    popup.style.left = `${Math.max(12, rect.left + scrollX - 40)}px`;

    document.body.appendChild(popup);
    activePopup = popup;

    setTimeout(() => {
      const input = popup.querySelector("#wahajNoteInput");
      if (input) input.focus();
    }, 100);

    popup.querySelector("#wahajPopupClose").addEventListener("click", removePopup);
    popup.querySelector("#wahajCancelBtn").addEventListener("click", removePopup);

    popup.querySelector("#wahajSaveBtn").addEventListener("click", () => {
      const note = popup.querySelector("#wahajNoteInput").value.trim();
      handleSave(text, note, popup);
    });

    popup.querySelector("#wahajNoteInput").addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.key === "Enter") {
        const note = popup.querySelector("#wahajNoteInput").value.trim();
        handleSave(text, note, popup);
      }
    });
  }

  /* ═══════════════════════════════════════════════
     4. SAVE & ANALYZE (Multi-Node & Cross-Element)
     ═══════════════════════════════════════════════ */
  async function handleSave(text, note, popup) {
    const saveBtn = popup.querySelector("#wahajSaveBtn");
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<span class="wahaj-spinner"></span> جارٍ التحليل الذكي للكيانات والجذور...`;

    const payload = {
      url: window.location.href,
      page_title: document.title,
      selected_text: text,
      note: note || null,
      color: "#f1c75b",
      auto_analyze: true,
      author_name: "باحث",
    };

    const rangeToHighlight = currentSelectedRange ? currentSelectedRange.cloneRange() : null;

    try {
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage(
          { action: "saveAnnotation", payload },
          (res) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else if (res && res.success) {
              resolve(res.data);
            } else {
              reject(new Error(res ? res.error : "Unknown error"));
            }
          }
        );
      });

      removePopup();

      let markElement = null;
      if (rangeToHighlight) {
        markElement = highlightRange(rangeToHighlight, response);
      }
      if (!markElement) {
        markElement = findAndHighlightCrossNodeText(text, response);
      }

      currentAnnotations.push(response);

      // Cache locally in chrome.storage for instant offline recovery
      updateLocalCache(currentAnnotations);

      // IMMEDIATELY OPEN IN-PAGE CARD OVER THE HIGHLIGHT!
      if (markElement) {
        showTooltipCard(markElement, response);
      }

      if (window.getSelection) {
        window.getSelection().removeAllRanges();
      }
      currentSelectedRange = null;

      showToast("✅ تم التحليل واستخراج الكيانات والجذور!", "success");
    } catch (err) {
      console.error("Wahaj save error:", err);
      saveBtn.disabled = false;
      saveBtn.innerHTML = "💾 حفظ واستخراج الكيانات والجذور";
      const msg = err && err.message ? err.message : "";
      if (msg.includes("Extension context invalidated")) {
        showToast("⚠️ يرجى تحديث صفحة الويب (اضغط F5) لإعادة ربط الإضافة بالمتصفح", "warning");
      } else if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
        showToast("❌ تعذر الاتصال بالخادم — شغّل run.py في مجلد backend", "error");
      } else {
        showToast(`❌ خطأ: ${msg || "تأكد أن الخادم يعمل"}`, "error");
      }
    }
  }

  /* ═══════════════════════════════════════════════
     5. ROBUST MULTI-NODE HIGHLIGHTING ENGINE
     ═══════════════════════════════════════════════ */
  function highlightRange(range, annotationData) {
    if (!range) return null;

    const textNodes = getTextNodesInRange(range);
    if (textNodes.length === 0) return null;

    let firstMark = null;

    textNodes.forEach((node) => {
      let start = 0;
      let end = node.textContent.length;

      if (node === range.startContainer) {
        start = range.startOffset;
      }
      if (node === range.endContainer) {
        end = range.endOffset;
      }

      if (start >= end) return;

      const chunk = node.textContent.substring(start, end);
      if (!chunk.trim()) return;

      const afterNode = node.splitText(start);
      afterNode.splitText(end - start);

      const mark = document.createElement("mark");
      mark.className = "wahaj-highlight notranslate";
      mark.setAttribute("translate", "no");
      mark.dataset.annotationId = annotationData.id;
      mark.dataset.annotationData = JSON.stringify(annotationData);
      mark.title = "اضغط لعرض النص والملاحظة والكيانات والجذور";

      afterNode.parentNode.insertBefore(mark, afterNode);
      mark.appendChild(afterNode);

      attachHighlightListeners(mark, annotationData);

      if (!firstMark) firstMark = mark;
    });

    return firstMark;
  }

  function getTextNodesInRange(range) {
    const textNodes = [];
    let root = range.commonAncestorContainer;
    if (root.nodeType === Node.TEXT_NODE) {
      root = root.parentNode;
    }

    const walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: (node) => {
          const parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;
          const tag = parent.tagName.toUpperCase();
          if (
            tag === "SCRIPT" ||
            tag === "STYLE" ||
            tag === "NOSCRIPT" ||
            tag === "TEMPLATE" ||
            tag === "SVG" ||
            parent.closest(".wahaj-selection-popup, .wahaj-tooltip-card, .wahaj-toast")
          ) {
            return NodeFilter.FILTER_REJECT;
          }
          if (range.intersectsNode(node)) {
            return NodeFilter.FILTER_ACCEPT;
          }
          return NodeFilter.FILTER_REJECT;
        },
      }
    );

    while (walker.nextNode()) {
      textNodes.push(walker.currentNode);
    }
    return textNodes;
  }

  /* ═══════════════════════════════════════════════
     6. HIGH-PRECISION CROSS-NODE TEXT LOCATOR
     ═══════════════════════════════════════════════ */
  function createRangeForTargetText(container, targetText) {
    if (!container || !targetText) return null;

    const cleanTargetNorm = normalizeStringForMatching(targetText);
    if (!cleanTargetNorm || cleanTargetNorm.length < 2) return null;

    // Collect content text nodes, skipping styles, scripts and Wahaj UI
    const textNodes = [];
    const walker = document.createTreeWalker(
      container,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: (node) => {
          const parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;
          const tag = parent.tagName.toUpperCase();
          if (
            tag === "SCRIPT" ||
            tag === "STYLE" ||
            tag === "NOSCRIPT" ||
            tag === "TEMPLATE" ||
            tag === "SVG" ||
            tag === "CANVAS" ||
            tag === "BUTTON" ||
            tag === "INPUT" ||
            tag === "TEXTAREA" ||
            tag === "SELECT" ||
            parent.closest(".wahaj-selection-popup, .wahaj-tooltip-card, .wahaj-toast")
          ) {
            return NodeFilter.FILTER_REJECT;
          }
          return NodeFilter.FILTER_ACCEPT;
        },
      }
    );

    while (walker.nextNode()) {
      textNodes.push(walker.currentNode);
    }
    if (textNodes.length === 0) return null;

    // Build contiguous character map with virtual spaces across block boundaries
    const charMap = [];
    let lastBlockEl = null;

    for (const node of textNodes) {
      const parentBlock = node.parentElement
        ? node.parentElement.closest("p, li, div, h1, h2, h3, h4, h5, h6, blockquote, td, th, tr, dt, dd, section, article")
        : null;

      if (lastBlockEl && parentBlock && lastBlockEl !== parentBlock) {
        charMap.push({ node, offset: 0, char: " ", isVirtual: true });
      }
      lastBlockEl = parentBlock;

      const content = node.textContent;
      for (let i = 0; i < content.length; i++) {
        charMap.push({ node, offset: i, char: content[i], isVirtual: false });
      }
    }

    if (charMap.length === 0) return null;

    // Build normalized stream with direct 1-to-1 index mapping to charMap
    const normStream = [];
    let inSpace = false;

    for (let idx = 0; idx < charMap.length; idx++) {
      const entry = charMap[idx];
      const n = normalizeArabicChar(entry.char);
      if (n === null) continue; // Diacritics, tatweel, zero-width chars skipped
      if (n === " ") {
        if (!inSpace) {
          normStream.push({ normChar: " ", charMapIndex: idx });
          inSpace = true;
        }
      } else {
        normStream.push({ normChar: n, charMapIndex: idx });
        inSpace = false;
      }
    }

    if (normStream.length === 0) return null;

    const streamString = normStream.map((s) => s.normChar).join("");

    // 1. Exact Normalized Substring Search
    let matchIdx = streamString.indexOf(cleanTargetNorm);

    // 2. Anchor Word Matching (for citations [1] or Wikipedia templates interspersed in text)
    if (matchIdx === -1) {
      const words = cleanTargetNorm.split(" ").filter((w) => w.length > 1);
      if (words.length >= 4) {
        const startAnchor = words.slice(0, 3).join(" ");
        const endAnchor = words.slice(-3).join(" ");
        const posStart = streamString.indexOf(startAnchor);
        if (posStart !== -1) {
          const posEnd = streamString.indexOf(endAnchor, posStart);
          if (posEnd !== -1) {
            const matchSpan = (posEnd + endAnchor.length) - posStart;
            const expectedSpan = cleanTargetNorm.length;
            if (Math.abs(matchSpan - expectedSpan) / expectedSpan < 0.35) {
              const startEntry = normStream[posStart];
              const endEntry = normStream[posEnd + endAnchor.length - 1];
              if (startEntry && endEntry) {
                const startDom = charMap[startEntry.charMapIndex];
                const endDom = charMap[endEntry.charMapIndex];
                if (startDom && endDom) {
                  try {
                    const range = document.createRange();
                    range.setStart(startDom.node, startDom.offset);
                    range.setEnd(endDom.node, endDom.offset + 1);
                    return range;
                  } catch (e) {}
                }
              }
            }
          }
        }
      }
    }

    if (matchIdx === -1) return null;

    const endNormIdx = matchIdx + cleanTargetNorm.length - 1;
    if (endNormIdx >= normStream.length) return null;

    const startEntry = normStream[matchIdx];
    const endEntry = normStream[endNormIdx];
    if (!startEntry || !endEntry) return null;

    const startDom = charMap[startEntry.charMapIndex];
    const endDom = charMap[endEntry.charMapIndex];
    if (!startDom || !endDom) return null;

    try {
      const range = document.createRange();
      range.setStart(startDom.node, startDom.offset);
      range.setEnd(endDom.node, endDom.offset + 1);
      return range;
    } catch (e) {
      return null;
    }
  }

  function findAndHighlightCrossNodeText(searchText, annotationData) {
    if (!searchText) return null;

    const existing = document.querySelector(`mark.wahaj-highlight[data-annotation-id="${annotationData.id}"]`);
    if (existing) return existing;

    const cleanTargetNorm = normalizeStringForMatching(searchText);
    if (!cleanTargetNorm) return null;

    const leafBlocks = document.querySelectorAll("p, li, blockquote, dt, dd, td, th, h1, h2, h3, h4, h5, h6");

    // Pass 1: Check Leaf Blocks (Fast Path)
    for (const block of leafBlocks) {
      if (block.closest(".wahaj-selection-popup, .wahaj-tooltip-card, .wahaj-toast")) continue;
      const bNorm = normalizeStringForMatching(block.textContent);
      if (bNorm.includes(cleanTargetNorm)) {
        const range = createRangeForTargetText(block, searchText);
        if (range) {
          return highlightRange(range, annotationData);
        }
      }
    }

    // Pass 2: Main Article / Body Content Container
    const mainCont =
      document.querySelector("article, main, [role='main'], .mw-parser-output, .entry-content, .article-body, #bodyContent, #content") ||
      document.body;

    const contRange = createRangeForTargetText(mainCont, searchText);
    if (contRange) {
      return highlightRange(contRange, annotationData);
    }

    // Pass 3: Multi-Paragraph Split Matching (Selections spanning multiple paragraphs or list items)
    const paragraphs = searchText
      .split(/\n+/)
      .map((p) => p.trim())
      .filter((p) => p.length >= 10);

    if (paragraphs.length > 1) {
      let anyMark = null;
      for (const para of paragraphs) {
        const pNorm = normalizeStringForMatching(para);
        let foundRange = null;

        for (const block of leafBlocks) {
          if (block.closest(".wahaj-selection-popup, .wahaj-tooltip-card, .wahaj-toast")) continue;
          const bNorm = normalizeStringForMatching(block.textContent);
          if (bNorm.includes(pNorm)) {
            foundRange = createRangeForTargetText(block, para);
            if (foundRange) break;
          }
        }

        if (!foundRange) {
          foundRange = createRangeForTargetText(mainCont, para);
        }

        if (foundRange) {
          const m = highlightRange(foundRange, annotationData);
          if (m && !anyMark) anyMark = m;
        }
      }
      if (anyMark) return anyMark;
    }

    return null;
  }

  /* ═══════════════════════════════════════════════
     7. CLICK & HOVER LISTENERS ON HIGHLIGHT
     ═══════════════════════════════════════════════ */
  function attachHighlightListeners(markElement, annotationData) {
    markElement.addEventListener("click", (e) => {
      e.stopPropagation();
      showTooltipCard(markElement, annotationData);
    });

    let hoverTimer;
    markElement.addEventListener("mouseenter", () => {
      hoverTimer = setTimeout(() => {
        if (!activeTooltip) {
          showTooltipCard(markElement, annotationData);
        }
      }, 200);
    });

    markElement.addEventListener("mouseleave", () => {
      clearTimeout(hoverTimer);
    });
  }

  /* ═══════════════════════════════════════════════
     8. THE IN-PAGE INTERACTIVE CARD (Exact Requested Layout)
     Order:
     1. 📖 النص المظلل (Selected Text)
     2. 📌 الملاحظة (Note)
     3. 🏷️ الكيانات المكتشفة (Entities)
     4. 🔤 الجذور الصرفية الثلاثية (Trilateral Roots)
     5. أزرار التحكم (تعديل، حذف)
     ═══════════════════════════════════════════════ */
  function showTooltipCard(anchor, annotationData) {
    removeTooltip();

    const tooltip = document.createElement("div");
    tooltip.className = "wahaj-tooltip-card notranslate";
    tooltip.setAttribute("translate", "no");

    // 0. Header with close button
    const headerSection = `
      <div class="wahaj-tooltip-header">
        <span class="wahaj-tooltip-title">🌟 بطاقة التحليل الصرفي والدلالي</span>
        <button class="wahaj-tooltip-close" id="wahajCardClose" title="إغلاق">✕</button>
      </div>
    `;

    // 1. SELECTED TEXT (FIRST!)
    const selectedTextSection = `
      <div class="wahaj-card-section">
        <span class="wahaj-card-label">📖 النص المظلل:</span>
        <div class="wahaj-card-selected-text">${annotationData.selected_text}</div>
      </div>
    `;

    // 2. NOTE (SECOND - DIRECTLY UNDER TEXT!)
    let noteSection = "";
    if (annotationData.note) {
      noteSection = `
        <div class="wahaj-card-section">
          <span class="wahaj-card-label">📌 الملاحظة المكتوبة:</span>
          <div class="wahaj-card-note">${annotationData.note}</div>
        </div>
      `;
    }

    // 3. ENTITIES SECTION (THIRD!)
    let entitiesSection = "";
    const entities = annotationData.entities || [];
    if (entities.length > 0) {
      const badges = entities
        .map((ent) => {
          const catLabel = getCategoryLabel(ent.category);
          const catNameAr = ent.label_ar || getCategoryArabicName(ent.category);
          return `
            <span class="wahaj-entity-badge" data-category="${ent.category}">
              ${catLabel} <strong>${ent.text}</strong>
              <span class="wahaj-entity-category-pill">${catNameAr}</span>
            </span>
          `;
        })
        .join("");

      const avgConf = entities.reduce((s, e) => s + (e.confidence || 0), 0) / entities.length;
      const confPercent = Math.round(avgConf * 100);

      entitiesSection = `
        <div class="wahaj-card-section">
          <span class="wahaj-card-label">🏷️ الكيانات والمفاهيم المكتشفة:</span>
          <div class="wahaj-entity-list">${badges}</div>
          <div style="margin-top:8px;display:flex;align-items:center;gap:8px;">
            <span style="font-size:11px;color:#aaa;">نسبة الثقة (Confidence):</span>
            <div class="wahaj-confidence-bar-track" style="flex:1;">
              <div class="wahaj-confidence-bar-fill" style="width:${confPercent}%;"></div>
            </div>
            <span style="font-size:11px;color:#FFE082;font-weight:700;">${confPercent}%</span>
          </div>
        </div>
      `;
    }

    // 4. TRILATERAL ROOTS SECTION (FOURTH!)
    let rootsSection = "";
    const allRoots = [];
    entities.forEach((ent) => {
      if (ent.roots) {
        ent.roots.forEach((r) => {
          if (r.root && r.root !== "None" && !allRoots.some((existing) => existing.word === r.word && existing.root === r.root)) {
            allRoots.push(r);
          }
        });
      }
    });

    if (allRoots.length > 0) {
      const rootItems = allRoots
        .map(
          (r) => `
        <div class="wahaj-root-item">
          <span class="wahaj-root-word">${r.word}</span>
          <span class="wahaj-root-arrow">◀</span>
          <span class="wahaj-root-value">${r.root}</span>
        </div>
      `
        )
        .join("");

      rootsSection = `
        <div class="wahaj-card-section">
          <span class="wahaj-card-label">🔤 الجذور اللغوية:</span>
          <div class="wahaj-roots-grid">${rootItems}</div>
        </div>
      `;
    }

    // 5. ACTION BUTTONS (Edit + Delete)
    const actionsSection = `
      <div class="wahaj-card-actions">
        <button class="wahaj-card-btn wahaj-card-btn-edit" id="wahajCardEdit">✏️ تعديل الملاحظة</button>
        <button class="wahaj-card-btn wahaj-card-btn-delete" id="wahajCardDelete">🗑️ حذف التظليل</button>
      </div>
    `;

    tooltip.innerHTML = headerSection + selectedTextSection + noteSection + entitiesSection + rootsSection + actionsSection;

    const rect = anchor.getBoundingClientRect();
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;

    tooltip.style.top = `${rect.bottom + scrollY + 8}px`;
    tooltip.style.left = `${Math.max(12, rect.left + scrollX - 30)}px`;

    document.body.appendChild(tooltip);
    activeTooltip = tooltip;

    tooltip.querySelector("#wahajCardClose").addEventListener("click", (e) => {
      e.stopPropagation();
      removeTooltip();
    });

    tooltip.querySelector("#wahajCardEdit").addEventListener("click", (e) => {
      e.stopPropagation();
      handleEditAnnotation(annotationData, anchor);
    });

    tooltip.querySelector("#wahajCardDelete").addEventListener("click", (e) => {
      e.stopPropagation();
      handleDeleteAnnotation(annotationData.id, anchor);
    });
  }

  /* ═══════════════════════════════════════════════
     9. EDIT & DELETE ANNOTATIONS
     ═══════════════════════════════════════════════ */
  function handleEditAnnotation(annotationData, anchor) {
    const currentNote = annotationData.note || "";
    const newNote = prompt("✏️ تعديل الملاحظة:", currentNote);

    if (newNote === null) return;

    chrome.runtime.sendMessage(
      {
        action: "updateAnnotation",
        id: annotationData.id,
        payload: { note: newNote },
      },
      (res) => {
        if (res && res.success) {
          annotationData.note = newNote;
          anchor.dataset.annotationData = JSON.stringify({ ...annotationData, note: newNote });

          const idx = currentAnnotations.findIndex((a) => a.id === annotationData.id);
          if (idx !== -1) currentAnnotations[idx].note = newNote;
          updateLocalCache(currentAnnotations);

          showTooltipCard(anchor, annotationData);
          showToast("✅ تم تعديل الملاحظة بنجاح", "success");
        } else {
          showToast("❌ خطأ في التعديل", "error");
        }
      }
    );
  }

  function handleDeleteAnnotation(annotationId, anchor) {
    if (!confirm("🗑️ هل تريد بالتأكيد حذف هذا التظليل وملاحظته نهائياً؟")) return;

    removeTooltip();

    chrome.runtime.sendMessage(
      { action: "deleteAnnotation", id: annotationId },
      (res) => {
        if (res && res.success) {
          const marks = document.querySelectorAll(`mark.wahaj-highlight[data-annotation-id="${annotationId}"]`);
          marks.forEach((m) => {
            const textNode = document.createTextNode(m.textContent);
            m.parentNode.replaceChild(textNode, m);
          });

          currentAnnotations = currentAnnotations.filter((a) => a.id !== annotationId);
          updateLocalCache(currentAnnotations);

          showToast("🗑️ تم حذف التظليل بنجاح", "success");
        } else {
          showToast("❌ خطأ في الحذف", "error");
        }
      }
    );
  }

  /* ═══════════════════════════════════════════════
     10. OFFLINE-FIRST RESTORATION & CACHING
     ═══════════════════════════════════════════════ */
  function updateLocalCache(annotations) {
    const currentUrl = canonicalizeUrl(window.location.href);
    const cacheKey = `wahaj_cache_${currentUrl}`;
    const updateObj = {};
    updateObj[cacheKey] = annotations;
    chrome.storage.local.set(updateObj);
  }

  function applyAnnotationsToDom(annotations) {
    const list = Array.isArray(annotations) ? annotations : [];
    const validIds = new Set(list.map((a) => String(a.id)));

    // 1. Remove obsolete highlights from DOM if deleted from backend/Supabase
    const existingMarks = document.querySelectorAll("mark.wahaj-highlight");
    existingMarks.forEach((m) => {
      const markId = String(m.dataset.annotationId || "");
      if (markId && !validIds.has(markId)) {
        const textNode = document.createTextNode(m.textContent);
        m.parentNode.replaceChild(textNode, m);
      }
    });

    if (list.length === 0) return;

    // 2. Add new highlights or update existing dataset
    list.forEach((ann) => {
      const marks = document.querySelectorAll(`mark.wahaj-highlight[data-annotation-id="${ann.id}"]`);
      if (marks.length > 0) {
        marks.forEach((m) => {
          m.dataset.annotationData = JSON.stringify(ann);
        });
      } else {
        findAndHighlightCrossNodeText(ann.selected_text, ann);
      }
    });
  }

  async function restoreHighlights() {
    const currentUrl = canonicalizeUrl(window.location.href);
    const cacheKey = `wahaj_cache_${currentUrl}`;

    // 1. Instant pass from local storage cache (0ms latency, works offline or while backend loads)
    try {
      chrome.storage.local.get([cacheKey], (res) => {
        const cached = res ? res[cacheKey] : null;
        if (Array.isArray(cached) && cached.length > 0) {
          currentAnnotations = cached;
          applyAnnotationsToDom(cached);
        }
      });
    } catch (e) {}

    // 2. Network pass from backend (syncs latest annotations)
    try {
      const response = await new Promise((resolve, reject) => {
        chrome.runtime.sendMessage(
          { action: "getAnnotations", url: window.location.href },
          (res) => {
            if (chrome.runtime.lastError) {
              reject(new Error(chrome.runtime.lastError.message));
            } else if (res && res.success) {
              resolve(res.data);
            } else {
              reject(new Error("Failed to load annotations"));
            }
          }
        );
      });

      if (Array.isArray(response)) {
        currentAnnotations = response;
        updateLocalCache(response);
        applyAnnotationsToDom(response);
      }
    } catch (e) {
      // Offline fallback: cached annotations already applied
    }
  }

  /* ═══════════════════════════════════════════════
     11. MESSAGE LISTENER
     ═══════════════════════════════════════════════ */
  function setupMessageListener() {
    chrome.runtime.onMessage.addListener((message) => {
      if (message.action === "toggleHighlighting") {
        isHighlightingEnabled = message.enabled;
        if (!isHighlightingEnabled) {
          removePopup();
          removeTooltip();
        }
        showToast(
          isHighlightingEnabled ? "🌟 تم تفعيل التظليل الذكي" : "⏸️ تم إيقاف التظليل مؤقتاً",
          "success"
        );
      }

      if (message.action === "triggerAnalysis") {
        const selection = window.getSelection();
        const text = message.text || selection.toString().trim();
        if (text) {
          const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
          currentSelectedRange = range ? range.cloneRange() : null;
          const rect = range ? range.getBoundingClientRect() : { bottom: 100, left: 100 };
          showSelectionPopup(text, rect);
        }
      }
    });
  }

  /* ═══════════════════════════════════════════════
     UTILITIES
     ═══════════════════════════════════════════════ */
  function removePopup() {
    if (activePopup) {
      activePopup.remove();
      activePopup = null;
    }
  }

  function removeTooltip() {
    if (activeTooltip) {
      activeTooltip.remove();
      activeTooltip = null;
    }
  }

  function showToast(message, type = "success") {
    const existing = document.querySelector(".wahaj-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = `wahaj-toast wahaj-toast-${type} notranslate`;
    toast.setAttribute("translate", "no");
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
  }

  function getCategoryLabel(category) {
    const labels = {
      SPECIES: "🌿",
      PHENOMENON: "🔬",
      WORK: "📖",
      EVENT: "⚔️",
      CHEMICAL: "🧪",
      ANATOMY: "🫀",
      LAW_RULE: "⚖️",
      PERIOD: "⏳",
      ASTRONOMY: "🌌",
      ARTIFACT: "🏺",
      UNIVERSITY: "🏛️",
      LOCATION: "📍",
      PERSON: "👤",
      ORGANIZATION: "🏢",
      DISEASE: "🦠",
      MEDICAL_TERM: "💊",
      TECHNOLOGY: "💻",
      CONCEPT: "💡",
      FIELD: "📚",
      DATE: "📅",
      OTHER: "🏷️",
    };
    return labels[category] || "🏷️";
  }

  function getCategoryArabicName(category) {
    const names = {
      SPECIES: "كائن حي / نبات",
      PHENOMENON: "ظاهرة علمية",
      WORK: "مؤلَّف / وثيقة",
      EVENT: "حدث تاريخي",
      CHEMICAL: "مركب كيميائي",
      ANATOMY: "عضو / تشريح",
      LAW_RULE: "نظرية / قاعدة",
      PERIOD: "عصر / حقبة",
      ASTRONOMY: "جرم فلكي",
      ARTIFACT: "أداة / أثر",
      UNIVERSITY: "جامعة",
      LOCATION: "موقع جغرافي",
      PERSON: "شخص / باحث",
      ORGANIZATION: "مؤسسة / هيئة",
      DISEASE: "مرض / متلازمة",
      MEDICAL_TERM: "مصطلح طبي",
      TECHNOLOGY: "تقنية",
      CONCEPT: "مفهوم علمي",
      FIELD: "حقل وتخصص",
      DATE: "تاريخ / زمن",
      OTHER: "كيان علمي",
    };
    return names[category] || category;
  }

  init();
})();
