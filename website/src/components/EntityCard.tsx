import { typeInfo } from '@/config/entityTypes';
import type { LibraryItem } from '@/types';

export default function EntityCard({ item, onDelete }: { item: LibraryItem; onDelete: (i: LibraryItem) => void }) {
  const t = typeInfo(item.type);
  return (
    <article style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 18, display: 'grid', gap: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ background: t.bg, color: t.color, borderRadius: 999, padding: '2px 12px', fontSize: 12, fontWeight: 700 }}>{item.label_ar || t.label}</span>
        <button onClick={() => onDelete(item)} title="حذف" aria-label="حذف"
          style={{ border: 0, background: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 16 }}>🗑️</button>
      </div>

      <h3 style={{ fontSize: 19, fontWeight: 800, color: 'var(--ink)' }}>{item.text}</h3>

      {item.root && (
        <div style={{ fontSize: 13, color: 'var(--muted)' }}>
          الجذر اللغوي: <strong style={{ color: 'var(--ink)' }}>{item.root}</strong>
        </div>
      )}

      {item.note && (
        <div style={{ background: 'var(--note-bg)', border: '1px solid var(--note-border)', borderRadius: 10, padding: '8px 12px', fontSize: 13, color: 'var(--ink)' }}>
          📝 {item.note}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--muted)', direction: 'ltr' }}>
        <span>{item.created_at?.slice(0, 10)}</span>
        <span>{item.source}</span>
      </div>
    </article>
  );
}
