-- ==============================================================================
-- حاشية / وَهَج - سكريبت تفريغ وحذف جميع جداول Supabase القديمة
-- ==============================================================================
-- يمكنكِ نسخ هذا الكود وتشغيله مباشرة داخل:
-- Supabase Dashboard -> SQL Editor -> New Query -> Run
-- ==============================================================================

-- الخيار 1 (الموصى به): تنظيف كامل وشامل لجميع الجداول والعلاقات والدوال القديمة
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

-- إعادة منح الصلاحيات الأساسية لأدوار Supabase
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO anon;
GRANT ALL ON SCHEMA public TO authenticated;
GRANT ALL ON SCHEMA public TO service_role;

-- تفعيل ملحق البحث والتطابق النصي (pg_trgm)
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;

-- تم بحمد الله! قاعدة البيانات الآن نظيفة 100% وجاهزة لبناء الجداول المطلوبة فقط لاحقاً.
