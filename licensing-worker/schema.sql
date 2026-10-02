CREATE TABLE IF NOT EXISTS entitlements (
  dossier_id TEXT PRIMARY KEY,
  license_id TEXT NOT NULL UNIQUE,
  account_email TEXT,
  plan TEXT NOT NULL CHECK (plan IN ('FREE','MEDIUM','FULL')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  source TEXT NOT NULL DEFAULT 'manual',
  note TEXT NOT NULL DEFAULT '',
  valid_until TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entitlements_email ON entitlements(account_email);
CREATE INDEX IF NOT EXISTS idx_entitlements_plan ON entitlements(plan);
CREATE INDEX IF NOT EXISTS idx_entitlements_status ON entitlements(status);

CREATE TABLE IF NOT EXISTS entitlement_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dossier_id TEXT NOT NULL,
  action TEXT NOT NULL,
  plan TEXT,
  source TEXT,
  note TEXT,
  created_at TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS usage_installations (
  dossier_id TEXT NOT NULL,
  installation_id TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'FREE' CHECK (plan IN ('FREE','MEDIUM','FULL')),
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  launch_count INTEGER NOT NULL DEFAULT 1,
  app_version TEXT NOT NULL DEFAULT '',
  platform TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (dossier_id, installation_id)
);

CREATE INDEX IF NOT EXISTS idx_usage_last_seen ON usage_installations(last_seen);
