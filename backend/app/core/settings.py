from pathlib import Path
from decimal import Decimal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Accounting App API"
    database_url: str = "sqlite:///./accounting.db"
    cors_allow_origins_raw: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    cbr_daily_rates_url: str = "https://www.cbr.ru/scripts/XML_daily.asp"
    cbr_source_name: str = "cbr.ru"
    cbr_target_codes_raw: str = "USD,EUR"
    cbr_rate_scale: Decimal = Decimal("0.00000001")
    currency_rub_code: str = "RUB"
    currency_rub_name: str = "Russian Ruble"
    currency_rub_numeric_code: str = "643"
    currency_rub_minor_units: int = 2
    currency_usd_code: str = "USD"
    currency_usd_name: str = "US Dollar"
    currency_usd_numeric_code: str = "840"
    currency_usd_minor_units: int = 2
    currency_eur_code: str = "EUR"
    currency_eur_name: str = "Euro"
    currency_eur_numeric_code: str = "978"
    currency_eur_minor_units: int = 2

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        if not value.startswith("sqlite:///"):
            return value

        suffix = value.removeprefix("sqlite:///")
        if suffix == ":memory:":
            return value

        path = Path(suffix)
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()

        return f"sqlite:///{path.as_posix()}"

    @property
    def cbr_target_codes(self) -> tuple[str, ...]:
        return tuple(item.upper() for item in self.parse_csv(self.cbr_target_codes_raw))

    @property
    def async_database_url(self) -> str:
        if self.database_url.startswith("sqlite:///"):
            return self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return self.database_url

    @property
    def cors_allow_origins(self) -> list[str]:
        return list(self.parse_csv(self.cors_allow_origins_raw))

    @classmethod
    def parse_csv(cls, value: str | tuple[str, ...] | list[str]) -> tuple[str, ...]:
        if isinstance(value, tuple):
            return value
        if isinstance(value, list):
            return tuple(value)
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        return tuple(value)


settings = Settings()
