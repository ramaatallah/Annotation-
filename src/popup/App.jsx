import { useEffect, useState } from "react";

function App() {
  const [enabled, setEnabled] = useState(false);

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

  return (
    <div>
      <h1>Annotation</h1>

      <button onClick={toggleEnabled}>
        {enabled ? "ON" : "OFF"}
      </button>
    </div>
  );
}

export default App;