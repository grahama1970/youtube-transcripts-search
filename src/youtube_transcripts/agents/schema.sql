CREATE TABLE IF NOT EXISTS agent_tasks (
    task_id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    config TEXT NOT NULL,
    result TEXT,
    error TEXT,
    progress REAL DEFAULT 0.0,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS agent_messages (
    message_id TEXT PRIMARY KEY,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    task_id TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_status ON agent_tasks(status);
CREATE INDEX idx_agent_type ON agent_tasks(agent_type);
CREATE INDEX idx_messages_recipient ON agent_messages(to_agent, processed);