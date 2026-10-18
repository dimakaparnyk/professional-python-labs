-- Upgrade, performed once by database.migrate.
ALTER TABLE devices ADD COLUMN location TEXT;
PRAGMA user_version=2;
-- SQLite 3.35+ downgrade (requires a separate controlled migration):
-- ALTER TABLE devices DROP COLUMN location;
-- PRAGMA user_version=1;
