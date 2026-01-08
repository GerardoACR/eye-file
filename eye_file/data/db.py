from __future__ import annotations

import sqlite3
from pathlib import Path


def get_db_path(project_root: Path) -> Path:
    """
    Return the path where the SQLite database should live.

    We keep the DB in ./app_data/eyefile.db so:
    - it doesn't pollute the repository
    - it's easy to exclude from git
    - it behaves like a local desktop app (user data)
    """
    app_data_dir = project_root / "app_data"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir / "eyefile.db"


def connect(db_path: Path) -> sqlite3.Connection:
    """
    Create a SQLite connection with sensible defaults.

    - foreign_keys ON: enforce FK constraints
    - row_factory: access columns by name (row["id"]) instead of tuple indexes
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection, schema_sql_path: Path) -> None:
    """
    Initialize the database schema if it does not exist yet.

    Reads schema.sql and executes it as a script.
    """
    schema_sql = schema_sql_path.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()


def seed_minimal_data(conn: sqlite3.Connection) -> None:
    """
    Seed minimal rows so the app can save notes immediately.

    MVP shortcut:
    - Create a default category if none exist.
    - Create a placeholder document if none exist.

    Later, once Import PDF exists, you will NOT need the placeholder doc.
    """
    
    # Categories tree (seed once if table is empty)
    ensure_default_categories(conn)

    # Placeholder document
    row = conn.execute("SELECT id FROM documents LIMIT 1;").fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO documents (title, authors, year, file_path) VALUES (?, ?, ?, ?);",
            ("(Placeholder) No document selected yet", "", None, ""),
        )

    conn.commit()


def get_default_ids(conn: sqlite3.Connection) -> tuple[int, int]:
    """
    Return (document_id, category_id) defaults.

    For now we pick:
    - first document
    - first category
    """
    doc_id = conn.execute("SELECT id FROM documents ORDER BY id ASC LIMIT 1;").fetchone()["id"]
    cat_id = conn.execute("SELECT id FROM categories ORDER BY id ASC LIMIT 1;").fetchone()["id"]
    return int(doc_id), int(cat_id)


def insert_note(
    conn: sqlite3.Connection,
    document_id: int,
    category_id: int,
    excerpt: str,
    body_md: str,
    page_ref: str | None,
) -> int:
    """
    Insert a note and return the inserted note id.
    """
    cur = conn.execute(
        """
        INSERT INTO notes (document_id, category_id, excerpt, body_md, page_ref)
        VALUES (?, ?, ?, ?, ?);
        """,
        (document_id, category_id, excerpt, body_md, page_ref),
    )
    conn.commit()
    return int(cur.lastrowid)

def ensure_default_categories(conn: sqlite3.Connection) -> None:
    """
    Ensure a minimal category tree exists.

    We create:
    - All notes
      - Reading
      - Ideas

    Only inserts if the table is empty.
    """
    row = conn.execute("SELECT id FROM categories LIMIT 1;").fetchone()
    if row is not None:
        return

    cur = conn.execute("INSERT INTO categories (name, parent_id) VALUES (?, ?);", ("All notes", None))
    root_id = int(cur.lastrowid)

    conn.execute("INSERT INTO categories (name, parent_id) VALUES (?, ?);", ("Reading", root_id))
    conn.execute("INSERT INTO categories (name, parent_id) VALUES (?, ?);", ("Ideas", root_id))
    conn.commit()


def fetch_categories(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """
    Return all categories as rows: id, name, parent_id
    """
    return conn.execute(
        "SELECT id, name, parent_id FROM categories ORDER BY parent_id ASC, name ASC;"
    ).fetchall()

def fetch_notes_for_category_subtree(conn: sqlite3.Connection, category_id: int) -> list[sqlite3.Row]:
    """
    Return notes that belong to the selected category OR any of its descendants.

    Uses a recursive CTE to compute the subtree of category ids.
    """
    return conn.execute(
        """
        WITH RECURSIVE subtree(id) AS (
            SELECT ?
            UNION ALL
            SELECT c.id
            FROM categories c
            JOIN subtree s ON c.parent_id = s.id
        )
        SELECT
            n.id,
            n.excerpt,
            n.body_md,
            n.page_ref,
            n.created_at,
            n.category_id,
            c.name AS category_name
        FROM notes n
        JOIN categories c ON c.id = n.category_id
        WHERE n.category_id IN (SELECT id FROM subtree)
        ORDER BY n.id DESC
        """,
        (category_id,),
    ).fetchall()


def fetch_note_by_id(conn: sqlite3.Connection, note_id: int) -> sqlite3.Row | None:
    """
    Fetch a single note row (used when the user clicks a note in the list).
    """
    return conn.execute(
        """
        SELECT id, excerpt, body_md, page_ref, created_at, category_id, document_id
        FROM notes
        WHERE id = ?
        """,
        (note_id,),
    ).fetchone()
