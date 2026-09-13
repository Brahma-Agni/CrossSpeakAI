-- Cross Speak AI: approved-term embeddings and atomic admin review actions.

create extension if not exists vector with schema extensions;

alter table public.approved_terms
    add column if not exists embedding extensions.vector(384);
alter table public.approved_terms
    alter column embedding set not null;

create index if not exists approved_terms_embedding_hnsw_idx
    on public.approved_terms
    using hnsw (embedding vector_cosine_ops);

create policy "approved_terms_admin_read_all"
on public.approved_terms for select to authenticated
using ((select private.is_admin()));

create or replace function public.match_approved_terms(
    query_embedding extensions.vector(384),
    match_threshold double precision default 0.45,
    match_count integer default 3
)
returns table (
    id uuid,
    term text,
    category text,
    meaning text,
    translation text,
    example text,
    context text,
    similarity double precision
)
language sql
stable
set search_path = ''
as $$
    select
        approved.id,
        approved.term,
        approved.category,
        approved.meaning,
        approved.translation,
        approved.example,
        approved.context,
        1 - (
            approved.embedding OPERATOR(extensions.<=>) query_embedding
        ) as similarity
    from public.approved_terms as approved
    where approved.active
      and 1 - (
          approved.embedding OPERATOR(extensions.<=>) query_embedding
      ) >= match_threshold
    order by approved.embedding OPERATOR(extensions.<=>) query_embedding
    limit greatest(1, least(match_count, 10));
$$;

create or replace function public.approve_slang_suggestion(
    p_suggestion_id uuid,
    p_edited_term text,
    p_edited_category text,
    p_edited_meaning text,
    p_edited_translation text,
    p_edited_example text,
    p_edited_context text,
    p_new_embedding extensions.vector(384)
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    approved_id uuid;
begin
    if not private.is_admin() then
        raise exception 'Admin access required' using errcode = '42501';
    end if;

    if not exists (
        select 1 from public.slang_suggestions
        where id = p_suggestion_id and status = 'pending'
        for update
    ) then
        raise exception 'Pending suggestion not found' using errcode = 'P0002';
    end if;

    insert into public.approved_terms (
        source_suggestion_id,
        term,
        category,
        meaning,
        translation,
        example,
        context,
        embedding
    ) values (
        p_suggestion_id,
        trim(p_edited_term),
        p_edited_category,
        trim(p_edited_meaning),
        trim(p_edited_translation),
        trim(p_edited_example),
        trim(p_edited_context),
        p_new_embedding
    )
    returning id into approved_id;

    update public.slang_suggestions
    set term = trim(p_edited_term),
        category = p_edited_category,
        meaning = trim(p_edited_meaning),
        translation = trim(p_edited_translation),
        example = trim(p_edited_example),
        context = trim(p_edited_context),
        status = 'approved',
        reviewed_by = (select auth.uid()),
        reviewed_at = now(),
        rejection_reason = null
    where id = p_suggestion_id;

    return approved_id;
end;
$$;

create or replace function public.reject_slang_suggestion(
    p_suggestion_id uuid,
    p_reason text default ''
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    if not private.is_admin() then
        raise exception 'Admin access required' using errcode = '42501';
    end if;

    update public.slang_suggestions
    set status = 'rejected',
        reviewed_by = (select auth.uid()),
        reviewed_at = now(),
        rejection_reason = nullif(trim(p_reason), '')
    where id = p_suggestion_id and status = 'pending';

    if not found then
        raise exception 'Pending suggestion not found' using errcode = 'P0002';
    end if;
end;
$$;

revoke execute on function public.approve_slang_suggestion(
    uuid, text, text, text, text, text, text, extensions.vector
) from public, anon;
grant execute on function public.approve_slang_suggestion(
    uuid, text, text, text, text, text, text, extensions.vector
) to authenticated;

revoke execute on function public.reject_slang_suggestion(uuid, text)
    from public, anon;
grant execute on function public.reject_slang_suggestion(uuid, text)
    to authenticated;

grant execute on function public.match_approved_terms(
    extensions.vector, double precision, integer
) to anon, authenticated;
