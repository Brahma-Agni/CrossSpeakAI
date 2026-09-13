-- Cross Speak AI: persistent accounts, conversations, history, and slang review.
-- Apply with the Supabase SQL editor or `supabase db push`.

create schema if not exists private;

create table public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    role text not null default 'user' check (role in ('user', 'admin')),
    created_at timestamptz not null default now()
);

create table public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null default 'New conversation'
        check (char_length(title) between 1 and 120),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.translation_history (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    conversation_id uuid references public.conversations(id) on delete cascade,
    input_text text not null check (char_length(input_text) between 1 and 10000),
    output_text text not null check (char_length(output_text) between 1 and 20000),
    detected_style text not null,
    translation_direction text not null,
    terms_used jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table public.slang_suggestions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    term text not null check (char_length(term) between 1 and 100),
    category text not null check (category in ('Corporate', 'Gen Z')),
    meaning text not null check (char_length(meaning) between 1 and 1000),
    translation text not null check (char_length(translation) between 1 and 1000),
    example text not null default '' check (char_length(example) <= 2000),
    context text not null default '' check (char_length(context) <= 2000),
    status text not null default 'pending'
        check (status in ('pending', 'approved', 'rejected')),
    reviewed_by uuid references auth.users(id) on delete set null,
    reviewed_at timestamptz,
    rejection_reason text check (char_length(rejection_reason) <= 1000),
    created_at timestamptz not null default now()
);

create table public.approved_terms (
    id uuid primary key default gen_random_uuid(),
    source_suggestion_id uuid unique
        references public.slang_suggestions(id) on delete set null,
    term text not null check (char_length(term) between 1 and 100),
    category text not null check (category in ('Corporate', 'Gen Z')),
    meaning text not null check (char_length(meaning) between 1 and 1000),
    translation text not null check (char_length(translation) between 1 and 1000),
    example text not null default '' check (char_length(example) <= 2000),
    context text not null default '' check (char_length(context) <= 2000),
    active boolean not null default true,
    approved_at timestamptz not null default now()
);

create index conversations_user_created_idx
    on public.conversations (user_id, created_at desc);
create index translation_history_user_created_idx
    on public.translation_history (user_id, created_at desc);
create index translation_history_conversation_created_idx
    on public.translation_history (conversation_id, created_at desc);
create index slang_suggestions_user_created_idx
    on public.slang_suggestions (user_id, created_at desc);
create index slang_suggestions_status_created_idx
    on public.slang_suggestions (status, created_at);
create index approved_terms_active_idx
    on public.approved_terms (active);

create or replace function private.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.profiles
        where id = (select auth.uid()) and role = 'admin'
    );
$$;

create or replace function private.create_profile_for_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id) values (new.id)
    on conflict (id) do nothing;
    return new;
end;
$$;

create trigger create_profile_after_signup
after insert on auth.users
for each row execute function private.create_profile_for_new_user();

grant usage on schema private to authenticated;
grant execute on function private.is_admin() to authenticated;

alter table public.profiles enable row level security;
alter table public.conversations enable row level security;
alter table public.translation_history enable row level security;
alter table public.slang_suggestions enable row level security;
alter table public.approved_terms enable row level security;

create policy "profiles_select_own_or_admin"
on public.profiles for select to authenticated
using ((select auth.uid()) = id or (select private.is_admin()));

create policy "conversations_select_own"
on public.conversations for select to authenticated
using ((select auth.uid()) = user_id);
create policy "conversations_insert_own"
on public.conversations for insert to authenticated
with check ((select auth.uid()) = user_id);
create policy "conversations_update_own"
on public.conversations for update to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
create policy "conversations_delete_own"
on public.conversations for delete to authenticated
using ((select auth.uid()) = user_id);

create policy "history_select_own"
on public.translation_history for select to authenticated
using ((select auth.uid()) = user_id);
create policy "history_insert_own"
on public.translation_history for insert to authenticated
with check (
    (select auth.uid()) = user_id
    and (
        conversation_id is null
        or exists (
            select 1 from public.conversations
            where id = public.translation_history.conversation_id
              and user_id = (select auth.uid())
        )
    )
);
create policy "history_delete_own"
on public.translation_history for delete to authenticated
using ((select auth.uid()) = user_id);

create policy "suggestions_select_own_or_admin"
on public.slang_suggestions for select to authenticated
using ((select auth.uid()) = user_id or (select private.is_admin()));
create policy "suggestions_insert_own_pending"
on public.slang_suggestions for insert to authenticated
with check (
    (select auth.uid()) = user_id
    and status = 'pending'
    and reviewed_by is null
    and reviewed_at is null
);
create policy "suggestions_admin_update"
on public.slang_suggestions for update to authenticated
using ((select private.is_admin()))
with check ((select private.is_admin()));

create policy "approved_terms_read_active"
on public.approved_terms for select to anon, authenticated
using (active);
create policy "approved_terms_admin_insert"
on public.approved_terms for insert to authenticated
with check ((select private.is_admin()));
create policy "approved_terms_admin_update"
on public.approved_terms for update to authenticated
using ((select private.is_admin()))
with check ((select private.is_admin()));
create policy "approved_terms_admin_delete"
on public.approved_terms for delete to authenticated
using ((select private.is_admin()));
