export default function SectionTitle({ title, subtitle }) {
  return (
    <div style={{ textAlign: 'center', marginBottom: 36 }}>
      <h2 style={{ fontSize: 32, fontWeight: 800 }}>{title}</h2>
      {subtitle && <p style={{ color: 'var(--muted)', fontSize: 15, marginTop: 4 }}>{subtitle}</p>}
    </div>
  );
}
