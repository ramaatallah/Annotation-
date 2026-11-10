import BrowserMock from './BrowserMock';

interface HeroProps {
  onTry?: () => void;
}

export default function Hero({ onTry }: HeroProps) {
  return (
    <section className="container" style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 40, alignItems: 'center', padding: '56px 20px' }}>
      <div>
        <span style={{ display: 'inline-block', background: 'var(--note-bg)', border: '1px solid var(--note-border)', color: '#8a5a00', borderRadius: 999, padding: '4px 14px', fontSize: 13, fontWeight: 700 }}>
          إضافة متصفح ذكية للتحليل اللغوي العربي
        </span>

        <h1 style={{ fontSize: 56, fontWeight: 800, margin: '16px 0', lineHeight: 1.2, color: 'var(--ink)' }}>
          ظَلّل. دوّن. <span style={{ color: 'var(--navy)' }}>افهم.</span>
        </h1>

        <p style={{ fontSize: 18, color: 'var(--muted)', maxWidth: 520, lineHeight: 1.8 }}>
          منصة وإضافة متصفح أكاديمية مخصصة للغة العربية؛ تتيح لك تظليل النصوص في أي موقع،
          واستخراج الكيانات المحددة (أسماء، أماكن، مؤسسات)، واستكشاف الجذور اللغوية، وحفظ الملاحظات بسهولة.
        </p>

        <div style={{ display: 'flex', gap: 12, margin: '28px 0 16px', flexWrap: 'wrap' }}>
          <a className="btn btn-primary" href="#">
            ثبّت الإضافة مجاناً
          </a>
          <button className="btn btn-outline" onClick={onTry}>جرّب التجربة المباشرة ←</button>
        </div>

        <div style={{ display: 'flex', gap: 18, fontSize: 13, color: 'var(--muted)' }}>
          <span>✔ يدعم المصطلحات المحلية</span>
          <span>✔ خالٍ من الإعلانات</span>
        </div>
      </div>

      <BrowserMock />
    </section>
  );
}
