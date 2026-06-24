-- ============================================================
-- LearnGraph — Supabase / Postgres schema
-- Run this in the Supabase SQL editor.
--
-- Tables for long-term learner memory + gamification. Row-Level Security
-- ensures each user can only read/write their own rows. The LangGraph
-- checkpointer (short-term memory) creates its own tables automatically via
-- PostgresSaver.setup(), so they are not defined here.
-- ============================================================

-- ---------- learner_profiles ----------
create table if not exists public.learner_profiles (
    user_id      uuid primary key references auth.users (id) on delete cascade,
    goals        jsonb       not null default '[]'::jsonb,
    preferences  jsonb       not null default '{}'::jsonb,
    xp           integer     not null default 0,
    streak_days  integer     not null default 0,
    last_active  date,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);

-- ---------- topic_progress ----------
create table if not exists public.topic_progress (
    id           bigint generated always as identity primary key,
    user_id      uuid        not null references auth.users (id) on delete cascade,
    topic        text        not null,
    mastery      real        not null default 1.0,
    completed_at timestamptz not null default now(),
    unique (user_id, topic)
);

-- ---------- quiz_results ----------
create table if not exists public.quiz_results (
    id            bigint generated always as identity primary key,
    user_id       uuid        not null references auth.users (id) on delete cascade,
    topic         text        not null,
    score         real        not null,
    total         integer     not null,
    weak_concepts jsonb       not null default '[]'::jsonb,
    taken_at      timestamptz not null default now()
);

-- ---------- roadmaps ----------
create table if not exists public.roadmaps (
    id         bigint generated always as identity primary key,
    user_id    uuid        not null references auth.users (id) on delete cascade,
    goal       text        not null,
    plan       jsonb       not null,
    progress   integer     not null default 0,
    created_at timestamptz not null default now()
);

-- ---------- indexes ----------
create index if not exists idx_topic_progress_user on public.topic_progress (user_id);
create index if not exists idx_quiz_results_user   on public.quiz_results (user_id);
create index if not exists idx_roadmaps_user        on public.roadmaps (user_id);

-- ============================================================
-- Row-Level Security
-- ============================================================
alter table public.learner_profiles enable row level security;
alter table public.topic_progress   enable row level security;
alter table public.quiz_results      enable row level security;
alter table public.roadmaps          enable row level security;

-- Helper to (re)create a policy idempotently.
do $$
declare
    t text;
begin
    foreach t in array array['learner_profiles', 'topic_progress', 'quiz_results', 'roadmaps']
    loop
        execute format('drop policy if exists "owner_select" on public.%I;', t);
        execute format('drop policy if exists "owner_modify" on public.%I;', t);

        execute format(
            'create policy "owner_select" on public.%I for select using (auth.uid() = user_id);', t);
        execute format(
            'create policy "owner_modify" on public.%I for all using (auth.uid() = user_id) with check (auth.uid() = user_id);', t);
    end loop;
end $$;

-- ============================================================
-- Auto-provision a profile row when a new auth user signs up.
-- ============================================================
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
    insert into public.learner_profiles (user_id)
    values (new.id)
    on conflict (user_id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ============================================================
-- keep updated_at fresh on learner_profiles
-- ============================================================
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_touch_profile on public.learner_profiles;
create trigger trg_touch_profile
    before update on public.learner_profiles
    for each row execute function public.touch_updated_at();


-- ============================================================
-- usage_events — analytics, cost tracking, token accounting
-- Written by the backend (service role). RLS is enabled with no public policy,
-- so anon/auth clients cannot read it; only the service role (admin API) can.
-- ============================================================
create table if not exists public.usage_events (
    id                bigint generated always as identity primary key,
    user_id           uuid references auth.users (id) on delete set null,
    event_type        text not null,           -- chat | tool | resume_analysis
    agent             text,                     -- supervisor route
    tool              text,
    model             text,
    prompt_tokens     integer     not null default 0,
    completion_tokens integer     not null default 0,
    total_tokens      integer     not null default 0,
    cost_usd          numeric(12, 6) not null default 0,
    created_at        timestamptz not null default now()
);

create index if not exists idx_usage_events_created on public.usage_events (created_at desc);
create index if not exists idx_usage_events_type    on public.usage_events (event_type);
create index if not exists idx_usage_events_agent   on public.usage_events (agent);

alter table public.usage_events enable row level security;
-- No SELECT/INSERT policies => only the service-role key (backend) may access it.


-- ============================================================
-- knowledge_documents — RAG vector store (pgvector)
-- Requires the pgvector extension. Embeddings are 1536-dim
-- (OpenAI text-embedding-3-small). Populate via: python -m app.rag.ingest
-- ============================================================
create extension if not exists vector;

create table if not exists public.knowledge_documents (
    id         bigint generated always as identity primary key,
    source     text not null,
    title      text,
    chunk      text not null,
    embedding  vector(1536),
    created_at timestamptz not null default now()
);

-- Approximate nearest-neighbour index for cosine distance.
create index if not exists idx_knowledge_embedding
    on public.knowledge_documents
    using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- RLS on; no public policy => retrieval goes through the backend (service role).
alter table public.knowledge_documents enable row level security;

-- Similarity search RPC used by the backend retriever.
create or replace function public.match_knowledge(
    query_embedding vector(1536),
    match_count int default 4
)
returns table (id bigint, source text, title text, chunk text, score float)
language sql stable
as $$
    select
        kd.id,
        kd.source,
        kd.title,
        kd.chunk,
        1 - (kd.embedding <=> query_embedding) as score
    from public.knowledge_documents kd
    where kd.embedding is not null
    order by kd.embedding <=> query_embedding
    limit match_count;
$$;
