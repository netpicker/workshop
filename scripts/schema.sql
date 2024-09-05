CREATE TABLE reconcile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,       -- Unique identifier for each entry
    reconcile_type TEXT NOT NULL,               -- Reconcile Type
    content TEXT NOT NULL                       -- JSON string for reconcile content fields
);