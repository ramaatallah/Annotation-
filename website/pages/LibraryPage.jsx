import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchLibrary, deleteItem } from '../services/libraryService';
import { ENTITY_TYPES } from '../config/entityTypes';
import LibraryLocked from '../components/LibraryLocked';
import EntityCard from '../components/EntityCard';

export default function LibraryPage({ onLogin }) {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('ALL');

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    setError('');
    fetchLibrary(user)
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [user]);

  const visible = useMemo(() => {
    const q = query.trim();
    return items.filter(
      (i) => (filter === 'ALL' || i.type === filter) && (!q || i.text?.includes(q) || i.note?.includes(q) || i.root?.includes(q))
    );
  }, [items, query, filter]);

  async function handleDelete(item) {
    if (!window.confirm('حذف هذا العنصر من مكتبتك؟')) return;
    try {
      await deleteItem(user, item.id);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
    } catch (e) {
      setError(e.message);
    }
  }

  if (authLoading) return null;
  if (!user) return <div className="container"><LibraryLocked onLogin={onLogin} /></div>;

  const chip = (active) => ({
    font: 'inherit', fontSize: 13, cursor: 'pointer', padding: '6px 14px', borderRadius: 999,
    border: '1.5px solid ' + (active ? 'var(--navy)' : 'var(--border)'),
    background: active ? 'var(--navy)' : 'var(--surface)', color: active ? '#fff' : 'var(--ink)', fontWeight: 700,
  });

  return (
    <section className="container" style={{ padding: '32px 20px 80px' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 32, fontWeight: 800 }}>مكتبتي</h1>
        <p style={{ color: 'var(--muted)' }}>كل ما حفظته من كيانات وملاحظات في مكان واحد ({items.length} عنصر)</p>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 20 }}>
        <input
          value={query} onChange={(e) => setQuery(e.target.value)} placeholder="ابحثي في مكتبتك..."
          style={{ flex: '1 1 260px', padding: '10px 14px', borderRadius: 10, border: '1.5px solid var(--border)', font: 'inherit', background: '#fff' }}
        />
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button style={chip(filter === 'ALL')} onClick={() => setFilter('ALL')}>الكل</button>
          {Object.entries(ENTITY_TYPES).map(([key, t]) => (
            <button key={key} style={chip(filter === key)} onClick={() => setFilter(key)}>{t.label}</button>
          ))}
        </div>
      </div>

      {error && <div style={{ background: '#fdecec', color: '#b42318', borderRadius: 8, padding: '10px 14px', marginBottom: 16 }}>{error}</div>}
      {loading && <p style={{ color: 'var(--muted)' }}>جارٍ التحميل...</p>}

      {!loading && !error && visible.length === 0 && (
        <p style={{ textAlign: 'center', color: 'var(--muted)', padding: 40 }}>
          {items.length === 0 ? 'مكتبتك فارغة. ابدئي بتظليل نصوص عربية بالإضافة وحفظها هنا.' : 'لا توجد نتائج مطابقة.'}
        </p>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 18 }}>
        {visible.map((item) => <EntityCard key={item.id} item={item} onDelete={handleDelete} />)}
      </div>
    </section>
  );
}
