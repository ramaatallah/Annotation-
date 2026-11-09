-- 005_fix_compatibility.sql
-- Ensures backward-compatibility for pre-existing tables in Supabase

-- 1. kb_entities columns
alter table public.kb_entities add column if not exists domain text;
alter table public.kb_entities add column if not exists subtype_ar text;
alter table public.kb_entities add column if not exists entity_type_ar text;
alter table public.kb_entities add column if not exists normalized_text text;

-- 2. pages columns
alter table public.pages add column if not exists domain text;
alter table public.pages add column if not exists title text default '';
alter table public.pages add column if not exists normalized_url text;

-- 3. annotation_entities columns
alter table public.annotation_entities add column if not exists user_id uuid references auth.users on delete cascade;
alter table public.annotation_entities add column if not exists words_snapshot jsonb;
alter table public.annotation_entities add column if not exists run_id uuid references public.analysis_runs;
alter table public.annotation_entities add column if not exists conflict boolean default false;
alter table public.annotation_entities add column if not exists bert_score real;
alter table public.annotation_entities add column if not exists llm_self_confidence real;
alter table public.annotation_entities add column if not exists start_offset int;
alter table public.annotation_entities add column if not exists end_offset int;

-- 4. Enable RLS and permissions
alter table public.pages enable row level security;
alter table public.annotations enable row level security;
alter table public.annotation_entities enable row level security;
alter table public.kb_entities enable row level security;
alter table public.entity_words enable row level security;
