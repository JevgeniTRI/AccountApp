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
        cursor = conn.execute("PRAGMA table_info(company_bank_accounts)")
        columns = cursor.fetchall()
        company_id_info = next((row for row in columns if row[1] == "company_id"), None)
        if company_id_info is None:
            raise RuntimeError("company_id column not found in company_bank_accounts")
        if company_id_info[3] == 0:
            print("company_bank_accounts.company_id is already nullable")
            return

        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")
        conn.execute("ALTER TABLE company_bank_accounts RENAME TO company_bank_accounts_old")
        conn.execute(
            """
            CREATE TABLE company_bank_accounts (
                company_id INTEGER,
                bank_id INTEGER NOT NULL,
                currency_code VARCHAR(3) NOT NULL,
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
                FOREIGN KEY(bank_id) REFERENCES banks (id),
                FOREIGN KEY(currency_code) REFERENCES currencies (code)
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
        conn.execute(
            "CREATE INDEX ix_company_bank_accounts_bank_id ON company_bank_accounts (bank_id)"
        )
        conn.execute(
            "CREATE INDEX ix_company_bank_accounts_company_id ON company_bank_accounts (company_id)"
        )
        conn.commit()
        print("company_bank_accounts.company_id is now nullable")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()


if __name__ == "__main__":
    main()
