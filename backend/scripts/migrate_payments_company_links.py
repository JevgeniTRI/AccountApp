import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.settings import settings


def get_sqlite_db_path() -> Path:
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        raise RuntimeError("This migration only supports sqlite:/// URLs")
    return Path(settings.database_url.removeprefix(prefix))


def column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def main() -> None:
    db_path = get_sqlite_db_path()
    conn = sqlite3.connect(db_path)
    try:
        changes = []

        if not column_exists(conn, "payments", "related_company_id"):
            conn.execute("ALTER TABLE payments ADD COLUMN related_company_id INTEGER REFERENCES companies (id)")
            changes.append("added related_company_id")

        if not column_exists(conn, "payments", "counterparty_name"):
            conn.execute("ALTER TABLE payments ADD COLUMN counterparty_name VARCHAR(255)")
            changes.append("added counterparty_name")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_payments_related_company_id ON payments (related_company_id)"
        )
        conn.commit()

        if changes:
            print(", ".join(changes))
        else:
            print("payments table already supports related companies and manual counterparties")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
