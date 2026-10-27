import SectionTitle from './SectionTitle';

const steps = [
  { n: '١', icon: '🖍️', title: 'ظلّل أي نص عربي', text: 'حدد العبارة أو الجملة التي تهمك على أي موقع باستخدام الإضافة.' },
  { n: '٢', icon: '✍️', title: 'دوّن ملاحظاتك', text: 'أضف تعليقاتك الشخصية أو الهوامش التي تساعدك على الفهم لاحقًا.' },
  { n: '٣', icon: '🧠', title: 'استخرج الكيانات والجذور', text: 'تتعرف المنصة على الأسماء والأماكن والمؤسسات وتستخرج جذور الكلمات.' },
];

export default function HowItWorks() {
  return (
    <section id="how" className="container" style={{ padding: '56px 20px' }}>
      <SectionTitle title="كيف تعمل منصة وهج؟" subtitle="ثلاث خطوات بسيطة لتحويل قراءاتك إلى معرفة منظمة" />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 20 }}>
        {steps.map((s) => (
          <article key={s.n} style={{ position: 'relative', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 24 }}>
            <span style={{ position: 'absolute', top: 12, left: 16, fontSize: 36, fontWeight: 800, color: '#e4e7f2' }}>{s.n}</span>
            <div style={{ width: 44, height: 44, borderRadius: 10, background: '#eef1fb', display: 'grid', placeItems: 'center', fontSize: 22, marginBottom: 14 }}>{s.icon}</div>
            <h3 style={{ fontSize: 18, marginBottom: 6 }}>{s.title}</h3>
            <p style={{ color: 'var(--muted)', fontSize: 14 }}>{s.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
