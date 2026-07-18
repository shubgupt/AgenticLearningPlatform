CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    grade TEXT,
    favorite_sport TEXT,
    favorite_character TEXT,
    friend_names TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lesson_requests(
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    skill TEXT NOT NULL,
    modality TEXT NOT NULL,
    mastery_pct REAL,
    prereq_threshold REAL,
    negative_constraint_token TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | generating | ready | failed
    failure_reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS generated_lessons(
    id INTEGER PRIMARY KEY,
    cache_key TEXT NOT NULL UNIQUE,
    skill TEXT NOT NULL,
    modality TEXT NOT NULL,
    negative_constraint_token TEXT,
    step_index INTEGER NOT NULL DEFAULT 1,
    content_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    critic_status TEXT,
    critic_feedback TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    hit_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS llm_call_trace(
    id INTEGER PRIMARY KEY,
    trace_id TEXT NOT NULL,
    span_id TEXT NOT NULL,
    parent_span_id TEXT,
    request_id INTEGER REFERENCES lesson_requests(id),
    role TEXT NOT NULL,  -- 'lesson_generator' | 'lesson_critic'
    model TEXT,
    input TEXT,
    output TEXT,
    status TEXT,
    started_at TEXT,
    ended_at TEXT,
    latency_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_llm_call_trace_request ON llm_call_trace(request_id);
CREATE INDEX IF NOT EXISTS idx_generated_lessons_cache_key ON generated_lessons(cache_key);
