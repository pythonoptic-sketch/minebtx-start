-- BTX Start backend schema.
--
-- SQLite-compatible for local development and tests. Production can run the
-- same logical schema in Postgres with type adjustments and managed migrations.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS miners (
  payout_address TEXT PRIMARY KEY,
  first_share_at TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workers (
  payout_address TEXT NOT NULL,
  worker_name TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  user_agent TEXT,
  PRIMARY KEY (payout_address, worker_name),
  FOREIGN KEY (payout_address) REFERENCES miners(payout_address)
);

CREATE TABLE IF NOT EXISTS shares (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  payout_address TEXT NOT NULL,
  worker_name TEXT NOT NULL,
  job_id TEXT NOT NULL,
  accepted INTEGER NOT NULL,
  is_block INTEGER NOT NULL DEFAULT 0,
  difficulty REAL NOT NULL DEFAULT 0,
  reason TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (payout_address) REFERENCES miners(payout_address)
);

CREATE INDEX IF NOT EXISTS idx_shares_payout_created
  ON shares(payout_address, created_at);

CREATE INDEX IF NOT EXISTS idx_shares_worker_seen
  ON shares(payout_address, worker_name, created_at);

CREATE TABLE IF NOT EXISTS balances (
  payout_address TEXT PRIMARY KEY,
  gross_sat INTEGER NOT NULL DEFAULT 0,
  fee_sat INTEGER NOT NULL DEFAULT 0,
  payable_sat INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (payout_address) REFERENCES miners(payout_address)
);

CREATE TABLE IF NOT EXISTS payouts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  payout_address TEXT NOT NULL,
  gross_sat INTEGER NOT NULL,
  fee_sat INTEGER NOT NULL,
  paid_sat INTEGER NOT NULL,
  txid TEXT,
  status TEXT NOT NULL DEFAULT 'planned',
  created_at TEXT NOT NULL,
  FOREIGN KEY (payout_address) REFERENCES miners(payout_address)
);

CREATE TABLE IF NOT EXISTS fee_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  payout_address TEXT NOT NULL,
  fee_sat INTEGER NOT NULL,
  fee_bps INTEGER NOT NULL,
  treasury_address TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (payout_address) REFERENCES miners(payout_address)
);

CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_addresses (
  account_id TEXT NOT NULL,
  payout_address TEXT NOT NULL,
  verified_at TEXT,
  PRIMARY KEY (account_id, payout_address),
  FOREIGN KEY (account_id) REFERENCES accounts(id),
  FOREIGN KEY (payout_address) REFERENCES miners(payout_address)
);

CREATE TABLE IF NOT EXISTS subscriptions (
  account_id TEXT PRIMARY KEY,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  status TEXT NOT NULL,
  trial_end TEXT,
  current_period_end TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS backend_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
