-- 003_save_rpc.sql
-- Atomic RPC function for saving annotations and their linked entities & word roots in a single transaction

create or replace function public.save_annotation_with_entities(p jsonb)
returns void language plpgsql security definer set search_path = public as $$
declare
  v_uid uuid := (p->>'user_id')::uuid;
  v_ann uuid := (p->>'annotation_id')::uuid;
  e jsonb;
  w jsonb;
  v_entity uuid;
begin
  -- 1. Insert or update the user annotation
  insert into annotations (id, user_id, page_id, selected_text, note, context_before, context_after)
  values (
    v_ann,
    v_uid,
    (p->>'page_id')::uuid,
    p->>'selected_text',
    coalesce(p->>'note', ''),
    coalesce(p->>'context_before', ''),
    coalesce(p->>'context_after', '')
  )
  on conflict (id) do update set
    note = excluded.note,
    updated_at = now()
  where annotations.user_id = v_uid;

  if not exists (select 1 from annotations where id = v_ann and user_id = v_uid) then
    raise exception 'annotation not owned by user';
  end if;

  -- 2. Clear old annotation-entity links for this annotation
  delete from annotation_entities where annotation_id = v_ann;

  -- 3. Iterate over entities
  for e in select * from jsonb_array_elements(coalesce(p->'entities', '[]'::jsonb)) loop
    v_entity := null;

    -- Upsert entity in shared KB
    select id into v_entity from kb_entities
    where normalized_text = (e->>'normalized') and entity_type = (e->>'type')
    limit 1;

    if v_entity is null then
      insert into kb_entities (entity_text, normalized_text, entity_type, entity_type_ar, subtype_ar, domain)
      values (
        e->>'text',
        e->>'normalized',
        e->>'type',
        e->>'type_ar',
        e->>'subtype_ar',
        e->>'domain'
      )
      returning id into v_entity;
    end if;

    -- Upsert word-level roots for this entity
    for w in select * from jsonb_array_elements(coalesce(e->'words', '[]'::jsonb)) loop
      begin
        insert into entity_words (
          entity_id, position, word, root, root_len, root_status,
          root_engine, engine_version, candidates, needs_review
        )
        values (
          v_entity,
          (w->>'position')::smallint,
          w->>'word',
          w->>'root',
          (w->>'root_len')::smallint,
          w->>'status',
          w->>'engine',
          w->>'engine_version',
          w->'candidates',
          coalesce((w->>'needs_review')::boolean, false)
        )
        on conflict (entity_id, position) do nothing;
      exception when others then
        null;
      end;
    end loop;

    -- Link annotation to entity
    begin
      insert into annotation_entities (
        annotation_id, entity_id, user_id, start_offset, end_offset,
        source, bert_score, llm_self_confidence, conflict, words_snapshot, run_id
      )
      values (
        v_ann,
        v_entity,
        v_uid,
        (e->>'start')::int,
        (e->>'end')::int,
        coalesce(e->>'source', 'llm'),
        (e->>'bert_score')::real,
        (e->>'llm_self_confidence')::real,
        coalesce((e->>'conflict')::boolean, false),
        e->'words',
        nullif(p->>'run_id', '')::uuid
      );
    exception when others then
      null;
    end;
  end loop;
end $$;

-- Security permissions: Accessible exclusively by the backend service role
revoke all on function public.save_annotation_with_entities(jsonb) from public, anon, authenticated;
grant execute on function public.save_annotation_with_entities(jsonb) to service_role;
