-- Create table for storing encrypted project secrets
CREATE TABLE IF NOT EXISTS project_secrets (
    project_id TEXT PRIMARY KEY,
    payload BLOB NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
