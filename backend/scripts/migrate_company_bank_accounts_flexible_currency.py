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


def main() -> None:
    db_path = get_sqlite_db_path()
    conn = sqlite3.connect(db_path)
    try:
        current_sql_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='company_bank_accounts'"
        ).fetchone()
        if current_sql_row is None:
            raise RuntimeError("company_bank_accounts table not found")

        current_sql = current_sql_row[0] or ""
        if "FOREIGN KEY(currency_code) REFERENCES currencies (code)" not in current_sql and "currency_code VARCHAR(32)" in current_sql:
            print("company_bank_accounts.currency_code is already flexible")
            return

        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")
        conn.execute("ALTER TABLE company_bank_accounts RENAME TO company_bank_accounts_old")
        conn.execute(
            """
            CREATE TABLE company_bank_accounts (
                company_id INTEGER,
                bank_id INTEGER NOT NULL,
                currency_code VARCHAR(32),
                account_name VARCHAR(255),
                iban VARCHAR(64),
                account_number VARCHAR(64),
                bic VARCHAR(32),
                bank_branch VARCHAR(255),
                is_primary BOOLEAN NOT NULL,
                is_active BOOLEAN NOT NULL,
                opened_at DATE,
                closed_at DATE,
                id INTEGER NOT NULL PRIMARY KEY,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY(company_id) REFERENCES companies (id),
                FOREIGN KEY(bank_id) REFERENCES banks (id)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO company_bank_accounts (
                company_id,
                bank_id,
                currency_code,
                account_name,
                iban,
                account_number,
                bic,
                bank_branch,
                is_primary,
                is_active,
                opened_at,
                closed_at,
                id,
                created_at,
                updated_at
            )
            SELECT
                company_id,
                bank_id,
                currency_code,
                account_name,
                iban,
                account_number,
                bic,
                bank_branch,
                is_primary,
                is_active,
                opened_at,
                closed_at,
                id,
                created_at,
                updated_at
            FROM company_bank_accounts_old
            """
        )
        conn.execute("DROP TABLE company_bank_accounts_old")
        conn.execute("CREATE INDEX ix_company_bank_accounts_bank_id ON company_bank_accounts (bank_id)")
        conn.execute("CREATE INDEX ix_company_bank_accounts_company_id ON company_bank_accounts (company_id)")
        conn.commit()
        print("company_bank_accounts.currency_code is now nullable and free-form")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()


if __name__ == "__main__":
    main()
