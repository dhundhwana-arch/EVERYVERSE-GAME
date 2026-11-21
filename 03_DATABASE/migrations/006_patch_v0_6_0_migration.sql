-- Migration v0.5.0 + v0.6.0: Justice, Business, Events, Research Labs & Virtual Marketplace
CREATE TABLE IF NOT EXISTS civic_cases (
    id TEXT PRIMARY KEY,
    filed_by_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    case_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    verdict TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_businesses (
    id TEXT PRIMARY KEY,
    owner_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    business_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    capital_invested INTEGER NOT NULL,
    revenue_total INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_projects (
    id TEXT PRIMARY KEY,
    lead_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    progress_pct INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS marketplace_listings (
    id TEXT PRIMARY KEY,
    seller_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_type TEXT NOT NULL,
    title TEXT NOT NULL,
    price_virtual INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    buyer_user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
