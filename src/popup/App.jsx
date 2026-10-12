
import { useEffect, useState } from "react";

function App() {
  const [enabled, setEnabled] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("");

  useEffect(() => {
    chrome.storage.local.get(["annotationEnabled"], (result) => {
      setEnabled(result.annotationEnabled ?? false);
    });
  }, []);

  const toggleEnabled = () => {
    setEnabled((currentValue) => {
      const newValue = !currentValue;

      chrome.storage.local.set({
        annotationEnabled: newValue,
      });

      return newValue;
    });
  };

  const testSupabaseConnection = () => {
    setConnectionStatus("جاري الاتصال...");

    chrome.runtime.sendMessage(
      { type: "SUPABASE_ANONYMOUS_SIGN_IN" },
      (response) => {
        if (chrome.runtime.lastError) {
          setConnectionStatus(
            `فشل الاتصال: ${chrome.runtime.lastError.message}`
          );
          return;
        }

        if (response?.success) {
          setConnectionStatus(
            `تم تسجيل الدخول بنجاح! ID: ${response.userId}`
          );
        } else {
          setConnectionStatus(
            `حدث خطأ: ${response?.error || "خطأ غير معروف"}`
          );
        }
      }
    );
  };

  return (
    <div>
      <h1>Annotation</h1>

      <button onClick={toggleEnabled}>
        {enabled ? "ON" : "OFF"}
      </button>

      <hr />

      <button onClick={testSupabaseConnection}>
        اختبار اتصال Supabase
      </button>

      <p>{connectionStatus}</p>
    </div>
  );
}

export default App;
