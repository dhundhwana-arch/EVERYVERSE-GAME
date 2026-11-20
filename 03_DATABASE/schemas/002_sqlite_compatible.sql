CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'player',
    is_guest INTEGER NOT NULL DEFAULT 0,
    is_suspended INTEGER NOT NULL DEFAULT 0,
    chat_restricted_until INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    preferred_language TEXT NOT NULL DEFAULT 'en',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    country_name TEXT NOT NULL DEFAULT 'Navabharat Confederation',
    city_name TEXT NOT NULL DEFAULT 'Suryanagar',
    avatar_method TEXT NOT NULL DEFAULT 'manual',
    avatar_config_json TEXT NOT NULL,
    photo_consent_granted INTEGER NOT NULL DEFAULT 0,
    privacy_level TEXT NOT NULL DEFAULT 'public',
    virtual_money INTEGER NOT NULL DEFAULT 1000,
    knowledge_points INTEGER NOT NULL DEFAULT 0,
    reputation_score INTEGER NOT NULL DEFAULT 10,
    life_level INTEGER NOT NULL DEFAULT 1,
    active_career_id TEXT,
    skills_json TEXT NOT NULL DEFAULT '{}',
    achievements_json TEXT NOT NULL DEFAULT '[]',
    inventory_json TEXT NOT NULL DEFAULT '[]',
    world_position_json TEXT NOT NULL DEFAULT '{"x": 0, "y": 0, "z": 0, "district": "Central Plaza"}',
    save_version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS career_tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    career_id TEXT NOT NULL,
    title TEXT NOT NULL,
    stage INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'assigned',
    deadline_epoch INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    feedback TEXT NOT NULL DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS elections (
    id TEXT PRIMARY KEY,
    country_name TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    winner_user_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS election_candidates (
    id TEXT PRIMARY KEY,
    election_id TEXT NOT NULL REFERENCES elections(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    public_trust INTEGER NOT NULL DEFAULT 0,
    governance_score INTEGER NOT NULL DEFAULT 0,
    integrity_score INTEGER NOT NULL DEFAULT 0,
    votes INTEGER NOT NULL DEFAULT 0,
    assigned_office TEXT NOT NULL DEFAULT 'candidate'
);

CREATE TABLE IF NOT EXISTS election_votes (
    id TEXT PRIMARY KEY,
    election_id TEXT NOT NULL REFERENCES elections(id) ON DELETE CASCADE,
    voter_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    candidate_id TEXT NOT NULL REFERENCES election_candidates(id) ON DELETE CASCADE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(election_id, voter_user_id)
);

CREATE TABLE IF NOT EXISTS economy_ledger (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tx_type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS friendships (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    is_blocked INTEGER NOT NULL DEFAULT 0,
    is_muted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parties (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    leader_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    district TEXT NOT NULL DEFAULT 'Suryanagar Central Plaza',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS party_members (
    party_id TEXT NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (party_id, user_id)
);

CREATE TABLE IF NOT EXISTS moderation_events (
    id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    message_excerpt TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    decision TEXT NOT NULL,
    warning_stage INTEGER NOT NULL DEFAULT 0,
    review_status TEXT NOT NULL DEFAULT 'auto_resolved',
    appeal_status TEXT NOT NULL DEFAULT 'none',
    appeal_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS abuse_reports (
    id TEXT PRIMARY KEY,
    reporter_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reported_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    context_ref TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    actor_id TEXT,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    details_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

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

-- Migration v0.4.0: Family, Wellbeing, Properties & Vehicles (PostgreSQL & SQLite compatible)
CREATE TABLE IF NOT EXISTS family_relationships (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    member_name TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    bond_score INTEGER NOT NULL DEFAULT 50,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wellbeing_state (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    happiness INTEGER NOT NULL DEFAULT 75,
    energy INTEGER NOT NULL DEFAULT 100,
    stress INTEGER NOT NULL DEFAULT 15,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_properties (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_id TEXT NOT NULL,
    property_name TEXT NOT NULL,
    district TEXT NOT NULL,
    purchase_price INTEGER NOT NULL,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_vehicles (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vehicle_id TEXT NOT NULL,
    vehicle_name TEXT NOT NULL,
    vehicle_type TEXT NOT NULL,
    purchase_price INTEGER NOT NULL,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
