-- Secure Razorpay order records and atomic paid-plan activation.
-- Apply after 004_profile_persona.sql.

alter table public.profiles
    add column if not exists plan_started_at timestamptz,
    add column if not exists free_usage_started_at timestamptz;

update public.profiles
set free_usage_started_at = created_at
where free_usage_started_at is null;

alter table public.profiles
    alter column free_usage_started_at set default now(),
    alter column free_usage_started_at set not null;

create table if not exists public.billing_orders (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    provider text not null default 'razorpay' check (provider = 'razorpay'),
    provider_order_id text not null unique,
    provider_payment_id text unique,
    provider_event_id text unique,
    amount integer not null check (amount > 0),
    currency text not null check (char_length(currency) = 3),
    plan_days integer not null check (plan_days between 1 and 366),
    status text not null default 'pending'
        check (status in ('pending', 'paid', 'failed', 'refunded')),
    created_at timestamptz not null default now(),
    paid_at timestamptz,
    plan_expires_at timestamptz
);

create index if not exists billing_orders_user_created_idx
    on public.billing_orders (user_id, created_at desc);

alter table public.billing_orders enable row level security;

drop policy if exists "billing_orders_select_own" on public.billing_orders;
create policy "billing_orders_select_own"
on public.billing_orders for select to authenticated
using ((select auth.uid()) = user_id);

revoke all on table public.billing_orders from anon, authenticated;
grant select on table public.billing_orders to authenticated;
grant select, insert, update on table public.billing_orders to service_role;

create or replace function public.activate_paid_plan(
    p_provider_order_id text,
    p_provider_payment_id text,
    p_provider_event_id text default null
)
returns table (user_id uuid, plan text, plan_expires_at timestamptz)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_order public.billing_orders%rowtype;
    v_now timestamptz := now();
    v_base timestamptz;
    v_expiry timestamptz;
begin
    select * into v_order
    from public.billing_orders
    where provider_order_id = p_provider_order_id
    for update;

    if not found then
        raise exception 'Unknown billing order';
    end if;

    if v_order.status = 'paid' then
        if v_order.provider_payment_id <> p_provider_payment_id then
            raise exception 'Order already paid with a different payment';
        end if;
        return query
        select v_order.user_id, p.plan, p.plan_expires_at
        from public.profiles p where p.id = v_order.user_id;
        return;
    end if;

    if v_order.status <> 'pending' then
        raise exception 'Billing order is not pending';
    end if;

    select greatest(v_now, coalesce(p.plan_expires_at, v_now))
    into v_base
    from public.profiles p
    where p.id = v_order.user_id
    for update;

    if v_base is null then
        raise exception 'Profile not found';
    end if;

    v_expiry := v_base + make_interval(days => v_order.plan_days);

    update public.profiles p
    set plan = 'paid',
        plan_started_at = case
            when p.plan = 'paid' and p.plan_expires_at > v_now
                then p.plan_started_at
            else v_now
        end,
        plan_expires_at = v_expiry,
        -- If paid access expires, the next free allowance starts fresh.
        free_usage_started_at = v_expiry
    where p.id = v_order.user_id;

    update public.billing_orders
    set status = 'paid',
        provider_payment_id = p_provider_payment_id,
        provider_event_id = coalesce(p_provider_event_id, provider_event_id),
        paid_at = v_now,
        plan_expires_at = v_expiry
    where id = v_order.id;

    return query select v_order.user_id, 'paid'::text, v_expiry;
end;
$$;

revoke all on function public.activate_paid_plan(text, text, text) from public;
revoke all on function public.activate_paid_plan(text, text, text) from anon, authenticated;
grant execute on function public.activate_paid_plan(text, text, text) to service_role;

create or replace function public.get_translation_usage(p_user_id uuid)
returns integer
language sql
stable
security definer
set search_path = ''
as $$
    select count(*)::integer
    from public.translation_history h
    join public.profiles p on p.id = h.user_id
    where h.user_id = p_user_id
      and h.created_at >= p.free_usage_started_at
      and (p_user_id = (select auth.uid()) or (select private.is_admin()));
$$;

grant execute on function public.get_translation_usage(uuid) to authenticated;
