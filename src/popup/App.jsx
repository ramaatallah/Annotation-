
import React, { useState, useEffect } from 'react';

function App() {
  const [isEnabled, setIsEnabled] = useState(true);
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // جلب الحالة الدائمة عند فتح الـ Popup أول مرة
  useEffect(() => {
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      chrome.storage.local.get(['annotationEnabled'], (result) => {
        const savedState = result.annotationEnabled ?? true;
        setIsEnabled(savedState);
        if (savedState) {
          fetchAnalysisData();
        }
      });
    } else {
      fetchAnalysisData();
    }
  }, []);

  const fetchAnalysisData = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      setTimeout(() => {
        setEntities([
          { id: 1, name: 'أحمد', type: 'شخص', confidence: '98%', root: 'حمد' },
          { id: 2, name: 'جامعة القدس', type: 'مؤسسة', confidence: '95%', root: 'جامع / قدس' },
          { id: 3, name: 'المقالات', type: 'كلمة مفتاحية', confidence: '91%', root: 'كتب' }
        ]);
        setLoading(false);
      }, 500);
    } catch (error) {
      setErrorMessage('فشل في تحليل النص أو الاتصال بالخادم.');
      setLoading(false);
    }
  };

  const handleToggle = () => {
    const newState = !isEnabled;
    setIsEnabled(newState);
    
    // استخدام نفس المفتاح annotationEnabled لكي يستجيب content.js فوراً!
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
      chrome.storage.local.set({ annotationEnabled: newState }, () => {
        console.log('تم تحديث annotationEnabled إلى:', newState);
      });
    }

    if (newState) {
      setSuccessMessage('تم تفعيل الإضافة بنجاح');
      fetchAnalysisData();
    } else {
      setSuccessMessage('تم إيقاف الإضافة مؤقتاً');
      setEntities([]);
    }
    setTimeout(() => setSuccessMessage(''), 3000);
  };

  const handleRemoveEntity = (id) => {
    setEntities(entities.filter(item => item.id !== id));
    setSuccessMessage('تم إزالة التظليل وتحديث الملاحظات بنجاح');
    setTimeout(() => setSuccessMessage(''), 3000);
  };

  return (
    <div style={{ width: '300px', padding: '12px', fontFamily: 'Arial, sans-serif', direction: 'rtl', background: '#fff', boxSizing: 'border-box' }}>
      {/* Header & Toggle Switch */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', borderBottom: '1px solid #ddd', paddingBottom: '6px' }}>
        <h3 style={{ margin: 0, fontSize: '15px', color: '#222' }}>محلل النصوص والكيانات</h3>
        <label style={{ position: 'relative', display: 'inline-block', width: '38px', height: '20px', cursor: 'pointer' }}>
          <input type="checkbox" checked={isEnabled} onChange={handleToggle} style={{ opacity: 0, width: 0, height: 0 }} />
          <span style={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: isEnabled ? '#4CAF50' : '#ccc', transition: '.3s', borderRadius: '20px'
          }}>
            <span style={{
              position: 'absolute', content: '""', height: '14px', width: '14px', left: isEnabled ? '20px' : '4px', bottom: '3px',
              backgroundColor: 'white', transition: '.3s', borderRadius: '50%'
            }}></span>
          </span>
        </label>
      </div>

      {/* Status Messages */}
      {errorMessage && (
        <div style={{ backgroundColor: '#ffebee', color: '#c62828', padding: '6px', borderRadius: '4px', fontSize: '11px', marginBottom: '8px' }}>
          {errorMessage}
        </div>
      )}
      {successMessage && (
        <div style={{ backgroundColor: '#e8f5e9', color: '#2e7d32', padding: '6px', borderRadius: '4px', fontSize: '11px', marginBottom: '8px' }}>
          {successMessage}
        </div>
      )}

      {/* Main Content View */}
      {!isEnabled ? (
        <p style={{ color: '#666', textAlign: 'center', fontSize: '12px', margin: '15px 0' }}>الإضافة متوقفة حالياً.</p>
      ) : loading ? (
        <p style={{ color: '#555', textAlign: 'center', fontSize: '12px', margin: '15px 0' }}>جاري تحليل الصفحة...</p>
      ) : entities.length === 0 ? (
        <p style={{ color: '#666', textAlign: 'center', fontSize: '12px', margin: '15px 0' }}>لا توجد كيانات مظللة حالياً.</p>
      ) : (
        <div style={{ maxHeight: '220px', overflowY: 'auto' }}>
          {entities.map(entity => (
            <div key={entity.id} style={{
              background: '#f9f9f9', border: '1px solid #e0e0e0', borderRadius: '5px', padding: '6px 8px', marginBottom: '6px', fontSize: '11px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', color: '#333' }}>
                <span>{entity.name}</span>
                <span style={{ color: '#1976d2', background: '#e3f2fd', padding: '2px 5px', borderRadius: '3px', fontSize: '9px' }}>{entity.type}</span>
              </div>
              <div style={{ color: '#555', marginTop: '3px' }}>
                <div>الجذر: <strong>{entity.root}</strong></div>
                <div>الثقة: <strong>{entity.confidence}</strong></div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                <button 
                  onClick={() => handleRemoveEntity(entity.id)}
                  style={{ background: '#ff5252', color: '#fff', border: 'none', padding: '2px 6px', borderRadius: '3px', cursor: 'pointer', fontSize: '9px' }}>
                  إزالة التظليل
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
