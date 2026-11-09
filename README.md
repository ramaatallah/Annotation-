# Annotation (حاشية / وَهَج)

مشروع بحثي متكامل لمعالجة اللغة العربية الأكاديمية على الويب: تظليل النصوص، واستخراج الكيانات وتصنيفها، وحساب الجذور الصرفية، وحفظ المعرفة في قاعدة بيانات سحابية.

---

## 📁 هيكل المشروع المنظّم (Monorepo Structure)

المشروع مقسم إلى وحدات واضحة ومستقلة:

```text
Annotation/
├── extension/    # إضافة متصفح Chrome (React + Vite)
├── api/          # خادم التحليل بالذكاء الاصطناعي (FastAPI + BERT + LLM + CAMeL Tools)
├── website/      # موقع الويب التعريفي ومختبر التحليل (React + Vite)
├── supabase/     # ملفات تهيئة قاعدة البيانات والـ SQL Migrations
├── package.json  # أوامر تشغيل سريعة من المجلد الرئيسي
└── README.md     # دليل المشروع
```

---

## 🚀 طريقة التشغيل

### 1. إعداد وبناء إضافة Chrome (`extension/`)

من المجلد الرئيسي، يمكنك البناء مباشرة:

```bash
# تثبيت الحزم والبناء
npm run build:extension
```

أو بالدخول إلى مجلد الإضافة:
```bash
cd extension
npm install
npm run build
```

> **تحميل الإضافة في Chrome:**
> 1. افتحي المتصفح على: `chrome://extensions/`
> 2. فعّلي **Developer mode** (أعلى اليمين).
> 3. اضغطي **Load unpacked**.
> 4. اختاري مجلد **`extension/dist`**.

---

### 2. تشغيل خادم التحليل (`api/`)

في نافذة Terminal (أو بتشغيل ملف `run_server.bat` بضغطة زر):

```bash
# تفعيل بيئة البايثون
source .venv/Scripts/activate     # أو .\.venv\Scripts\Activate.ps1 على PowerShell

# تشغيل السيرفر
cd api
uvicorn main:app --port 8000 --reload
```

---

### 3. تشغيل موقع الويب التعريفي (`website/`)

إذا أردتِ تشغيل موقع الويب التعريفي المستقل ومختبر تجربة النصوص:

```bash
npm run dev:website
# أو
cd website && npm run dev
```

يفتح على: `http://localhost:5173`.

---

## 📌 أوامر سريعة من المجلد الرئيسي

| الأمر | الوظيفة |
|---|---|
| `npm run build:extension` | بناء إضافة Chrome إلى مجلد `extension/dist` |
| `npm run dev:extension` | تشغيل الإضافة في وضع التطوير |
| `npm run build:website` | بناء موقع الويب إلى `website/dist` |
| `npm run dev:website` | تشغيل موقع الويب محلياً على المتصفح |
| `npm run reset:db` | تصفير قاعدة بيانات SQLite المحلية وحذف البيانات التجريبية |

---

## 🗄️ إدارة وتصفير قواعد البيانات

### 1. تصفير قاعدة البيانات المحلية (SQLite)
لحذف بيانات SQLite المحلية والبدء من الصفر بقاعدة نظيفة:
```bash
npm run reset:db
```
يقوم هذا الأمر بحذف ملف `api/annotations.db`، وعند تشغيل السيرفر يُنشئ جداول نظيفة وجديدة تلقائياً.

### 2. تصفير جداول Supabase في السحابة
لحذف جميع الجداول والعلاقات القديمة في مشروع Supabase:
1. افتحي لوحة تحكم [Supabase Dashboard](https://supabase.com/dashboard) ثم اختاري **SQL Editor**.
2. انسخي محتوى الملف [`supabase/drop_all_tables.sql`](file:///C:/Users/hp/Desktop/project/Annotation/supabase/drop_all_tables.sql).
3. الصقيه في المحرر واضغطي **Run**.
> **ملاحظة:** تم حفظ نسخة احتياطية من جميع المهاجرات السابقة داخل مجلد `archive/supabase-backup/`.

---

## 🔒 حماية الأسرار وقواعد Git

- لا ترفعي ملفات `.env` أو `.env.local` إطلاقاً (كلها معزولة ومحمية في `.gitignore`).
- اعملي branch لكل ميزة قبل الدمج في `main`.
