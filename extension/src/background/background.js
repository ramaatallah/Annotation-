import { supabase } from "../shared/supabase.js";

// Backend API Base URL (configurable, public endpoint)
const API_BASE = "http://127.0.0.1:8000";

/**
 * Executes an authenticated fetch request to the Annotation Backend API.
 * Attaches the Supabase JWT access token in the Authorization header.
 */
async function authedFetch(path, options = {}) {
  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) {
    throw new Error("سجّل الدخول أولاً للمتابعة.");
  }

  const token = data.session.access_token;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);

  try {
    const url = `${API_BASE}${path}`;
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });

    if (!res.ok) {
      let errMsg = `API error (${res.status})`;
      try {
        const errJson = await res.json();
        errMsg = errJson.detail || errMsg;
      } catch (_) {}
      throw new Error(errMsg);
    }

    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Retrieves the current authenticated user.
 */
async function getCurrentUser() {
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) {
    throw new Error("المستخدم غير مسجل الدخول إلى Supabase");
  }
  return data.user;
}

/**
 * Text Analysis (NER & Roots via CAMeL Tools):
 * Calls backend /v1/analyze. Zero LLM keys or root rules exist on the client.
 */
async function analyzeText(message) {
  const text = (message.text || "").trim();
  if (!text) return [];

  try {
    const response = await authedFetch("/v1/analyze", {
      method: "POST",
      body: JSON.stringify({
        text,
        page_url: message.url || "",
        title: message.title || "",
      }),
    });

    const entities = response.entities || [];
    // Map to extension format expected by content scripts
    return entities.map((e) => {
      // Find primary root from CAMeL Tools disambiguation
      let primaryRoot = null;
      for (const w of e.words || []) {
        if (w.status === "found" && w.root) {
          primaryRoot = w.root;
          break;
        }
      }

      // Multi-word roots representation for UI
      const wordRoots = (e.words || [])
        .filter((w) => w.status === "found" && w.root)
        .map((w) => ({ word: w.word, root: w.root }));

      return {
        ...e,
        root: primaryRoot,
        words: e.words || [],
        word_roots: wordRoots,
        confidence: e.llm_self_confidence || e.bert_score || 0.95,
      };
    });
  } catch (err) {
    console.error("[Extension NER] Backend analyze failed:", err);
    throw err;
  }
}

/**
 * Saves annotation and all linked entities atomically via the backend API.
 */
async function saveAnnotation(message) {
  return await authedFetch("/v1/annotations", {
    method: "POST",
    body: JSON.stringify({
      id: message.id,
      url: message.url,
      title: message.title || "",
      text: message.text,
      note: message.note || "",
      contextBefore: message.contextBefore || "",
      contextAfter: message.contextAfter || "",
    }),
  });
}

/**
 * Updates annotation note atomically via the backend API.
 */
async function updateAnnotation(message) {
  return await authedFetch(`/v1/annotations/${message.id}`, {
    method: "PUT",
    body: JSON.stringify({
      note: message.note || "",
    }),
  });
}

/**
 * Deletes user annotation atomically via the backend API.
 */
async function deleteAnnotation(message) {
  return await authedFetch(`/v1/annotations/${message.id}`, {
    method: "DELETE",
  });
}

/**
 * Loads annotations for the current page under Supabase RLS.
 */
async function getPageAnnotations(message) {
  const user = await getCurrentUser();

  const pageUrl = new URL(message.url);
  pageUrl.hash = "";
  pageUrl.search = "";
  const normalizedUrl = pageUrl.href;

  const { data: page, error: pageError } = await supabase
    .from("pages")
    .select("id")
    .eq("user_id", user.id)
    .eq("normalized_url", normalizedUrl)
    .maybeSingle();

  if (pageError) throw pageError;
  if (!page) return [];

  // Query annotations
  const { data: annotations, error: annError } = await supabase
    .from("annotations")
    .select("id, selected_text, note")
    .eq("user_id", user.id)
    .eq("page_id", page.id);

  if (annError) throw annError;
  if (!annotations || annotations.length === 0) return [];

  const annotationIds = annotations.map((a) => a.id);

  // Query linked annotation entities with word snapshots
  const { data: links, error: linkErr } = await supabase
    .from("annotation_entities")
    .select("annotation_id, entity_id, start_offset, end_offset, source, words_snapshot, kb_entities(entity_text, entity_type, entity_type_ar, domain)")
    .in("annotation_id", annotationIds);

  if (linkErr) {
    console.warn("Error fetching annotation_entities:", linkErr);
  }

  const linksByAnnId = {};
  for (const l of links || []) {
    if (!linksByAnnId[l.annotation_id]) {
      linksByAnnId[l.annotation_id] = [];
    }
    const kb = l.kb_entities || {};
    const wordsSnap = l.words_snapshot || [];
    const wordRoots = wordsSnap
      .filter((w) => w.status === "found" && w.root)
      .map((w) => ({ word: w.word, root: w.root }));
    const primaryRoot = wordRoots.length > 0 ? wordRoots[0].root : null;

    linksByAnnId[l.annotation_id].push({
      text: kb.entity_text,
      type: kb.entity_type,
      type_ar: kb.entity_type_ar,
      domain: kb.domain,
      start_offset: l.start_offset,
      end_offset: l.end_offset,
      source: l.source,
      root: primaryRoot,
      words: wordsSnap,
      word_roots: wordRoots,
    });
  }

  return annotations.map((a) => ({
    id: a.id,
    text: a.selected_text,
    note: a.note || "",
    entities: linksByAnnId[a.id] || [],
  }));
}

/**
 * Researcher feedback correction submission.
 */
async function submitCorrection(message) {
  return await authedFetch("/v1/corrections", {
    method: "POST",
    body: JSON.stringify({
      annotation_entity_id: message.annotationEntityId,
      field: message.field,
      old_value: message.oldValue,
      new_value: message.newValue,
    }),
  });
}

/**
 * Handles anonymous or session sign-in test from popup.
 */
async function anonymousSignIn() {
  const { data: sessionData } = await supabase.auth.getSession();
  if (sessionData?.session?.user?.id) {
    return { userId: sessionData.session.user.id };
  }

  const { data, error } = await supabase.auth.signInAnonymously();
  if (error) throw error;
  return { userId: data.user?.id };
}

// Chrome message listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const actions = {
    ANALYZE_TEXT: analyzeText,
    SUPABASE_SAVE_ANNOTATION: saveAnnotation,
    SUPABASE_UPDATE_ANNOTATION: updateAnnotation,
    SUPABASE_DELETE_ANNOTATION: deleteAnnotation,
    SUPABASE_GET_ANNOTATIONS: getPageAnnotations,
    SUBMIT_CORRECTION: submitCorrection,
    SUPABASE_ANONYMOUS_SIGN_IN: anonymousSignIn,
  };

  const action = actions[message?.type];
  if (!action) {
    sendResponse({
      success: false,
      error: `Unsupported message type: ${message?.type}`,
    });
    return false;
  }

  action(message)
    .then((data) => sendResponse({ success: true, ...data, data }))
    .catch((error) => {
      console.error("Background action error:", message?.type, error);
      sendResponse({
        success: false,
        error: error.message || "Unknown error",
      });
    });

  return true;
});
