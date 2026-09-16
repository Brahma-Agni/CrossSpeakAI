-- Store the persona selected during Supabase registration in public.profiles.
-- Apply after 003_plans_and_quota.sql.

create or replace function private.create_profile_for_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id, user_mode)
    values (
        new.id,
        case
            when new.raw_user_meta_data ->> 'user_mode' in ('corporate', 'genz')
                then new.raw_user_meta_data ->> 'user_mode'
            else 'corporate'
        end
    )
    on conflict (id) do nothing;
    return new;
end;
$$;
