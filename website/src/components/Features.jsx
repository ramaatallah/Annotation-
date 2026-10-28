import SectionTitle from './SectionTitle';

const features = [
  { icon: '🖍️', title: 'التظليل الذكي', text: 'تمييز دقيق للعبارات والكلمات المهمة داخل أي صفحة.' },
  { icon: '📒', title: 'ملاحظات وحفظ تلقائي', text: 'ربط كل ملاحظة بالنص المظلّل وحفظها في مكتبتك.' },
  { icon: '🏷️', title: 'استخراج الكيانات (NER)', text: 'تصنيف الأسماء والأماكن والمؤسسات تلقائيًا بالعربية.' },
  { icon: '🌱', title: 'استخراج الجذور اللغوية', text: 'إرجاع الكلمة إلى جذرها لفهم أعمق للمعنى.' },
];

export default function Features() {
  return (
    <section id="features" className="container" style={{ padding: '56px 20px 80px' }}>
      <SectionTitle title="مميزات المنصة الذكية" subtitle="أدوات متقدمة صُممت خصيصًا للباحثين والمهتمين باللغة العربية" />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}>
        {features.map((f) => (
          <article key={f.title} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 22 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: '#eef1fb', display: 'grid', placeItems: 'center', fontSize: 20, marginBottom: 12 }}>{f.icon}</div>
            <h3 style={{ fontSize: 17, marginBottom: 6 }}>{f.title}</h3>
            <p style={{ color: 'var(--muted)', fontSize: 14 }}>{f.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
