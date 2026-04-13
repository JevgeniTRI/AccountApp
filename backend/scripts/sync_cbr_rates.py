from __future__ import annotations

import argparse
import asyncio
from datetime import date

from app.db.session import SessionLocal, async_engine
from app.services.exchange_rates import sync_cbr_rub_rates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync RUB to EUR and RUB to USD rates from CBR.")
    parser.add_argument("--date", dest="rate_date", help="Rate date in YYYY-MM-DD format")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    rate_date = date.fromisoformat(args.rate_date) if args.rate_date else None

    db = SessionLocal()
    try:
        result = await sync_cbr_rub_rates(db=db, rate_date=rate_date)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()
        await async_engine.dispose()

    print(result.rate_date.isoformat())
    for item in result.items:
        print(
            f"{item.from_currency_code}->{item.to_currency_code}: "
            f"source_rub={item.source_rate_rub} stored_rate={item.stored_rate}"
        )


if __name__ == "__main__":
    asyncio.run(main())
