-- 002_rls.sql
-- Row Level Security (RLS) policies for user data isolation and knowledge sharing

alter table public.pages               enable row level security;
alter table public.annotations         enable row level security;
alter table public.annotation_entities enable row level security;
alter table public.analysis_runs       enable row level security;
alter table public.entity_corrections  enable row level security;
alter table public.kb_entities         enable row level security;
alter table public.entity_words        enable row level security;
alter table public.api_usage           enable row level security;

-- Drop existing policies if re-running
drop policy if exists own_select on public.pages;
drop policy if exists own_select on public.annotations;
drop policy if exists own_select on public.annotation_entities;
drop policy if exists own_select on public.analysis_runs;
drop policy if exists own_select on public.entity_corrections;
drop policy if exists read_kb on public.kb_entities;
drop policy if exists read_words on public.entity_words;

-- User private tables: Users can only query their own records
create policy own_select on public.pages               for select using (user_id = auth.uid());
create policy own_select on public.annotations         for select using (user_id = auth.uid());
create policy own_select on public.annotation_entities for select using (user_id = auth.uid());
create policy own_select on public.analysis_runs       for select using (user_id = auth.uid());
create policy own_select on public.entity_corrections  for select using (user_id = auth.uid());

-- Shared Knowledge Base: Authenticated researchers can read entities and roots
create policy read_kb    on public.kb_entities for select to authenticated using (true);
create policy read_words on public.entity_words for select to authenticated using (true);
