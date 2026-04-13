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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BigIntPrimaryKeyMixin, TimestampMixin
from app.models.enums import (
    ClientBalanceEntryType,
    CommissionType,
    LedgerAccountPurpose,
    LedgerAccountType,
    LedgerEntryKind,
    LedgerEntryStatus,
)

if TYPE_CHECKING:
    from app.models.banking import Payment


def enum_values(enum_cls: type) -> list[str]:
    return [item.value for item in enum_cls]


class PaymentSettlementRuleSnapshot(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_settlement_rules_snapshot"

    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False, unique=True)
    vat_applied: Mapped[bool | None] = mapped_column(Boolean)
    vat_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    vat_calculated_from_gross: Mapped[bool | None] = mapped_column(Boolean)
    company_commission_applied: Mapped[bool | None] = mapped_column(Boolean)
    company_commission_type: Mapped[CommissionType | None] = mapped_column(
        Enum(CommissionType, native_enum=False, length=16, values_callable=enum_values)
    )
    company_commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    company_commission_fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    client_commission_applied: Mapped[bool | None] = mapped_column(Boolean)
    client_commission_type: Mapped[CommissionType | None] = mapped_column(
        Enum(CommissionType, native_enum=False, length=16, values_callable=enum_values)
    )
    client_commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    client_commission_fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    custom_rule_code: Mapped[str | None] = mapped_column(String(64))
    rule_description: Mapped[str | None] = mapped_column(Text)

    payment: Mapped["Payment"] = relationship(back_populates="settlement_rule_snapshot")


class PaymentFinancialBreakdown(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_financial_breakdown"
    __table_args__ = (
        CheckConstraint("vat_amount_eur <= gross_amount_eur", name="ck_breakdown_vat_not_above_gross_eur"),
    )

    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False, unique=True)
    gross_amount_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    gross_amount_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    vat_amount_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    vat_amount_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    base_after_vat_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    base_after_vat_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    company_commission_amount_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    company_commission_amount_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    client_commission_amount_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    client_commission_amount_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    net_client_balance_effect_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    payment: Mapped["Payment"] = relationship(back_populates="financial_breakdown")


class ClientBalanceLedger(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "client_balance_ledger"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), index=True)
    ledger_entry_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_entries.id"), index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_type: Mapped[ClientBalanceEntryType] = mapped_column(
        Enum(ClientBalanceEntryType, native_enum=False, length=32, values_callable=enum_values),
        nullable=False,
    )
    amount_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class LedgerAccount(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ledger_accounts"
    __table_args__ = (UniqueConstraint("company_id", "account_code", name="uq_ledger_accounts_company_code"),)

    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    account_code: Mapped[str] = mapped_column(String(32), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[LedgerAccountType] = mapped_column(
        Enum(LedgerAccountType, native_enum=False, length=16, values_callable=enum_values),
        nullable=False,
    )
    purpose_code: Mapped[LedgerAccountPurpose] = mapped_column(
        Enum(LedgerAccountPurpose, native_enum=False, length=32, values_callable=enum_values),
        nullable=False,
    )
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    postings: Mapped[list["LedgerPosting"]] = relationship(back_populates="ledger_account")


class LedgerEntry(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ledger_entries"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_kind: Mapped[LedgerEntryKind] = mapped_column(
        Enum(LedgerEntryKind, native_enum=False, length=32, values_callable=enum_values),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)
    reference_number: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[LedgerEntryStatus] = mapped_column(
        Enum(LedgerEntryStatus, native_enum=False, length=16, values_callable=enum_values),
        nullable=False,
        default=LedgerEntryStatus.DRAFT,
    )

    postings: Mapped[list["LedgerPosting"]] = relationship(back_populates="ledger_entry")


class LedgerPosting(BigIntPrimaryKeyMixin, Base):
    __tablename__ = "ledger_postings"
    __table_args__ = (
        CheckConstraint(
            "(debit_amount_eur > 0 AND credit_amount_eur = 0) "
            "OR (credit_amount_eur > 0 AND debit_amount_eur = 0)",
            name="ck_ledger_postings_single_side_amount",
        ),
    )

    ledger_entry_id: Mapped[int] = mapped_column(ForeignKey("ledger_entries.id"), nullable=False, index=True)
    ledger_account_id: Mapped[int] = mapped_column(ForeignKey("ledger_accounts.id"), nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), index=True)
    counterparty_id: Mapped[int | None] = mapped_column(ForeignKey("counterparties.id"), index=True)
    debit_amount_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    credit_amount_eur: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ledger_entry: Mapped["LedgerEntry"] = relationship(back_populates="postings")
    ledger_account: Mapped["LedgerAccount"] = relationship(back_populates="postings")
