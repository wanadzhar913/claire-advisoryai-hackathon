-- Database schema for the application
-- Generated from SQLModel classes

CREATE TABLE IF NOT EXISTS app_users (
    id SERIAL PRIMARY KEY,
    clerk_id TEXT UNIQUE,
    email TEXT UNIQUE NOT NULL,
    -- Nullable when using Clerk authentication (backend creates users with hashed_password = NULL)
    hashed_password TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create session table
CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES app_users(id) ON DELETE CASCADE
);

-- Create thread table (for LangGraph)
CREATE TABLE IF NOT EXISTS thread (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create user uploads table
CREATE TABLE IF NOT EXISTS user_upload (
    file_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_url TEXT NOT NULL,
    file_mime_type TEXT NOT NULL,
    file_extension TEXT NOT NULL,
    statement_type TEXT NOT NULL CHECK(statement_type IN ('banking_transaction', 'receipt', 'invoice', 'other')),
    expense_month INTEGER NOT NULL,
    expense_year INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES app_users(id) ON DELETE CASCADE
);

-- Banking transactions table (structured fields for Malaysian bank statements)
CREATE TABLE IF NOT EXISTS statement_banking_transaction (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    file_id TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    transaction_year INTEGER NOT NULL,
    transaction_month INTEGER NOT NULL,
    transaction_day INTEGER NOT NULL,
    description TEXT NOT NULL,
    merchant_name TEXT,
    amount DECIMAL(15, 2) NOT NULL,
    is_subscription BOOLEAN NOT NULL DEFAULT FALSE,
    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('debit', 'credit')), -- 'credit' means money coming in, 'debit' means money going out
    balance DECIMAL(15, 2),
    reference_number TEXT,
    transaction_code TEXT,
    category TEXT,
    currency TEXT NOT NULL DEFAULT 'MYR',
    subscription_status TEXT CHECK(subscription_status IN ('predicted', 'confirmed', 'rejected', 'needs_review')),
    subscription_confidence REAL CHECK(subscription_confidence >= 0 AND subscription_confidence <= 1),
    subscription_merchant_key TEXT,
    subscription_name TEXT,
    subscription_reason_codes JSONB,
    subscription_updated_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES app_users(id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES user_upload(file_id) ON DELETE CASCADE
);

-- User financial goals table
CREATE TABLE IF NOT EXISTS user_goal (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    target_amount DECIMAL(15, 2) NOT NULL CHECK (target_amount >= 0),
    current_saved DECIMAL(15, 2) NOT NULL DEFAULT 0 CHECK (current_saved >= 0),
    target_year INTEGER NOT NULL,
    target_month INTEGER NOT NULL CHECK (target_month >= 1 AND target_month <= 12),
    banner_key TEXT NOT NULL CHECK (banner_key IN ('banner_1', 'banner_2', 'banner_3', 'banner_4')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for goals
CREATE INDEX IF NOT EXISTS idx_goal_user_id ON user_goal(user_id);
CREATE INDEX IF NOT EXISTS idx_goal_user_created_at ON user_goal(user_id, created_at);

-- Financial insights table (AI-generated transaction analysis)
CREATE TABLE IF NOT EXISTS financial_insight (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    file_id TEXT REFERENCES user_upload(file_id) ON DELETE SET NULL,
    insight_type TEXT NOT NULL CHECK(insight_type IN ('pattern', 'alert', 'recommendation')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT 'Lightbulb',
    severity TEXT CHECK(severity IN ('info', 'warning', 'critical')),
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for financial insights
CREATE INDEX IF NOT EXISTS idx_insight_user_id ON financial_insight(user_id);
CREATE INDEX IF NOT EXISTS idx_insight_user_type ON financial_insight(user_id, insight_type);
CREATE INDEX IF NOT EXISTS idx_insight_file_id ON financial_insight(file_id);

-- Create indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_user_email ON app_users(email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_app_users_clerk_id ON app_users(clerk_id);
CREATE INDEX IF NOT EXISTS idx_session_user_id ON session(user_id);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_user_id ON statement_banking_transaction(user_id);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_file_id ON statement_banking_transaction(file_id);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_date ON statement_banking_transaction(transaction_date);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_year_month ON statement_banking_transaction(transaction_year, transaction_month);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_type ON statement_banking_transaction(transaction_type);

-- Subscription classification indexes
CREATE INDEX IF NOT EXISTS idx_banking_transaction_user_date ON statement_banking_transaction(user_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_user_subscription ON statement_banking_transaction(user_id, is_subscription);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_user_merchant_key ON statement_banking_transaction(user_id, subscription_merchant_key);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_user_date_subscription ON statement_banking_transaction(user_id, transaction_date, is_subscription);