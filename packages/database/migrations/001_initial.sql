-- 001_initial.sql
-- Core tables for Grant Path AI

-- ─── Users ───────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    tier VARCHAR(20) DEFAULT 'free',
    org_id UUID,
    api_key_hash VARCHAR(64),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key_hash) WHERE api_key_hash IS NOT NULL;

-- ─── Organizations ───────────────────

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    org_type VARCHAR(50) NOT NULL,
    ein VARCHAR(20),
    uei VARCHAR(20),
    mission_statement TEXT,
    mission_short VARCHAR(500),
    location JSONB DEFAULT '{}',
    annual_budget DECIMAL(15,2),
    team_size INTEGER,
    focus_areas TEXT[] DEFAULT '{}',
    target_population TEXT,
    capacity_statement TEXT,
    past_grants_summary TEXT,
    indirect_cost_rate DECIMAL(5,2) DEFAULT 10.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Grants ──────────────────────────

CREATE TABLE IF NOT EXISTS grants (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    funder_name VARCHAR(255) NOT NULL,
    funder_type VARCHAR(50),
    description TEXT,
    description_compressed TEXT,
    eligibility_criteria JSONB DEFAULT '[]',
    funding_amount_min DECIMAL(15,2),
    funding_amount_max DECIMAL(15,2),
    deadline TIMESTAMPTZ,
    application_url TEXT,
    category_tags TEXT[] DEFAULT '{}',
    geographic_restrictions TEXT[] DEFAULT '{}',
    org_type_eligibility TEXT[] DEFAULT '{}',
    cost_sharing_required BOOLEAN DEFAULT false,
    cost_sharing_percentage DECIMAL(5,2),
    scoring_criteria JSONB DEFAULT '[]',
    required_sections TEXT[] DEFAULT '{}',
    section_limits JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active',
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_verified TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_grants_deadline ON grants(deadline) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_grants_funder ON grants(funder_name);
CREATE INDEX IF NOT EXISTS idx_grants_status ON grants(status);
CREATE INDEX IF NOT EXISTS idx_grants_tags ON grants USING GIN(category_tags);
CREATE INDEX IF NOT EXISTS idx_grants_org_type ON grants USING GIN(org_type_eligibility);

-- ─── Applications ────────────────────

CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    grant_id VARCHAR(50) REFERENCES grants(id),
    user_id UUID REFERENCES users(id),
    project_title VARCHAR(500),
    status VARCHAR(50) DEFAULT 'discovered',
    funding_requested DECIMAL(15,2),
    internal_deadline DATE,
    submission_date TIMESTAMPTZ,
    outcome VARCHAR(50),
    award_amount DECIMAL(15,2),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_apps_org ON applications(org_id);
CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_apps_grant ON applications(grant_id);

-- ─── Application Documents ───────────

CREATE TABLE IF NOT EXISTS application_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    section_name VARCHAR(100) NOT NULL,
    content TEXT,
    word_count INTEGER,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(application_id, section_name, version)
);

-- ─── Budgets ─────────────────────────

CREATE TABLE IF NOT EXISTS budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
    line_items JSONB DEFAULT '[]',
    summary JSONB DEFAULT '{}',
    narrative TEXT,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Grant Match Feedback ────────────

CREATE TABLE IF NOT EXISTS grant_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    grant_id VARCHAR(50) REFERENCES grants(id),
    feedback VARCHAR(20) NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, grant_id)
);

-- ─── Notifications ───────────────────

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    type VARCHAR(50),
    title VARCHAR(255),
    message TEXT,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read);
