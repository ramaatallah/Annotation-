// صفحة "عن المشروع": بطاقة تعريف + فريق العمل والمطورون
// لإضافة/تعديل عضو: عدّل مصفوفة TEAM تحت (supervisor: true بيعطيه الشكل الأصفر المميّز)

const TEAM = [
  { name: 'سيرين نجار', role: 'علم حاسوب', badge: 'جامعة النجاح الوطنية' },
  { name: 'رهف داوود', role: 'علم حاسوب', badge: 'جامعة النجاح الوطنية' },
  { name: 'راما عطاالله', role: 'علم حاسوب', badge: 'جامعة النجاح الوطنية' },
  { name: 'د. أمجد هواش', role: 'مشرف المشروع - الإشراف الأكاديمي', badge: 'قسم علم الحاسوب', supervisor: true },
];

const GOLD = '#f1c75b';

// أول حرف من الاسم (نتجاوز "د." للمشرف)
const initial = (name) => name.replace(/^د\.\s*/, '').charAt(0);

// أيقونة قبعة التخرج (SVG مضمّن، ما بتحتاج مكتبة)
function GradCapIcon() {
  return (
    <svg width="64" height="64" viewBox="0 0 64 64" fill="#b45309" xmlns="http://www.w3.org/2000/svg">
      <path d="M32 9 62 24 32 39 2 24Z" />
      <path d="M15 34v11c0 5 8.5 9 17 9s17-4 17-9V34L32 43Z" />
      <rect x="54" y="26" width="3.2" height="19" rx="1.6" />
      <path d="M52.5 44h6.2l1.6 11h-9.4Z" />
    </svg>
  );
}

function MemberCard({ m }) {
  const sup = !!m.supervisor;
  return (
    <article
      style={{
        position: 'relative', overflow: 'hidden', textAlign: 'center',
        background: sup ? '#fffdf5' : 'var(--surface)',
        border: `1px solid ${sup ? '#f4dc8e' : 'var(--border)'}`,
        borderRadius: 24, padding: '28px 18px 24px',
        boxShadow: '0 4px 14px rgba(27,37,71,.05)',
      }}
    >
      {sup && <div style={{ position: 'absolute', top: 0, insetInline: 0, height: 5, background: GOLD }} />}

      <div
        aria-hidden="true"
        style={{
          width: 92, height: 92, margin: '0 auto 18px', borderRadius: '50%',
          display: 'grid', placeItems: 'center', fontSize: 38, fontWeight: 800,
          background: sup ? '#fdf0c4' : '#eaedf5',
          color: sup ? '#8a4b00' : 'var(--navy)',
          border: `2.5px solid ${sup ? '#e8a317' : 'var(--navy)'}`,
        }}
      >
        {initial(m.name)}
      </div>

      <h3 style={{ fontSize: 21, fontWeight: 800, marginBottom: 4 }}>{m.name}</h3>
      <p style={{ fontSize: 15, marginBottom: 14, color: sup ? '#8a4b00' : 'var(--muted)', fontWeight: sup ? 700 : 400 }}>{m.role}</p>
      <span
        style={{
          display: 'inline-block', fontSize: 13, padding: '3px 14px', borderRadius: 999,
          background: sup ? '#fff3d0' : '#eef0f4', color: sup ? '#8a4b00' : '#3b4468',
          border: sup ? `1px solid ${GOLD}` : '1px solid transparent',
        }}
      >
        {m.badge}
      </span>
    </article>
  );
}

export default function About() {
  return (
    <section id="about" className="container" style={{ padding: '48px 20px 96px' }}>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 44, padding: '52px 40px 48px', textAlign: 'center', boxShadow: '0 2px 10px rgba(27,37,71,.04)' }}>
        <div
          aria-hidden="true"
          style={{ width: 112, height: 112, margin: '0 auto 22px', borderRadius: 30, background: '#fef3c7', display: 'grid', placeItems: 'center' }}
        >
          <GradCapIcon />
        </div>

        <h2 style={{ fontSize: 46, fontWeight: 800, marginBottom: 6, color: 'var(--ink)' }}>مشروع تخرج جامعي متميز</h2>
        <p style={{ fontSize: 20, fontWeight: 700, color: 'var(--navy)', marginBottom: 22 }}>
          جامعة النجاح الوطنية - كلية الهندسة وتكنولوجيا المعلومات (قسم علم الحاسوب)
        </p>
        <p style={{ color: '#4b5563', fontSize: 19, lineHeight: 1.9, maxWidth: 1000, margin: '0 auto' }}>
          مشروع "منصة وهج" ينطلق من رؤية أكاديمية لخدمة المحتوى العربي على الشبكة العنكبوتية،
          من خلال تزويد الباحثين والقرّاء بأدوات حديثة تعتمد المعالجة الآلية للغة العربية
          لسهولة التحليل والتدوين.
        </p>
      </div>

      <h2 style={{ fontSize: 30, fontWeight: 800, textAlign: 'center', margin: '56px 0 32px' }}>فريق العمل والمطورون</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 24 }}>
        {TEAM.map((m) => <MemberCard key={m.name} m={m} />)}
      </div>
    </section>
  );
}
