# موقع حاشية (Website)

الواجهة التعريفية لمشروع **حاشية**، وفيها صفحة الهبوط وتسجيل الدخول والتسجيل.
الموقع مشروع Vite + React مستقل داخل مجلد `website/`، ولا علاقة له بكود الإضافة في `src/` بجذر المشروع.

## التقنيات

- React + Vite
- react-router-dom (التنقل بين الصفحات)
- ESLint

## التشغيل

```bash
git clone <رابط الريبو>
cd Annotation
git checkout feature/website
cd website
npm install
npm run dev
```

افتح الرابط الذي يظهر في التيرمنال (غالباً `http://localhost:5173`).

أوامر أخرى:

```bash
npm run build     # بناء النسخة النهائية في dist/
npm run preview   # تجربة النسخة المبنية محلياً
npm run lint      # فحص الكود
```

## هيكل المجلدات

```
website/
├── index.html          # lang="ar" dir="rtl" + الخط العربي
├── public/             # الصور والأيقونات الثابتة
└── src/
    ├── main.jsx        # نقطة البداية
    ├── App.jsx         # الـ Routes
    ├── pages/          # Home, Login, Register
    ├── components/     # Navbar, Hero, Steps, ToolsGrid, CtaBanner, Footer
    └── services/       # دوال التواصل مع الـ API
```

## أقسام الصفحة الرئيسية وتوزيع الشغل

عدّلوا الأسماء حسب الاتفاق بينكم:

| الجزء | الملف | المسؤول |
|-------|-------|---------|
| Navbar + Footer | `components/Navbar.jsx`, `Footer.jsx` | |
| Hero | `components/Hero.jsx` | |
| من النص إلى المعرفة (3 خطوات) | `components/Steps.jsx` | |
| أدوات صغيرة، أثر كبير | `components/ToolsGrid.jsx` | |
| CTA + تجميع الصفحة الرئيسية | `components/CtaBanner.jsx`, `pages/Home.jsx` | |
| تسجيل الدخول والتسجيل | `pages/Login.jsx`, `pages/Register.jsx` | |

## قواعد التصميم

- الموقع عربي بالكامل: `dir="rtl"` و`lang="ar"`.
- الخط: IBM Plex Sans Arabic.
- الألوان معرّفة كمتغيرات CSS في `src/index.css` (أزرق غامق للأساسي وأصفر للتظليل). استخدموا المتغيرات ولا تكتبوا الألوان مباشرة في المكوّنات.
- أبقوا كل مكوّن في ملف مستقل حتى لا تتعارض التعديلات.

## طريقة العمل على Git

1. الفرع الأساسي للموقع هو `feature/website`. **لا تشتغلوا عليه مباشرة.**
2. قبل أي شغل، حدّثوا نسختكم:
   ```bash
   git checkout feature/website
   git pull origin feature/website
   ```
3. افتحوا فرعاً خاصاً بشغلكم:
   ```bash
   git checkout -b feature/website-navbar
   ```
4. اعملوا كوميتات صغيرة بوصف واضح:
   ```bash
   git add .
   git commit -m "Add Navbar component"
   ```
5. ارفعوا الفرع:
   ```bash
   git push -u origin feature/website-navbar
   ```
6. افتحوا Pull Request على GitHub: `base: feature/website` و`compare: فرعكم`، واطلبوا مراجعة من زميل قبل الدمج.

### تجنّب التعارضات

- كل شخص يعدّل على ملفاته فقط حسب الجدول أعلاه.
- ملفات `App.jsx` و`index.css` و`package.json` مشتركة، فأخبروا الفريق قبل تعديلها.
- لا تثبّتوا حزماً جديدة دون إعلام الفريق، لأنها تعدّل `package-lock.json`.

## متغيرات البيئة

- لا ترفعوا ملف `.env` أبداً (مضاف في `.gitignore`).
- أنشئوا ملف `.env.example` فيه أسماء المتغيرات بدون قيم، مثل:
  ```
  VITE_API_URL=
  ```
- أي متغير يبدأ بـ `VITE_` يظهر في كود المتصفح للجميع، فلا تضعوا فيه مفاتيح سرية.

## ملاحظة

مجلدا `src/` و`api/` في جذر المشروع خاصان بالإضافة والـ backend ولا يتم تعديلهما من شغل الموقع.