from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import BigIntPrimaryKeyMixin, TimestampMixin


class Company(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(128))
    registration_number: Mapped[str | None] = mapped_column(String(64))
    vat_number: Mapped[str | None] = mapped_column(String(64))
    country_code: Mapped[str | None] = mapped_column(String(2))
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(128))
    postal_code: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str | None] = mapped_column(String(32))

    contacts: Mapped[list["CompanyContact"]] = relationship(back_populates="company")
    bank_accounts: Mapped[list["CompanyBankAccount"]] = relationship(back_populates="company")
    company_clients: Mapped[list["CompanyClient"]] = relationship(back_populates="company")


class CompanyContact(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "company_contacts"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    company: Mapped["Company"] = relationship(back_populates="contacts")
    responsible_for_clients: Mapped[list["CompanyClient"]] = relationship(back_populates="responsible_contact")


class Bank(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "banks"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(128))
    swift_code: Mapped[str | None] = mapped_column(String(32))
    country_code: Mapped[str | None] = mapped_column(String(2))
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(128))
    postal_code: Mapped[str | None] = mapped_column(String(32))
    website: Mapped[str | None] = mapped_column(String(255))

    company_bank_accounts: Mapped[list["CompanyBankAccount"]] = relationship(back_populates="bank")


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    numeric_code: Mapped[str | None] = mapped_column(String(3))
    minor_units: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CompanyBankAccount(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "company_bank_accounts"

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("banks.id"), nullable=False, index=True)
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"), nullable=False)
    account_name: Mapped[str | None] = mapped_column(String(255))
    iban: Mapped[str | None] = mapped_column(String(64))
    account_number: Mapped[str | None] = mapped_column(String(64))
    bic: Mapped[str | None] = mapped_column(String(32))
    bank_branch: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    opened_at: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[date | None] = mapped_column(Date)

    company: Mapped["Company"] = relationship(back_populates="bank_accounts")
    bank: Mapped["Bank"] = relationship(back_populates="company_bank_accounts")
    currency: Mapped["Currency"] = relationship()


class Client(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clients"

    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    middle_name: Mapped[str | None] = mapped_column(String(128))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    personal_id_number: Mapped[str | None] = mapped_column(String(64))
    country_code: Mapped[str | None] = mapped_column(String(2))
    tax_residency_country_code: Mapped[str | None] = mapped_column(String(2))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(128))
    postal_code: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(32))

    companies: Mapped[list["CompanyClient"]] = relationship(back_populates="client")
    counterparties: Mapped[list["Counterparty"]] = relationship(back_populates="client")


class CompanyClient(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "company_clients"
    __table_args__ = (UniqueConstraint("company_id", "client_id", name="uq_company_clients_company_client"),)

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    responsible_contact_id: Mapped[int | None] = mapped_column(ForeignKey("company_contacts.id"))
    relationship_start_date: Mapped[date | None] = mapped_column(Date)
    relationship_end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)

    company: Mapped["Company"] = relationship(back_populates="company_clients")
    client: Mapped["Client"] = relationship(back_populates="companies")
    responsible_contact: Mapped["CompanyContact | None"] = relationship(back_populates="responsible_for_clients")


class Counterparty(BigIntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "counterparties"

    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(128))
    registration_number: Mapped[str | None] = mapped_column(String(64))
    vat_number: Mapped[str | None] = mapped_column(String(64))
    country_code: Mapped[str | None] = mapped_column(String(2))
    address_line1: Mapped[str | None] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(128))
    postal_code: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    website: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(32))

    client: Mapped["Client"] = relationship(back_populates="counterparties")
