CREATE TABLE manufacturers (id INTEGER PRIMARY KEY, name TEXT COLLATE NOCASE NOT NULL UNIQUE);
CREATE TABLE devices (id INTEGER PRIMARY KEY, inventory_number TEXT COLLATE NOCASE NOT NULL UNIQUE,
 type TEXT NOT NULL, model TEXT NOT NULL, value_cents INTEGER NOT NULL CHECK(value_cents >= 0),
 manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id));
PRAGMA user_version=1;
