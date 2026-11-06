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
     1. INITIALIZATION
     ═══════════════════════════════════════════════ */
  async function init() {
    chrome.storage.local.get({ wahaj_enabled: true }, (res) => {
      isHighlightingEnabled = res.wahaj_enabled;
    });

    await restoreHighlights();
    setupSelectionListener();
    setupMessageListener();
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
      <div class="wahaj-selected-preview">${truncate(text, 120)}</div>
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
          if (
            node.parentElement &&
            node.parentElement.closest(".wahaj-selection-popup, .wahaj-tooltip-card, .wahaj-toast")
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
     6. CROSS-NODE TEXT SEARCH (For Restoring Highlights)
     ═══════════════════════════════════════════════ */
  function findAndHighlightCrossNodeText(searchText, annotationData) {
    const cleanSearch = searchText.replace(/\s+/g, " ").trim();
    if (!cleanSearch) return null;

    const blocks = document.querySelectorAll("p, div, li, article, section, td, th, h1, h2, h3, h4");
    for (const block of blocks) {
      if (block.closest(".wahaj-selection-popup, .wahaj-tooltip-card, .wahaj-toast")) continue;

      const blockText = block.textContent.replace(/\s+/g, " ");
      if (blockText.includes(cleanSearch)) {
        const range = createRangeForSubstring(block, cleanSearch);
        if (range) {
          return highlightRange(range, annotationData);
        }
      }
    }

    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: (node) => {
          if (node.parentElement && node.parentElement.closest(".wahaj-selection-popup, .wahaj-tooltip-card, .wahaj-toast")) {
            return NodeFilter.FILTER_REJECT;
          }
          if (node.textContent.includes(searchText)) {
            return NodeFilter.FILTER_ACCEPT;
          }
          return NodeFilter.FILTER_REJECT;
        },
      }
    );

    if (walker.nextNode()) {
      const node = walker.currentNode;
      const idx = node.textContent.indexOf(searchText);
      if (idx !== -1) {
        const range = document.createRange();
        range.setStart(node, idx);
        range.setEnd(node, idx + searchText.length);
        return highlightRange(range, annotationData);
      }
    }

    return null;
  }

  function createRangeForSubstring(container, text) {
    const walker = document.createTreeWalker(
      container,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: (node) => {
          if (
            node.parentElement &&
            node.parentElement.closest(".wahaj-selection-popup, .wahaj-tooltip-card, .wahaj-toast, .wahaj-highlight")
          ) {
            return NodeFilter.FILTER_REJECT;
          }
          return NodeFilter.FILTER_ACCEPT;
        },
      }
    );

    const nodes = [];
    const starts = [];
    let fullStr = "";

    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
      starts.push(fullStr.length);
      fullStr += walker.currentNode.textContent;
    }

    const normFull = fullStr.replace(/\s+/g, " ");
    let pos = normFull.indexOf(text);
    if (pos === -1) {
      const lead = text.substring(0, Math.min(30, text.length));
      pos = normFull.indexOf(lead);
    }
    if (pos === -1) return null;

    const targetEnd = pos + text.length;

    let startNode = null;
    let startOffset = 0;
    let endNode = null;
    let endOffset = 0;

    for (let i = 0; i < nodes.length; i++) {
      const nodeStart = starts[i];
      const nodeEnd = nodeStart + nodes[i].textContent.length;

      if (!startNode && pos >= nodeStart && pos < nodeEnd) {
        startNode = nodes[i];
        startOffset = pos - nodeStart;
      }
      if (targetEnd > nodeStart && targetEnd <= nodeEnd) {
        endNode = nodes[i];
        endOffset = targetEnd - nodeStart;
        break;
      }
    }

    if (!endNode && nodes.length > 0) {
      endNode = nodes[nodes.length - 1];
      endOffset = endNode.textContent.length;
    }

    if (startNode && endNode) {
      const range = document.createRange();
      range.setStart(startNode, startOffset);
      range.setEnd(endNode, endOffset);
      return range;
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
          const catNameAr = getCategoryArabicName(ent.category);
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
          if (!allRoots.some((existing) => existing.word === r.word)) {
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
          <div class="wahaj-root-left">
            <span class="wahaj-root-word">${r.word}</span>
            ${r.segmentation && r.segmentation !== r.word ? `<span class="wahaj-root-seg" title="التجزئة الصرفية">${r.segmentation}</span>` : ""}
          </div>
          <div class="wahaj-root-right">
            <span class="wahaj-root-arrow">◀</span>
            <span class="wahaj-root-value">${r.root || "غير محسوم"}</span>
            ${r.lemma && r.lemma !== r.word ? `<span class="wahaj-root-lemma" title="اللمة المعجمية">(${r.lemma})</span>` : ""}
            ${r.is_trilateral ? '<span class="wahaj-root-trilateral-badge">ثلاثي</span>' : (r.root && r.root.length === 4 ? '<span class="wahaj-root-quad-badge">رباعي</span>' : '<span class="wahaj-root-unresolved-badge">غير محسوم</span>')}
          </div>
        </div>
      `
        )
        .join("");

      rootsSection = `
        <div class="wahaj-card-section">
          <span class="wahaj-card-label">🔤 الجذور الصرفية الثلاثية:</span>
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

    // Assembled in the exact order requested: Header -> Text -> Note -> Entities -> Roots -> Actions
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
          showToast("🗑️ تم حذف التظليل بنجاح", "success");
        } else {
          showToast("❌ خطأ في الحذف", "error");
        }
      }
    );
  }

  /* ═══════════════════════════════════════════════
     10. RESTORE HIGHLIGHTS
     ═══════════════════════════════════════════════ */
  async function restoreHighlights() {
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

      if (Array.isArray(response) && response.length > 0) {
        currentAnnotations = response;
        response.forEach((ann) => {
          findAndHighlightCrossNodeText(ann.selected_text, ann);
        });
      }
    } catch {
      // Server offline, nothing to restore
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

  function truncate(str, maxLen) {
    if (!str) return "";
    return str.length > maxLen ? str.substring(0, maxLen) + "..." : str;
  }

  function getCategoryLabel(category) {
    const labels = {
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
    };
    return labels[category] || "🏷️";
  }

  function getCategoryArabicName(category) {
    const names = {
      UNIVERSITY: "جامعة",
      LOCATION: "موقع جغرافي",
      PERSON: "شخص / باحث",
      ORGANIZATION: "مؤسسة / هيئة",
      DISEASE: "مرض / متلازمة",
      MEDICAL_TERM: "مصطلح طبي / مناعي",
      TECHNOLOGY: "تقنية",
      CONCEPT: "مفهوم علمي",
      FIELD: "حقل وتخصص",
      DATE: "تاريخ / زمن",
    };
    return names[category] || category;
  }

  init();
})();
