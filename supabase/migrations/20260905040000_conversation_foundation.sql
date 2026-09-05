create schema if not exists conversation;

create table if not exists conversation.threads (
  conversation_id uuid primary key default gen_random_uuid(),
  account_id text not null,
  person_id text not null,
  thread_key text not null unique,
  state text not null default 'received'
    check (state in ('received','normalized','thread_matched','classified','action_selected','human_handled','resolved')),
  last_message_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists conversation.replies (
  reply_id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversation.threads(conversation_id) on delete cascade,
  provider_message_id text not null unique,
  account_id text not null,
  person_id text not null,
  source_send_id uuid,
  sender_email text not null,
  subject text not null default '',
  body_text text not null,
  classification text not null default 'unclassified'
    check (classification in ('interested','not_now','negative','ooo','unsubscribe','question','other','unclassified')),
  received_at timestamptz not null,
  created_at timestamptz not null default now()
);

create index if not exists conversation_replies_thread_idx
  on conversation.replies(conversation_id, received_at desc);

alter table conversation.threads enable row level security;
alter table conversation.replies enable row level security;
