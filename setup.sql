-- Kör hela det här i Supabase: SQL Editor -> New query -> Run

create table if not exists rooms (
  room text not null,
  member text not null,
  data jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (room, member)
);

-- Ingen får läsa tabellen direkt; allt går via funktionerna nedan som kräver rumsnamnet.
alter table rooms enable row level security;

create or replace function get_room(r text) returns setof rooms
language sql security definer set search_path = public as $$
  select * from rooms where room = r and updated_at > now() - interval '90 days'
$$;

create or replace function put_room(r text, m text, d jsonb) returns void
language sql security definer set search_path = public as $$
  insert into rooms(room, member, data, updated_at) values (r, m, d, now())
  on conflict (room, member) do update set data = excluded.data, updated_at = now()
$$;

create or replace function leave_room(r text, m text) returns void
language sql security definer set search_path = public as $$
  delete from rooms where room = r and member = m
$$;

grant execute on function get_room(text), put_room(text,text,jsonb), leave_room(text,text) to anon;
