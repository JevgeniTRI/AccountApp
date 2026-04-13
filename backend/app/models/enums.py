from enum import StrEnum


class PaymentKind(StrEnum):
    CLIENT_PAYMENT = "client_payment"
    EXPENSE = "expense"


class PaymentDirection(StrEnum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class PaymentStatus(StrEnum):
    IMPORTED = "imported"
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    POSTED = "posted"
    CANCELLED = "cancelled"


class ExpenseCategory(StrEnum):
    BANK_FEE = "bank_fee"
    SALARY = "salary"
    RENT = "rent"
    OTHER = "other"


class CommissionType(StrEnum):
    FIXED = "fixed"
    PERCENT = "percent"
    CONDITIONAL = "conditional"


class ClientBalanceEntryType(StrEnum):
    ACCRUAL = "accrual"
    PAYOUT = "payout"
    COMPANY_COMMISSION = "company_commission"
    CLIENT_COMMISSION = "client_commission"
    VAT = "vat"
    CORRECTION = "correction"
    OPENING_BALANCE = "opening_balance"


class LedgerAccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    INCOME = "income"
    EXPENSE = "expense"
    CLEARING = "clearing"


class LedgerAccountPurpose(StrEnum):
    BANK = "bank"
    CLIENT_SETTLEMENT = "client_settlement"
    COMPANY_COMMISSION_INCOME = "company_commission_income"
    CLIENT_COMMISSION_EXPENSE = "client_commission_expense"
    VAT = "vat"
    OPERATING_EXPENSE = "operating_expense"
    EXCHANGE_DIFF = "exchange_diff"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class LedgerEntryKind(StrEnum):
    CLIENT_PAYMENT = "client_payment"
    EXPENSE = "expense"
    CORRECTION = "correction"
    OPENING_BALANCE = "opening_balance"


class LedgerEntryStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    POSTED = "posted"
    CANCELLED = "cancelled"
