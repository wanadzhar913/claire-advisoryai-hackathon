-- Database schema for the application
-- Generated from SQLModel classes

CREATE TABLE IF NOT EXISTS app_users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create session table
CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
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
    user_id INTEGER NOT NULL,
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
    user_upload_id TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    transaction_year INTEGER NOT NULL,
    transaction_month INTEGER NOT NULL,
    transaction_day INTEGER NOT NULL,
    description TEXT NOT NULL,
    merchant_name TEXT,
    amount DECIMAL(15, 2) NOT NULL,
    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('debit', 'credit')),
    balance DECIMAL(15, 2),
    reference_number TEXT,
    transaction_code TEXT,
    category TEXT,
    currency TEXT NOT NULL DEFAULT 'MYR',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_upload_id) REFERENCES user_upload(file_id) ON DELETE CASCADE
);



-- Create indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_user_email ON app_users(email);
CREATE INDEX IF NOT EXISTS idx_session_user_id ON session(user_id);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_upload_id ON statement_banking_transaction(user_upload_id);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_date ON statement_banking_transaction(transaction_date);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_year_month ON statement_banking_transaction(transaction_year, transaction_month);
CREATE INDEX IF NOT EXISTS idx_banking_transaction_type ON statement_banking_transaction(transaction_type);