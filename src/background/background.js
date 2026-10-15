import { supabase } from "../shared/supabase.js";

// عنوان خدمة التحليل (NER). غيّريه هون بس إذا تغيّر (مثلاً رابط ngrok).
const ANALYZE_API_URL = "http://127.0.0.1:8000/analyze";

async function getCurrentUser() {
  const { data, error } = await supabase.auth.getUser();

  if (error || !data.user) {
    throw new Error("المستخدم غير مسجل الدخول إلى Supabase");
  }

  return data.user;
}

async function getOrCreatePage(userId, url, title) {
  const normalizedUrl = new URL(url);
  normalizedUrl.hash = "";
  normalizedUrl.search = "";

  const pageUrl = normalizedUrl.href;

  const { data: existingPage, error: searchError } = await supabase
    .from("pages")
    .select("id")
    .eq("user_id", userId)
    .eq("normalized_url", pageUrl)
    .maybeSingle();

  if (searchError) throw searchError;
  if (existingPage) return existingPage.id;

  const { data: newPage, error: insertError } = await supabase
    .from("pages")
    .insert({
      user_id: userId,
      url,
      normalized_url: pageUrl,
      title: title || "",
      domain: normalizedUrl.hostname,
    })
    .select("id")
    .single();

  if (insertError) throw insertError;

  return newPage.id;
}

async function saveAnnotation(message) {
  const user = await getCurrentUser();

  const pageId = await getOrCreatePage(
    user.id,
    message.url,
    message.title
  );

  const { error } = await supabase.from("annotations").upsert({
    id: message.id,
    user_id: user.id,
    page_id: pageId,
    selected_text: message.text,
    note: message.note,
    context_before: message.contextBefore || "",
    context_after: message.contextAfter || "",
    anchor_data: { groupId: message.id },
  });

  if (error) throw error;

  return { id: message.id };
}

async function updateAnnotation(message) {
  const user = await getCurrentUser();

  const { error } = await supabase
    .from("annotations")
    .update({
      note: message.note,
      updated_at: new Date().toISOString(),
    })
    .eq("id", message.id)
    .eq("user_id", user.id);

  if (error) throw error;

  return { id: message.id };
}

async function deleteAnnotation(message) {
  const user = await getCurrentUser();

  const { error } = await supabase
    .from("annotations")
    .delete()
    .eq("id", message.id)
    .eq("user_id", user.id);

  if (error) throw error;

  return { id: message.id };
}

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

  const { data, error } = await supabase
    .from("annotations")
    .select("id, selected_text, note")
    .eq("user_id", user.id)
    .eq("page_id", page.id);

  if (error) throw error;

  return (data || []).map((annotation) => ({
    id: annotation.id,
    text: annotation.selected_text,
    note: annotation.note || "",
  }));
}

// تحليل النص (NER) عبر الـ background بدل الـ content script
async function analyzeText(message) {
  if (typeof message.text !== "string" || !message.text.trim()) {
    return [];
  }

  const response = await fetch(ANALYZE_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: message.text }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  return data.entities || [];
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "SUPABASE_ANONYMOUS_SIGN_IN") {
    supabase.auth.signInAnonymously()
      .then(({ data, error }) => {
        if (error) throw error;

        sendResponse({
          success: true,
          userId: data.user?.id ?? null,
        });
      })
      .catch((error) => {
        sendResponse({
          success: false,
          error: error.message || "Unknown Supabase error",
        });
      });

    return true;
  }

  const actions = {
    SUPABASE_SAVE_ANNOTATION: saveAnnotation,
    SUPABASE_UPDATE_ANNOTATION: updateAnnotation,
    SUPABASE_DELETE_ANNOTATION: deleteAnnotation,
    SUPABASE_GET_ANNOTATIONS: getPageAnnotations,
    ANALYZE_TEXT: analyzeText,
  };

  const action = actions[message?.type];

  if (!action) return;

  action(message)
    .then((data) => sendResponse({ success: true, data }))
    .catch((error) => {
      console.error("Background action error:", message?.type, error);

      sendResponse({
        success: false,
        error: error.message || "Unknown error",
      });
    });

  return true;
});