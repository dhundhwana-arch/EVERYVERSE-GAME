-- Migration v0.3.0: NPC Dialogue Memory & Side Quests (PostgreSQL & SQLite compatible)
CREATE TABLE IF NOT EXISTS npc_interactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    npc_id TEXT NOT NULL,
    affinity_score INTEGER NOT NULL DEFAULT 0,
    quest_completed INTEGER NOT NULL DEFAULT 0,
    last_dialogue_node TEXT NOT NULL DEFAULT 'greeting',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, npc_id)
);
