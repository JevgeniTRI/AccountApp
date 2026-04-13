from __future__ import annotations

import base64
import binascii
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import PaymentFinancialBreakdown
from app.models.banking import Payment, PaymentAttachment
from app.models.enums import PaymentDirection, PaymentKind, PaymentStatus
from app.models.reference import Bank, Client, Company, CompanyBankAccount, CompanyClient, Counterparty, Currency
from app.schemas.payments import PaymentCreateRequest

MAX_PAYMENT_ATTACHMENT_BYTES = 10 * 1024 * 1024


class PaymentValidationError(Exception):
    pass


async def list_payments(
    db: AsyncSession,
    *,
    date_from: date | None,
    date_to: date | None,
    search: str | None,
    company_id: int | None,
    bank_id: int | None,
    currency_code: str | None,
    client_id: int | None,
    include_incoming: bool,
    include_outgoing: bool,
    limit: int,
    offset: int,
) -> tuple[int, list[dict]]:
    if not include_incoming and not include_outgoing:
        return 0, []

    company_name = func.coalesce(Company.short_name, Company.legal_name)
    counterparty_name = func.coalesce(Counterparty.short_name, Counterparty.legal_name)

    stmt = (
        select(
            Payment.id,
            Payment.booking_date,
            Payment.value_date,
            Payment.transaction_date,
            Payment.amount_original,
            Payment.amount_eur,
            Payment.currency_code,
            Payment.payment_direction,
            Payment.payment_kind,
            Payment.status,
            Payment.payment_reference,
            Payment.payment_purpose,
            Payment.notes,
            Payment.created_at,
            Payment.company_id,
            company_name.label("company_name"),
            Bank.id.label("bank_id"),
            Bank.name.label("bank_name"),
            Counterparty.id.label("counterparty_id"),
            counterparty_name.label("counterparty_name"),
            Client.id.label("client_id"),
            Client.full_name.label("client_name"),
            PaymentFinancialBreakdown.vat_amount_eur,
            PaymentFinancialBreakdown.company_commission_amount_eur,
        )
        .join(Company, Company.id == Payment.company_id)
        .join(CompanyBankAccount, CompanyBankAccount.id == Payment.company_bank_account_id)
        .join(Bank, Bank.id == CompanyBankAccount.bank_id)
        .outerjoin(Client, Client.id == Payment.client_id)
        .outerjoin(Counterparty, Counterparty.id == Payment.counterparty_id)
        .outerjoin(PaymentFinancialBreakdown, PaymentFinancialBreakdown.payment_id == Payment.id)
    )

    conditions = []
    if date_from is not None:
        conditions.append(Payment.booking_date >= date_from)
    if date_to is not None:
        conditions.append(Payment.booking_date <= date_to)
    if company_id is not None:
        conditions.append(Payment.company_id == company_id)
    if bank_id is not None:
        conditions.append(CompanyBankAccount.bank_id == bank_id)
    if currency_code is not None:
        conditions.append(Payment.currency_code == currency_code.upper())
    if client_id is not None:
        conditions.append(Payment.client_id == client_id)

    if include_incoming and not include_outgoing:
        conditions.append(Payment.payment_direction == PaymentDirection.INCOMING)
    elif include_outgoing and not include_incoming:
        conditions.append(Payment.payment_direction == PaymentDirection.OUTGOING)

    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Company.legal_name.ilike(pattern),
                Company.short_name.ilike(pattern),
                Bank.name.ilike(pattern),
                Counterparty.legal_name.ilike(pattern),
                Counterparty.short_name.ilike(pattern),
                Client.full_name.ilike(pattern),
                Payment.payment_reference.ilike(pattern),
                Payment.payment_purpose.ilike(pattern),
                Payment.notes.ilike(pattern),
            )
        )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int((await db.execute(count_stmt)).scalar_one())

    result = await db.execute(stmt.order_by(Payment.booking_date.desc(), Payment.id.desc()).limit(limit).offset(offset))
    rows = [dict(row._mapping) for row in result]

    payment_ids = [row["id"] for row in rows]
    attachments_by_payment: dict[int, list[dict]] = defaultdict(list)
    if payment_ids:
        attachments_result = await db.execute(
            select(
                PaymentAttachment.id,
                PaymentAttachment.payment_id,
                PaymentAttachment.file_name,
                PaymentAttachment.content_type,
                PaymentAttachment.file_size,
            )
            .where(PaymentAttachment.payment_id.in_(payment_ids))
            .order_by(PaymentAttachment.id.asc())
        )
        for attachment_row in attachments_result:
            data = dict(attachment_row._mapping)
            attachments_by_payment[data["payment_id"]].append(data)

    for row in rows:
        row["attachments"] = attachments_by_payment.get(row["id"], [])
    return total, rows


async def create_payment(db: AsyncSession, payload: PaymentCreateRequest) -> Payment:
    company_bank_account = await db.get(CompanyBankAccount, payload.company_bank_account_id)
    if company_bank_account is None:
        raise PaymentValidationError("Company bank account not found")
    if not company_bank_account.is_active:
        raise PaymentValidationError("Company bank account is inactive")

    company = await db.get(Company, company_bank_account.company_id)
    if company is None:
        raise PaymentValidationError("Company not found for bank account")

    bank = await db.get(Bank, company_bank_account.bank_id)
    if bank is None:
        raise PaymentValidationError("Bank not found for bank account")

    currency = await db.get(Currency, company_bank_account.currency_code)
    if currency is None:
        raise PaymentValidationError("Currency not found for bank account")

    client = None
    counterparty = None
    payment_kind = PaymentKind.EXPENSE

    if payload.client_id is not None:
        client = await db.get(Client, payload.client_id)
        if client is None:
            raise PaymentValidationError("Client not found")
        payment_kind = PaymentKind.CLIENT_PAYMENT

        if payload.counterparty_id is not None:
            counterparty = await db.get(Counterparty, payload.counterparty_id)
            if counterparty is None:
                raise PaymentValidationError("Counterparty not found")
            if counterparty.client_id != client.id:
                raise PaymentValidationError("Counterparty does not belong to client")
        elif payload.counterparty_name:
            counterparty = await get_or_create_counterparty(db, client.id, payload.counterparty_name)
        else:
            raise PaymentValidationError("Client payment requires counterparty_id or counterparty_name")

        await ensure_company_client_link(db, company.id, client.id)
    else:
        if payload.counterparty_id is not None or payload.counterparty_name:
            raise PaymentValidationError("Expense payment cannot contain counterparty")

    amount_eur = payload.amount_eur
    if amount_eur is None:
        if currency.code == "EUR":
            amount_eur = payload.amount_original
        else:
            raise PaymentValidationError("amount_eur is required for non-EUR payments")

    validate_financial_breakdown(payload, amount_eur)

    payment = Payment(
        company_id=company.id,
        company_bank_account_id=company_bank_account.id,
        client_id=client.id if client else None,
        counterparty_id=counterparty.id if counterparty else None,
        payment_kind=payment_kind,
        payment_direction=payload.payment_direction,
        booking_date=payload.booking_date,
        value_date=payload.value_date,
        transaction_date=payload.transaction_date,
        amount_original=payload.amount_original,
        currency_code=currency.code,
        exchange_rate_id=payload.exchange_rate_id,
        exchange_rate_manual=payload.exchange_rate_manual,
        amount_eur=amount_eur,
        payment_reference=payload.payment_reference,
        payment_purpose=payload.payment_purpose,
        notes=payload.notes,
        status=PaymentStatus.PENDING_REVIEW,
        is_manual=True,
    )
    db.add(payment)
    await db.flush()
    await upsert_payment_financial_breakdown(db, payment=payment, payload=payload, currency_code=currency.code)
    await replace_payment_attachments(db, payment=payment, payload=payload)
    return payment


async def create_payments_batch(db: AsyncSession, payloads: list[PaymentCreateRequest]) -> list[Payment]:
    payments: list[Payment] = []
    for index, payload in enumerate(payloads, start=1):
        try:
            payments.append(await create_payment(db, payload))
        except PaymentValidationError as exc:
            raise PaymentValidationError(f"Row {index}: {exc}") from exc
    return payments


def validate_financial_breakdown(payload: PaymentCreateRequest, amount_eur: Decimal) -> None:
    if payload.vat_amount_eur > amount_eur:
        raise PaymentValidationError("vat_amount_eur cannot exceed amount_eur")


async def upsert_payment_financial_breakdown(
    db: AsyncSession,
    *,
    payment: Payment,
    payload: PaymentCreateRequest,
    currency_code: str,
) -> None:
    existing_result = await db.execute(
        select(PaymentFinancialBreakdown).where(PaymentFinancialBreakdown.payment_id == payment.id)
    )
    breakdown = existing_result.scalar_one_or_none()

    vat_amount_eur = payload.vat_amount_eur
    company_commission_amount_eur = payload.company_commission_amount_eur
    base_after_vat_eur = payment.amount_eur - vat_amount_eur
    gross_amount_original = payment.amount_original
    vat_amount_original = vat_amount_eur if currency_code == "EUR" else None
    base_after_vat_original = (
        payment.amount_original - vat_amount_original if vat_amount_original is not None else None
    )
    company_commission_amount_original = (
        company_commission_amount_eur if currency_code == "EUR" else None
    )

    values = {
        "gross_amount_original": gross_amount_original,
        "gross_amount_eur": payment.amount_eur,
        "vat_amount_original": vat_amount_original,
        "vat_amount_eur": vat_amount_eur,
        "base_after_vat_original": base_after_vat_original,
        "base_after_vat_eur": base_after_vat_eur,
        "company_commission_amount_original": company_commission_amount_original,
        "company_commission_amount_eur": company_commission_amount_eur,
        "client_commission_amount_original": None,
        "client_commission_amount_eur": Decimal("0"),
        "net_client_balance_effect_eur": base_after_vat_eur + company_commission_amount_eur,
    }

    if breakdown is None:
        db.add(PaymentFinancialBreakdown(payment_id=payment.id, **values))
        await db.flush()
        return

    for field_name, field_value in values.items():
        setattr(breakdown, field_name, field_value)


async def ensure_company_client_link(db: AsyncSession, company_id: int, client_id: int) -> None:
    result = await db.execute(
        select(CompanyClient).where(
            CompanyClient.company_id == company_id,
            CompanyClient.client_id == client_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is not None:
        return

    db.add(
        CompanyClient(
            company_id=company_id,
            client_id=client_id,
            status="active",
        )
    )
    await db.flush()


async def get_or_create_counterparty(db: AsyncSession, client_id: int, name: str) -> Counterparty:
    normalized_name = name.strip()
    result = await db.execute(
        select(Counterparty).where(
            Counterparty.client_id == client_id,
            func.lower(Counterparty.legal_name) == normalized_name.lower(),
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    counterparty = Counterparty(
        client_id=client_id,
        legal_name=normalized_name,
        status="active",
    )
    db.add(counterparty)
    await db.flush()
    return counterparty


async def replace_payment_attachments(
    db: AsyncSession,
    *,
    payment: Payment,
    payload: PaymentCreateRequest,
) -> None:
    result = await db.execute(select(PaymentAttachment).where(PaymentAttachment.payment_id == payment.id))
    for existing_attachment in result.scalars().all():
        await db.delete(existing_attachment)
    await db.flush()

    if not payload.attachments:
        return

    for attachment_payload in payload.attachments:
        try:
            file_content = base64.b64decode(attachment_payload.file_content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise PaymentValidationError("Attachment content is not valid base64") from exc

        if not file_content:
            raise PaymentValidationError("Attachment file is empty")
        if len(file_content) > MAX_PAYMENT_ATTACHMENT_BYTES:
            raise PaymentValidationError("Attachment file exceeds 10 MB limit")

        db.add(
            PaymentAttachment(
                payment_id=payment.id,
                file_name=attachment_payload.file_name.strip(),
                content_type=attachment_payload.content_type.strip() if attachment_payload.content_type else None,
                file_size=len(file_content),
                file_content=file_content,
            )
        )

    await db.flush()
