-- Cross Speak AI: Add subscription plans and server-side usage quota.
-- Apply via Supabase SQL Editor or `supabase db push`.

-- ── 1. Add plan columns to profiles ──────────────────────────────────────────

alter table public.profiles
    add column if not exists plan text not null default 'free'
        check (plan in ('free', 'paid')),
    add column if not exists plan_expires_at timestamptz,
    add column if not exists user_mode text not null default 'corporate'
        check (user_mode in ('corporate', 'genz'));

-- ── 2. RLS: users read own plan; only admins promote plans ───────────────────

-- Drop policies if they already exist (idempotent re-run)
drop policy if exists "profiles_update_own_plan" on public.profiles;
drop policy if exists "profiles_admin_update" on public.profiles;

create policy "profiles_admin_update"
on public.profiles for update to authenticated
using ((select private.is_admin()))
with check ((select private.is_admin()));

-- ── 3. Function: get total translation usage for a user ──────────────────────

create or replace function public.get_translation_usage(p_user_id uuid)
returns integer
language sql
stable
security definer
set search_path = ''
as $$
    select count(*)::integer
    from public.translation_history
    where user_id = p_user_id
      and (p_user_id = (select auth.uid()) or (select private.is_admin()));
$$;

grant execute on function public.get_translation_usage(uuid) to authenticated;

-- ── 4. Function: get all conversations with their first message snippet ───────

create or replace function public.get_conversations_with_preview(p_user_id uuid)
returns table (
    id uuid,
    title text,
    created_at timestamptz,
    updated_at timestamptz,
    message_count bigint,
    last_input text
)
language sql
stable
security definer
set search_path = ''
as $$
    select
        c.id,
        c.title,
        c.created_at,
        c.updated_at,
        count(th.id) as message_count,
        (
            select th2.input_text
            from public.translation_history th2
            where th2.conversation_id = c.id
            order by th2.created_at desc
            limit 1
        ) as last_input
    from public.conversations c
    left join public.translation_history th on th.conversation_id = c.id
    where c.user_id = p_user_id
    group by c.id, c.title, c.created_at, c.updated_at
    order by c.updated_at desc;
$$;

grant execute on function public.get_conversations_with_preview(uuid) to authenticated;

-- ── 5. Useful index for quota counting ───────────────────────────────────────

create index if not exists translation_history_user_day_idx
    on public.translation_history (user_id, created_at desc);
