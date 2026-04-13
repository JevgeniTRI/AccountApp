# Architecture

The project starts on `SQLite` for development speed and keeps the schema portable enough to move to `MySQL` later.

## Design rules

- Backend keeps business rules out of raw bank import tables.
- Accounting uses a double-entry layer separate from client balance projections.
- Payment classification is binary at the domain level: `client_payment` or `expense`.
- Frontend is intentionally postponed until backend workflows and schema settle.

## Persistence layers

1. Raw bank imports
2. Normalized payments
3. Payment settlement snapshots and calculated breakdowns
4. Accounting ledger and client balance ledger

## Note about `exchange_rates`

The shared database design explicitly references `exchange_rates` but does not include its column list. The initial model in this repository infers a conservative structure from the stated requirements:

- original currency
- target currency
- rate date
- rate value
- source metadata

That table should be finalized once the business rules for FX sourcing are confirmed.
