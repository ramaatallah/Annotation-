-- 004_website_view.sql
-- Helper view for frontend and researcher dashboards to query entities and their word roots

-- Ensure new columns exist on kb_entities in case the table existed previously
alter table public.kb_entities add column if not exists domain text;
alter table public.kb_entities add column if not exists subtype_ar text;
alter table public.kb_entities add column if not exists entity_type_ar text;
alter table public.kb_entities add column if not exists normalized_text text;

create or replace view public.entities_with_roots with (security_invoker = true) as
select
  e.id,
  e.entity_text,
  e.normalized_text,
  e.entity_type,
  e.entity_type_ar,
  e.subtype_ar,
  e.domain,
  array_agg(w.root order by w.position) filter (where w.root is not null) as roots,
  jsonb_agg(
    jsonb_build_object(
      'position', w.position,
      'word', w.word,
      'root', w.root,
      'status', w.root_status,
      'engine', w.root_engine,
      'needs_review', w.needs_review
    ) order by w.position
  ) as words
from public.kb_entities e
left join public.entity_words w on w.entity_id = e.id
group by e.id;
