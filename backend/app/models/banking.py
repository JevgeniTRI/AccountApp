from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BigIntPrimaryKeyMixin, TimestampMixin
from app.models.enums import ExpenseCategory, PaymentDirection, PaymentKind, PaymentStatus

if TYPE_CHECKING:
    from app.models.accounting import PaymentFinancialBreakdown, PaymentSettlementRuleSnapshot


def enum_values(enum_cls: type) -> list[str]:
    return [item.value for item in enum_cls]


class BankStatement(BigIntPrimaryKeyMixin, Base):
    __tablename__ = "bank_statements"

    company_bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("company_bank_accounts.id"),
        nullable=False,
        index=True,
    )
    statement_number: Mapped[str | None] = mapped_column(String(64))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    opening_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    opening_balance_currency_code: Mapped[str | None] = mapped_column(ForeignKey("currencies.code"))
    closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    closing_balance_currency_code: Mapped[str | None] = mapped_column(ForeignKey("currencies.code"))
    source_file_name: Mapped[str | None] = mapped_column(String(255))
    source_file_hash: Mapped[str | None] = mapped_column(String(128))
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lines: Mapped[list["BankStatementLine"]] = relationship(back_populates="statement")


class BankStatementLine(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bank_statement_lines"

    statement_id: Mapped[int] = mapped_column(ForeignKey("bank_statements.id"), nullable=False, index=True)
    line_number: Mapped[int | None] = mapped_column()
    booking_date: Mapped[date | None] = mapped_column(Date)
    value_date: Mapped[date | None] = mapped_column(Date)
    transaction_date: Mapped[date | None] = mapped_column(Date)
    raw_description: Mapped[str | None] = mapped_column(Text)
    raw_reference: Mapped[str | None] = mapped_column(String(255))
    payer_name: Mapped[str | None] = mapped_column(String(255))
    payer_account: Mapped[str | None] = mapped_column(String(128))
    payer_bank_bic: Mapped[str | None] = mapped_column(String(32))
    payee_name: Mapped[str | None] = mapped_column(String(255))
    payee_account: Mapped[str | None] = mapped_column(String(128))
    payee_bank_bic: Mapped[str | None] = mapped_column(String(32))
    debit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    credit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency_code: Mapped[str | None] = mapped_column(ForeignKey("currencies.code"))
    balance_after_line: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    external_transaction_id: Mapped[str | None] = mapped_column(String(128))

    statement: Mapped["BankStatement"] = relationship(back_populates="lines")
    payment: Mapped["Payment | None"] = relationship(back_populates="bank_statement_line")


class ExchangeRate(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        CheckConstraint("rate_value > 0", name="ck_exchange_rates_rate_value_positive"),
        CheckConstraint(
            "from_currency_code <> to_currency_code",
            name="ck_exchange_rates_currency_pair_distinct",
        ),
        UniqueConstraint(
            "from_currency_code",
            "to_currency_code",
            "rate_date",
            "source_name",
            name="uq_exchange_rates_pair_date_source",
        ),
    )

    # The shared design references this table but does not list its columns.
    # These fields are inferred from the stated FX requirements.
    from_currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"), nullable=False)
    to_currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate_value: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255))
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Payment(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "(payment_kind = 'client_payment' AND client_id IS NOT NULL AND counterparty_id IS NOT NULL) "
            "OR (payment_kind = 'expense' AND client_id IS NULL AND counterparty_id IS NULL)",
            name="ck_payments_kind_party_consistency",
        ),
    )

    bank_statement_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_statement_lines.id"),
        unique=True,
    )
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    company_bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("company_bank_accounts.id"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), index=True)
    counterparty_id: Mapped[int | None] = mapped_column(ForeignKey("counterparties.id"), index=True)
    payment_kind: Mapped[PaymentKind] = mapped_column(
        Enum(PaymentKind, native_enum=False, length=32, values_callable=enum_values),
        nullable=False,
    )
    payment_direction: Mapped[PaymentDirection] = mapped_column(
        Enum(PaymentDirection, native_enum=False, length=16, values_callable=enum_values),
        nullable=False,
    )
    booking_date: Mapped[date | None] = mapped_column(Date)
    value_date: Mapped[date | None] = mapped_column(Date)
    transaction_date: Mapped[date | None] = mapped_column(Date)
    amount_original: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"), nullable=False)
    exchange_rate_id: Mapped[int | None] = mapped_column(ForeignKey("exchange_rates.id"))
    exchange_rate_manual: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    amount_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payer_name: Mapped[str | None] = mapped_column(String(255))
    payer_account: Mapped[str | None] = mapped_column(String(128))
    payee_name: Mapped[str | None] = mapped_column(String(255))
    payee_account: Mapped[str | None] = mapped_column(String(128))
    payment_reference: Mapped[str | None] = mapped_column(String(255))
    payment_purpose: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=32, values_callable=enum_values),
        nullable=False,
        default=PaymentStatus.IMPORTED,
    )
    expense_category: Mapped[ExpenseCategory | None] = mapped_column(
        Enum(ExpenseCategory, native_enum=False, length=32, values_callable=enum_values),
    )
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    bank_statement_line: Mapped["BankStatementLine | None"] = relationship(back_populates="payment")
    exchange_rate: Mapped["ExchangeRate | None"] = relationship()
    settlement_rule_snapshot: Mapped["PaymentSettlementRuleSnapshot | None"] = relationship(
        back_populates="payment"
    )
    financial_breakdown: Mapped["PaymentFinancialBreakdown | None"] = relationship(back_populates="payment")
    attachments: Mapped[list["PaymentAttachment"]] = relationship(back_populates="payment")


class PaymentAttachment(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_attachments"

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))
    file_size: Mapped[int] = mapped_column(nullable=False)
    file_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    payment: Mapped["Payment"] = relationship(back_populates="attachments")
