import ArchitectureDiagram from '../components/ArchitectureDiagram';

const steps = [
  { icon: '🖍️', title: '١. التظليل عبر المتصفح', text: 'يقوم المستخدم بتحديد النص المطلوب على أي صفحة ويب. تقوم إضافة Chrome بقراءة النص المظلل فوراً.' },
  { icon: '⚙️', title: '٢. الإرسال والمعالجة اللغوية', text: 'يتم إرسال النص إلى خادم FastAPI المعزز بنموذج معالجة اللغة العربية المتقدم لاستخراج الكيانات والتأكد من صيغة الجذر.' },
  { icon: '✨', title: '٣. العرض والتحكم التفاعلي', text: 'تظهر النتائج فوراً على شاشة المتصفح بقوائم ملونة تسهل القراءة وإضافة الملاحظات.' },
  // TODO: نص هذه الخطوة تقريبي، طابقيه مع التصميم النهائي
  { icon: '🔄', title: '٤. المزامنة مع منصة وهج', text: 'تُحفظ الملاحظات والكيانات في قاعدة البيانات وتظهر في مكتبتك على المنصة لتعودي إليها في أي وقت.' },
];

export default function HowItWorksPage() {
  return (
    <section className="container" style={{ padding: '40px 20px 90px' }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h1 style={{ fontSize: 36, fontWeight: 800 }}>آلية العمل والربط المعماري</h1>
        <p style={{ color: 'var(--muted)', marginTop: 4 }}>
          رحلة البيانات من لحظة تحديد النص في متصفحك إلى المعالجة والتحليل واسترجاع النتائج.
        </p>
      </div>

      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <ArchitectureDiagram />

        <ol style={{ listStyle: 'none', display: 'grid', gap: 16, marginTop: 36, paddingInlineEnd: 20, borderInlineEnd: '2px solid var(--border)' }}>
          {steps.map((s) => (
            <li key={s.title} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '18px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
                <span style={{ width: 38, height: 38, borderRadius: 10, background: 'var(--navy)', display: 'grid', placeItems: 'center', fontSize: 18 }}>{s.icon}</span>
                <h3 style={{ fontSize: 18, fontWeight: 800 }}>{s.title}</h3>
              </div>
              <p style={{ color: 'var(--muted)', fontSize: 14 }}>{s.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
