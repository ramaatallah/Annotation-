import "./content.css";

let annotationEnabled = false;

chrome.storage.local.get(["annotationEnabled"], (result) => {
  annotationEnabled = result.annotationEnabled ?? false;
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.annotationEnabled) {
    annotationEnabled = changes.annotationEnabled.newValue ?? false;
  }
});

console.log("Annotation content script loaded");
restoreSavedAnnotations();

document.addEventListener("mouseup", () => {
  if (!annotationEnabled) {
    return;
  }

  const selection = window.getSelection();

  if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
    return;
  }

  const selectedText = selection.toString().trim();

  if (!selectedText) {
    return;
  }

  const range = selection.getRangeAt(0);

  console.log("Selected text:", selectedText);

  const highlightedNodes = highlightSelection(range);

  if (highlightedNodes.length === 0) {
    return;
  }

  showNotePopup(range, highlightedNodes, selectedText);

  selection.removeAllRanges();
});


function highlightSelection(range, savedGroupId = crypto.randomUUID()) {
  const textNodes = getTextNodesInRange(range);
  const highlightedNodes = [];
  const groupId = savedGroupId;
  textNodes.forEach((textNode) => {
    const nodeRange = document.createRange();

    nodeRange.selectNodeContents(textNode);

    if (textNode === range.startContainer) {
      nodeRange.setStart(textNode, range.startOffset);
    }

    if (textNode === range.endContainer) {
      nodeRange.setEnd(textNode, range.endOffset);
    }

    if (nodeRange.collapsed) {
      return;
    }

    const fragment = nodeRange.extractContents();
    const highlight = document.createElement("span");

    highlight.className = "annotation-highlight";
    highlight.dataset.annotationGroup = groupId;

    highlight.appendChild(fragment);
    nodeRange.insertNode(highlight);

    highlightedNodes.push(highlight);
  });

  return highlightedNodes;
}


function getTextNodesInRange(range) {
  const textNodes = [];

  let root = range.commonAncestorContainer;

  if (root.nodeType === Node.TEXT_NODE) {
    root = root.parentNode;
  }

  const walker = document.createTreeWalker(
    root,
    NodeFilter.SHOW_TEXT
  );

  let currentNode;

  while ((currentNode = walker.nextNode())) {
    if (range.intersectsNode(currentNode)) {
      textNodes.push(currentNode);
    }
  }

  return textNodes;
}

function showNotePopup(range, highlightedNodes, selectedText) {
  removeExistingNotePopup();

  const popup = document.createElement("div");

  popup.className = "annotation-note-popup";

  popup.innerHTML = `
    <div class="annotation-note-popup-title">
      إضافة ملاحظة
    </div>

    <textarea
      placeholder="اكتب ملاحظتك هنا..."
      aria-label="Note"
    ></textarea>

    <div class="annotation-note-popup-actions">
      <button
        type="button"
        class="annotation-note-save"
      >
        حفظ
      </button>

      <button
        type="button"
        class="annotation-note-cancel"
      >
        إلغاء
      </button>
    </div>
  `;

  document.documentElement.appendChild(popup);

  positionNotePopup(popup, range);

  const textarea = popup.querySelector("textarea");
  const saveButton = popup.querySelector(".annotation-note-save");
  const cancelButton = popup.querySelector(".annotation-note-cancel");

  textarea.focus();

  saveButton.addEventListener("click", () => {
    const note = textarea.value.trim();

    if (!note) {
      textarea.focus();
      return;
    }

    highlightedNodes.forEach((node) => {
  node.dataset.annotationNote = note;
  node.dataset.annotationText = selectedText;

  attachTooltip(node);
});

const groupId = highlightedNodes[0].dataset.annotationGroup;
const firstHighlight = highlightedNodes[0];
const lastHighlight = highlightedNodes[highlightedNodes.length - 1];

const contextBefore = firstHighlight
  ? firstHighlight.parentElement?.textContent
      ?.slice(0, 100) || ""
  : "";

const contextAfter = lastHighlight
  ? lastHighlight.parentElement?.textContent
      ?.slice(-100) || ""
  : "";
saveAnnotationRecord(
  groupId,
  selectedText,
  note,
  contextBefore,
  contextAfter
);

chrome.runtime.sendMessage(
  {
    type: "SUPABASE_SAVE_ANNOTATION",
    id: groupId,
    text: selectedText,
    note,
    url: location.href,
    title: document.title,
    contextBefore,
    contextAfter,
  },
  (response) => {
    if (chrome.runtime.lastError) {
      console.error(
        "Supabase save error:",
        chrome.runtime.lastError.message
      );
      return;
    }

    if (!response?.success) {
      console.error("Supabase save error:", response?.error);
      return;
    }

    console.log("Annotation saved to Supabase:", response.data);
  }
);

    console.log("Annotation saved temporarily:", {
      text: selectedText,
      note,
    });

    popup.remove();
  });

  cancelButton.addEventListener("click", () => {
    highlightedNodes.forEach((node) => {
      const parent = node.parentNode;

      if (!parent) {
        return;
      }

      while (node.firstChild) {
        parent.insertBefore(node.firstChild, node);
      }

      parent.removeChild(node);
      parent.normalize();
    });

    popup.remove();
  });
}

function positionNotePopup(popup, range) {
  const rect = range.getBoundingClientRect();

  const popupWidth = 320;
  const popupHeight = 180;
  const margin = 10;

  let left = rect.left;

  if (left + popupWidth > window.innerWidth - margin) {
    left = window.innerWidth - popupWidth - margin;
  }

  if (left < margin) {
    left = margin;
  }

  let top = rect.bottom + margin;

  if (top + popupHeight > window.innerHeight - margin) {
    top = rect.top - popupHeight - margin;
  }

  if (top < margin) {
    top = margin;
  }

  popup.style.left = `${left}px`;
  popup.style.top = `${top}px`;
}

function removeExistingNotePopup() {
  const existingPopup = document.querySelector(
    ".annotation-note-popup"
  );

  if (existingPopup) {
    existingPopup.remove();
  }
}

function attachTooltip(highlightNode) {
  highlightNode.addEventListener("mouseenter", () => {
    const note = highlightNode.dataset.annotationNote;
    const selectedText = highlightNode.dataset.annotationText;

    if (!note || !selectedText) {
      return;
    }

    showTooltip(highlightNode, selectedText, note);
  });

  highlightNode.addEventListener("mouseleave", () => {
    const tooltip = document.querySelector(".annotation-tooltip");

    if (!tooltip) {
      return;
    }

    setTimeout(() => {
      if (
        !tooltip.matches(":hover") &&
        !highlightNode.matches(":hover")
      ) {
        removeTooltip();
      }
    }, 150);
  });
}

function showTooltip(highlightNode, selectedText, note) {
  removeTooltip();

  const tooltip = document.createElement("div");

  tooltip.className = "annotation-tooltip";

  tooltip.innerHTML = `
    <div class="annotation-tooltip-text-title">
      النص المحدد
    </div>

    <div class="annotation-tooltip-text">
      ${escapeHtml(selectedText)}
    </div>

    <div class="annotation-tooltip-note-title">
      الملاحظة
    </div>

    <div class="annotation-tooltip-note">
      ${escapeHtml(note)}
    </div>
    
    <div class="annotation-tooltip-entities-title">
      الكيانات والتصنيفات
    </div>

    <div class="annotation-tooltip-entities">
      جاري تحليل النص...
    </div>

   
<div class="annotation-tooltip-actions">
  <button
    type="button"
    class="annotation-tooltip-edit"
  >
    تعديل الملاحظة
  </button>

  <button
    type="button"
    class="annotation-tooltip-remove"
  >
    إزالة التحديد
  </button>
</div>

  `;

  document.documentElement.appendChild(tooltip);

  
  positionTooltip(tooltip, highlightNode);

  tooltip.addEventListener("mouseleave", () => {
    setTimeout(() => {
      if (
        !tooltip.matches(":hover") &&
        !highlightNode.matches(":hover")
      ) {
        removeTooltip();
      }
    }, 150);
  });

 
const editButton = tooltip.querySelector(
  ".annotation-tooltip-edit"
);

const removeButton = tooltip.querySelector(
  ".annotation-tooltip-remove"
);

editButton.addEventListener("click", (event) => {
  event.stopPropagation();

  showEditNotePopup(
    highlightNode,
    selectedText,
    highlightNode.dataset.annotationNote
  );
});

removeButton.addEventListener("click", (event) => {
  event.stopPropagation();

  removeHighlight(highlightNode);
});

}

function deleteAnnotationNote(highlightNode) {
  highlightNode.dataset.annotationNote = "";

  removeTooltip();

  console.log("Annotation note deleted");
}

function showEditNotePopup(highlightNode, selectedText, currentNote) {
  removeTooltip();
  removeExistingNotePopup();

  const popup = document.createElement("div");

  popup.className = "annotation-note-popup";

  popup.innerHTML = `
    <div class="annotation-note-popup-title">
      تعديل الملاحظة
    </div>

    <textarea
      aria-label="Note"
    ></textarea>

    <div class="annotation-note-popup-actions">
      <button
        type="button"
        class="annotation-note-save"
      >
        حفظ
      </button>

      <button
        type="button"
        class="annotation-note-cancel"
      >
        إلغاء
      </button>
    </div>
  `;

  document.documentElement.appendChild(popup);

  const textarea = popup.querySelector("textarea");
  const saveButton = popup.querySelector(".annotation-note-save");
  const cancelButton = popup.querySelector(".annotation-note-cancel");

  textarea.value = currentNote;
  textarea.focus();

  saveButton.addEventListener("click", () => {
    const newNote = textarea.value.trim();

    if (!newNote) {
      textarea.focus();
      return;
    }

   const groupId = highlightNode.dataset.annotationGroup;

document
  .querySelectorAll(".annotation-highlight")
  .forEach((node) => {
    if (node.dataset.annotationGroup === groupId) {
      node.dataset.annotationNote = newNote;
    }
  });

updateAnnotationRecord(groupId, newNote);
chrome.runtime.sendMessage(
  {
    type: "SUPABASE_UPDATE_ANNOTATION",
    id: groupId,
    note: newNote,
  },
  (response) => {
    if (chrome.runtime.lastError) {
      console.error(
        "Supabase update error:",
        chrome.runtime.lastError.message
      );
      return;
    }

    if (!response?.success) {
      console.error("Supabase update error:", response?.error);
      return;
    }

    console.log("Annotation updated in Supabase:", response.data);
  }
);
popup.remove();

    console.log("Annotation note updated:", {
      text: selectedText,
      note: newNote,
    });
  });

  cancelButton.addEventListener("click", () => {
    popup.remove();
  });

  positionEditPopup(popup, highlightNode);
}
function positionEditPopup(popup, highlightNode) {
  const rect = highlightNode.getBoundingClientRect();

  const popupWidth = 320;
  const popupHeight = 180;
  const margin = 10;

  let left = rect.left;

  if (left + popupWidth > window.innerWidth - margin) {
    left = window.innerWidth - popupWidth - margin;
  }

  if (left < margin) {
    left = margin;
  }

  let top = rect.bottom + margin;

  if (top + popupHeight > window.innerHeight - margin) {
    top = rect.top - popupHeight - margin;
  }

  if (top < margin) {
    top = margin;
  }

  popup.style.left = `${left}px`;
  popup.style.top = `${top}px`;
}

function positionTooltip(tooltip, highlightNode) {
  const rect = highlightNode.getBoundingClientRect();

  const tooltipWidth = 300;
  const tooltipHeight = tooltip.offsetHeight;
  const margin = 10;

  let left = rect.left;

  if (left + tooltipWidth > window.innerWidth - margin) {
    left = window.innerWidth - tooltipWidth - margin;
  }

  if (left < margin) {
    left = margin;
  }

  let top = rect.bottom + margin;

  if (top + tooltipHeight > window.innerHeight - margin) {
    top = rect.top - tooltipHeight - margin;
  }

  if (top < margin) {
    top = margin;
  }

  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function removeTooltip() {
  const existingTooltip = document.querySelector(
    ".annotation-tooltip"
  );

  if (existingTooltip) {
    existingTooltip.remove();
  }
}

function escapeHtml(value) {
  const div = document.createElement("div");

  div.textContent = value;

  return div.innerHTML;
}





function removeHighlight(highlightNode) {
  removeTooltip();

  const groupId = highlightNode.dataset.annotationGroup;

  // حذف التحديد من التخزين الدائم
  deleteAnnotationRecord(groupId);
  
chrome.runtime.sendMessage(
  {
    type: "SUPABASE_DELETE_ANNOTATION",
    id: groupId,
  },
  (response) => {
    if (chrome.runtime.lastError) {
      console.error(
        "Supabase delete error:",
        chrome.runtime.lastError.message
      );
      return;
    }

    if (!response?.success) {
      console.error("Supabase delete error:", response?.error);
      return;
    }

    console.log("Annotation deleted from Supabase:", response.data);
  }
);

  const highlights = groupId
    ? Array.from(
        document.querySelectorAll(".annotation-highlight")
      ).filter(
        (node) =>
          node.dataset.annotationGroup === groupId
      )
    : [highlightNode];

  highlights.forEach((highlight) => {
    const parent = highlight.parentNode;

    if (!parent) {
      return;
    }

    while (highlight.firstChild) {
      parent.insertBefore(
        highlight.firstChild,
        highlight
      );
    }

    parent.removeChild(highlight);
    parent.normalize();
  });

  console.log("Complete highlight group removed");
}


function getPageStorageKey() {
  return `annotations:${location.href}`;
}


function getPageAnnotations(callback) {
  chrome.runtime.sendMessage(
    {
      type: "SUPABASE_GET_ANNOTATIONS",
      url: location.href,
    },
    (response) => {
      if (chrome.runtime.lastError) {
        console.error(
          "Supabase fetch error:",
          chrome.runtime.lastError.message
        );
        callback([]);
        return;
      }

      if (!response?.success) {
        console.error("Supabase fetch error:", response?.error);
        callback([]);
        return;
      }

      callback(response.data || []);
    }
  );
}


function savePageAnnotations(annotations, callback = () => {}) {
  const key = getPageStorageKey();

  chrome.storage.local.set(
    { [key]: annotations },
    callback
  );
}


function saveAnnotationRecord(
  groupId,
  text,
  note,
  contextBefore = "",
  contextAfter = ""
) {
  getPageAnnotations((annotations) => {
    const updated = annotations.filter(
      (item) => item.id !== groupId
    );

    updated.push({
      id: groupId,
      text,
      note,
      url: location.href,
      contextBefore,
      contextAfter,
    });

    savePageAnnotations(updated, () => {
      console.log("Annotation stored successfully");
    });
  });
}


function updateAnnotationRecord(groupId, newNote) {
  getPageAnnotations((annotations) => {
    const updated = annotations.map((item) =>
      item.id === groupId
        ? { ...item, note: newNote }
        : item
    );

    savePageAnnotations(updated);
  });
}

function deleteAnnotationRecord(groupId) {
  getPageAnnotations((annotations) => {
    const updated = annotations.filter(
      (item) => item.id !== groupId
    );

    savePageAnnotations(updated);
  });
}



function findTextRange(searchText) {
  if (typeof searchText !== "string" || !searchText || !document.body) {
    return null;
  }

  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        const parent = node.parentElement;

        if (
          !node.nodeValue ||
          !parent ||
          parent.closest(
            "script, style, noscript, textarea, input, " +
            "button, select, option, " +
            ".annotation-highlight, " +
            ".annotation-note-popup, .annotation-tooltip"
          )
        ) {
          return NodeFilter.FILTER_REJECT;
        }

        return NodeFilter.FILTER_ACCEPT;
      },
    }
  );

  const segments = [];
  let fullText = "";
  let node;

  while ((node = walker.nextNode())) {
    const start = fullText.length;
    fullText += node.nodeValue;

    segments.push({
      node,
      start,
      end: fullText.length,
    });
  }

  function normalizeWithMap(value) {
    let normalized = "";
    const map = [];

    for (let i = 0; i < value.length; i++) {
      const char = value[i];

      // تجاهل المسافات وعلامات الترقيم في البحث.
      if (/[\s\p{P}\p{S}]/u.test(char)) {
        continue;
      }

      normalized += char;
      map.push(i);
    }

    return { normalized, map };
  }

  const source = normalizeWithMap(fullText);
  const target = normalizeWithMap(searchText);

  if (!target.normalized) {
    return null;
  }

  const index = source.normalized.indexOf(target.normalized);

  if (index === -1) {
    console.warn("Saved annotation text not found.", {
      savedLength: searchText.length,
      pageTextLength: fullText.length,
      savedStart: searchText.slice(0, 100),
    });

    return null;
  }

  const originalStart = source.map[index];
  const originalEnd =
    source.map[index + target.normalized.length - 1] + 1;

  function pointAt(offset, isEnd = false) {
    const segment = segments.find((item) =>
      isEnd
        ? offset > item.start && offset <= item.end
        : offset >= item.start && offset < item.end
    );

    if (!segment) {
      return null;
    }

    return {
      node: segment.node,
      offset: offset - segment.start,
    };
  }

  const start = pointAt(originalStart);
  const end = pointAt(originalEnd, true);

  if (!start || !end) {
    return null;
  }

  const range = document.createRange();
  range.setStart(start.node, start.offset);
  range.setEnd(end.node, end.offset);

  return range;
}





function restoreSavedAnnotations() {
  getPageAnnotations((annotations) => {
    console.log("Annotations to restore:", annotations.length);

    annotations.forEach((annotation) => {
      if (
        !annotation ||
        typeof annotation.text !== "string" ||
        !annotation.text.trim()
      ) {
        console.warn("Invalid saved annotation:", annotation);
        return;
      }

      const alreadyRestored = document.querySelector(
        `.annotation-highlight[data-annotation-group="${annotation.id}"]`
      );

      if (alreadyRestored) {
        return;
      }

      const range = findTextRange(annotation.text);

      if (!range) {
        console.warn(
          "Could not restore annotation:",
          annotation.text.slice(0, 100)
        );
        return;
      }

      const nodes = highlightSelection(range, annotation.id);

      nodes.forEach((highlight) => {
        highlight.dataset.annotationNote = annotation.note || "";
        highlight.dataset.annotationText = annotation.text;

        attachTooltip(highlight);
      });

      console.log("Restored annotation:", annotation.id, nodes.length);
    });

    console.log("Saved annotations restoration finished.");
  });
}

