"""Database module — single main.db with multiple tables."""
import sqlite3
import os

DB_PATH = "/data/database/main.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'custom',
            sort_order INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target_date TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            is_pinned INTEGER NOT NULL DEFAULT 0,
            show_on_home INTEGER NOT NULL DEFAULT 0,
            repeat_type TEXT NOT NULL DEFAULT 'none',
            repeat_interval INTEGER NOT NULL DEFAULT 1,
            include_start_day INTEGER NOT NULL DEFAULT 0,
            highlight INTEGER NOT NULL DEFAULT 0,
            color TEXT NOT NULL DEFAULT '#4A90D9',
            icon TEXT NOT NULL DEFAULT 'default',
            note TEXT NOT NULL DEFAULT '',
            image TEXT NOT NULL DEFAULT '',
            is_completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            ripple_score INTEGER DEFAULT 50,
            fire_score INTEGER DEFAULT 50,
            difficulty INTEGER DEFAULT 50,
            status INTEGER DEFAULT 1,
            progress INTEGER DEFAULT 0,
            linked_countdown_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            achieved_at TEXT,
            FOREIGN KEY (linked_countdown_id) REFERENCES events(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS wish_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wish_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_completed INTEGER DEFAULT 0,
            target_date TEXT,
            FOREIGN KEY (wish_id) REFERENCES wishes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS wish_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wish_id INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            FOREIGN KEY (wish_id) REFERENCES wishes(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS wish_journey_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wish_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            entry_date DATETIME NOT NULL,
            fire_score_at_entry INTEGER DEFAULT 50,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (wish_id) REFERENCES wishes(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_journey_wish_id ON wish_journey_log(wish_id);

        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            content_md TEXT NOT NULL DEFAULT '',
            content_html TEXT NOT NULL DEFAULT '',
            is_starred INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS memo_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memo_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (memo_id) REFERENCES memos(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_memos_created_at ON memos(created_at);
        CREATE INDEX IF NOT EXISTS idx_memos_subject ON memos(subject);
    """)

    # Default categories
    existing = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if existing == 0:
        conn.execute("INSERT INTO categories (name, type, sort_order) VALUES (?, 'fixed', 0)", ("首页",))
        conn.execute("INSERT INTO categories (name, type, sort_order) VALUES (?, 'fixed', 1)", ("全部",))
        conn.execute("INSERT INTO categories (name, type, sort_order) VALUES (?, 'fixed', 2)", ("归档",))
        conn.execute("INSERT INTO categories (name, type, sort_order) VALUES (?, 'custom', 3)", ("默认",))

    # Schema migration: ensure show_on_home column exists
    try:
        conn.execute("ALTER TABLE events ADD COLUMN show_on_home INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Schema migration: upgrade old wishes table to v2 schema
    _migrate_wishes(conn)
    # Schema migration: extract journey_content to wish_journey_log table
    _migrate_journey(conn)
    # Schema migration: move old notes to memos
    _migrate_notes_to_memos(conn)
    # Schema migration: add content_md column to memos
    _migrate_memos_add_md(conn)

    conn.commit()
    conn.close()


def _migrate_wishes(conn):
    """Upgrade wishes table through schema versions to current (v3)."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info('wishes')").fetchall()]
    # Current schema: has ripple_score, no legacy columns
    has_legacy = "is_fulfilled" in cols or "para_category" in cols or "journey_content" in cols
    if "ripple_score" in cols and not has_legacy:
        return  # already current schema

    # Collect existing data with status mapping
    old_rows = []
    if "is_fulfilled" in cols:
        # v0 schema: is_fulfilled column
        rows = conn.execute("SELECT id, title, description, is_fulfilled, created_at FROM wishes").fetchall()
        for r in rows:
            status = 2 if r["is_fulfilled"] else 1
            old_rows.append((r["id"], r["title"], r["description"], 50, 50, 50, status, 0, None, r["created_at"]))
    elif "para_category" in cols:
        # v1 schema: TEXT status + para_category
        rows = conn.execute("SELECT * FROM wishes").fetchall()
        for r in rows:
            # Map text status to integer
            old_status = r["status"]
            if old_status == "draft":
                new_status = 0
            elif old_status == "achieved" or old_status == "archived":
                new_status = 2
            else:
                new_status = 1  # active or default
            old_rows.append((
                r["id"], r["title"], r.get("description", ""),
                r.get("ripple_score", 50), r.get("fire_score", 50),
                r.get("difficulty", 50), new_status,
                r.get("progress", 0), r.get("linked_countdown_id"),
                r.get("created_at", "")
            ))
    else:
        rows = conn.execute("SELECT * FROM wishes").fetchall()
        for r in rows:
            old_rows.append((
                r["id"], r["title"], r.get("description", ""),
                r.get("ripple_score", 50), r.get("fire_score", 50),
                r.get("difficulty", 50), r.get("status", 1),
                r.get("progress", 0), r.get("linked_countdown_id"),
                r.get("created_at", "")
            ))

    conn.execute("DROP TABLE IF EXISTS wishes")
    conn.execute("""
        CREATE TABLE wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            ripple_score INTEGER DEFAULT 50,
            fire_score INTEGER DEFAULT 50,
            difficulty INTEGER DEFAULT 50,
            status INTEGER DEFAULT 1,
            progress INTEGER DEFAULT 0,
            linked_countdown_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            achieved_at TEXT,
            FOREIGN KEY (linked_countdown_id) REFERENCES events(id) ON DELETE SET NULL
        )
    """)

    for row in old_rows:
        conn.execute(
            """INSERT INTO wishes (id, title, description, ripple_score, fire_score,
               difficulty, status, progress, linked_countdown_id, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))""",
            row
        )


def _migrate_journey(conn):
    """Migrate journey_content from wishes table to wish_journey_log table."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info('wishes')").fetchall()]
    if "journey_content" not in cols:
        return  # already migrated

    # Copy existing journey_content to wish_journey_log
    rows = conn.execute(
        "SELECT id, journey_content, fire_score, updated_at FROM wishes WHERE journey_content != ''"
    ).fetchall()

    for r in rows:
        entry_date = r["updated_at"] or "datetime('now','localtime')"
        conn.execute(
            """INSERT INTO wish_journey_log (wish_id, content, entry_date, fire_score_at_entry)
               VALUES (?,?,?,?)""",
            (r["id"], r["journey_content"], entry_date, r["fire_score"] or 50),
        )

    # Drop journey_content column (SQLite: recreate table without the column)
    # Get all current wishes data
    all_rows = conn.execute("SELECT * FROM wishes").fetchall()
    # Build new column list without journey_content
    new_cols = [c for c in [r[1] for r in conn.execute("PRAGMA table_info('wishes')").fetchall()]
                if c != "journey_content"]

    conn.execute("DROP TABLE IF EXISTS wishes")
    conn.execute("""
        CREATE TABLE wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            ripple_score INTEGER DEFAULT 50,
            fire_score INTEGER DEFAULT 50,
            difficulty INTEGER DEFAULT 50,
            status INTEGER DEFAULT 1,
            progress INTEGER DEFAULT 0,
            linked_countdown_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            achieved_at TEXT,
            FOREIGN KEY (linked_countdown_id) REFERENCES events(id) ON DELETE SET NULL
        )
    """)

    for row in all_rows:
        conn.execute(
            """INSERT INTO wishes (id, user_id, title, description, ripple_score, fire_score,
               difficulty, status, progress, linked_countdown_id,
               created_at, updated_at, achieved_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (row["id"], row["user_id"], row["title"], row["description"],
             row["ripple_score"], row["fire_score"], row["difficulty"],
             row["status"], row["progress"], row["linked_countdown_id"],
             row["created_at"], row["updated_at"], row["achieved_at"]),
        )


def _migrate_notes_to_memos(conn):
    """Migrate old notes table to memos table."""
    try:
        conn.execute("SELECT id FROM notes LIMIT 1")
    except sqlite3.OperationalError:
        return  # notes table doesn't exist, nothing to migrate

    old_rows = conn.execute("SELECT * FROM notes").fetchall()
    if not old_rows:
        return

    for r in old_rows:
        summary = _strip_html(r["content"])[:100] if r["content"] else ""
        conn.execute(
            """INSERT INTO memos (subject, summary, content_html, is_starred, created_at, updated_at)
               VALUES (?,?,?,0,?,?)""",
            (r["title"], summary, r["content"] or "", r["created_at"], r["updated_at"]),
        )

    conn.execute("DROP TABLE IF EXISTS notes")


def _strip_html(html):
    """Remove HTML tags and return plain text."""
    import re
    clean = re.sub(r'<[^>]+>', '', html or '')
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def _migrate_memos_add_md(conn):
    """Add content_md column to memos if missing."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info('memos')").fetchall()]
    if "content_md" in cols:
        return
    try:
        conn.execute("ALTER TABLE memos ADD COLUMN content_md TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
