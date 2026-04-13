from __future__ import annotations

from pathlib import Path
import sqlite3
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.settings import settings


def get_sqlite_db_path() -> Path:
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        raise RuntimeError("This migration script only supports SQLite databases.")
    return Path(settings.database_url.removeprefix(prefix))


def main() -> None:
    db_path = get_sqlite_db_path()
    conn = sqlite3.connect(db_path)
    conn.isolation_level = None

    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN")
        conn.execute("ALTER TABLE payment_attachments RENAME TO payment_attachments_old")
        conn.execute(
            """
            CREATE TABLE payment_attachments (
                id INTEGER NOT NULL PRIMARY KEY,
                payment_id INTEGER NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                content_type VARCHAR(128),
                file_size INTEGER NOT NULL,
                file_content BLOB NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(payment_id) REFERENCES payments (id)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO payment_attachments (
                id,
                payment_id,
                file_name,
                content_type,
                file_size,
                file_content,
                created_at,
                updated_at
            )
            SELECT
                id,
                payment_id,
                file_name,
                content_type,
                file_size,
                file_content,
                created_at,
                updated_at
            FROM payment_attachments_old
            """
        )
        conn.execute("DROP TABLE payment_attachments_old")
        conn.execute(
            """
            CREATE INDEX ix_payment_attachments_payment_id
            ON payment_attachments (payment_id)
            """
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

    print(f"Payment attachments migrated to multi-file mode in {db_path}")


if __name__ == "__main__":
    main()
