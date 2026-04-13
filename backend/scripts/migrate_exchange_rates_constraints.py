from __future__ import annotations

from pathlib import Path
import sqlite3

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
        conn.execute("ALTER TABLE exchange_rates RENAME TO exchange_rates_old")
        conn.execute(
            """
            CREATE TABLE exchange_rates (
                id INTEGER NOT NULL PRIMARY KEY,
                from_currency_code VARCHAR(3) NOT NULL,
                to_currency_code VARCHAR(3) NOT NULL,
                rate_date DATE NOT NULL,
                rate_value NUMERIC(18, 8) NOT NULL,
                source_name VARCHAR(64) NOT NULL,
                source_reference VARCHAR(255),
                is_manual BOOLEAN NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT ck_exchange_rates_rate_value_positive CHECK (rate_value > 0),
                CONSTRAINT ck_exchange_rates_currency_pair_distinct CHECK (from_currency_code <> to_currency_code),
                CONSTRAINT uq_exchange_rates_pair_date_source UNIQUE (
                    from_currency_code,
                    to_currency_code,
                    rate_date,
                    source_name
                ),
                FOREIGN KEY(from_currency_code) REFERENCES currencies (code),
                FOREIGN KEY(to_currency_code) REFERENCES currencies (code)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO exchange_rates (
                id,
                from_currency_code,
                to_currency_code,
                rate_date,
                rate_value,
                source_name,
                source_reference,
                is_manual,
                created_at,
                updated_at
            )
            SELECT
                id,
                from_currency_code,
                to_currency_code,
                rate_date,
                rate_value,
                source_name,
                source_reference,
                is_manual,
                created_at,
                updated_at
            FROM exchange_rates_old
            """
        )
        conn.execute("DROP TABLE exchange_rates_old")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

    print(f"Exchange rates constraints migrated in {db_path}")


if __name__ == "__main__":
    main()
