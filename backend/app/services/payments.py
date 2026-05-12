from __future__ import annotations

import base64
import binascii
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.accounting import PaymentFinancialBreakdown
from app.models.accounting import ClientBalanceLedger, LedgerEntry, LedgerPosting, PaymentSettlementRuleSnapshot
from app.models.banking import Payment, PaymentAttachment
from app.models.enums import PaymentDirection, PaymentKind, PaymentStatus
from app.models.reference import Bank, Client, Company, CompanyBankAccount, CompanyClient, Counterparty
from app.schemas.payments import PaymentCreateRequest, PaymentDetailResponse, PaymentPartySummary
from app.schemas.reference import BankAccountLookupItem
from app.services.reference import format_bank_display_name, format_company_display_name

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
    related_company = aliased(Company)
    related_company_name = func.coalesce(related_company.short_name, related_company.legal_name)
    counterparty_name = func.coalesce(Payment.counterparty_name, Counterparty.short_name, Counterparty.legal_name)

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
            Payment.related_company_id,
            related_company_name.label("related_company_name"),
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
        .outerjoin(related_company, related_company.id == Payment.related_company_id)
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
                related_company.legal_name.ilike(pattern),
                related_company.short_name.ilike(pattern),
                Bank.name.ilike(pattern),
                Payment.counterparty_name.ilike(pattern),
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
    resolved = await resolve_payment_payload(db, payload)

    validate_financial_breakdown(payload, resolved["amount_eur"])

    payment = Payment(
        company_id=resolved["company"].id,
        company_bank_account_id=resolved["company_bank_account"].id,
        related_company_id=resolved["related_company"].id if resolved["related_company"] else None,
        client_id=resolved["client"].id if resolved["client"] else None,
        counterparty_id=resolved["counterparty"].id if resolved["counterparty"] else None,
        counterparty_name=resolved["counterparty_name"],
        payment_kind=resolved["payment_kind"],
        payment_direction=payload.payment_direction,
        booking_date=payload.booking_date,
        value_date=payload.value_date,
        transaction_date=payload.transaction_date,
        amount_original=payload.amount_original,
        currency_code=resolved["currency_code"],
        exchange_rate_id=payload.exchange_rate_id,
        exchange_rate_manual=payload.exchange_rate_manual,
        amount_eur=resolved["amount_eur"],
        payment_reference=payload.payment_reference,
        payment_purpose=payload.payment_purpose,
        notes=payload.notes,
        status=PaymentStatus.PENDING_REVIEW,
        is_manual=True,
    )
    db.add(payment)
    await db.flush()
    await upsert_payment_financial_breakdown(db, payment=payment, payload=payload, currency_code=resolved["currency_code"])
    await replace_payment_attachments(db, payment=payment, payload=payload)
    return payment


async def get_payment_detail(db: AsyncSession, payment_id: int) -> PaymentDetailResponse | None:
    payment = await db.get(Payment, payment_id)
    if payment is None:
        return None

    company_bank_account = await db.get(CompanyBankAccount, payment.company_bank_account_id)
    if company_bank_account is None:
        raise PaymentValidationError("Company bank account not found")

    company = await db.get(Company, payment.company_id)
    bank = await db.get(Bank, company_bank_account.bank_id)
    if company is None or bank is None:
        raise PaymentValidationError("Failed to resolve payment references")

    related_company = await db.get(Company, payment.related_company_id) if payment.related_company_id else None
    client = await db.get(Client, payment.client_id) if payment.client_id else None
    counterparty = await db.get(Counterparty, payment.counterparty_id) if payment.counterparty_id else None

    breakdown_result = await db.execute(
        select(PaymentFinancialBreakdown).where(PaymentFinancialBreakdown.payment_id == payment.id)
    )
    breakdown = breakdown_result.scalar_one_or_none()

    attachments_result = await db.execute(
        select(PaymentAttachment)
        .where(PaymentAttachment.payment_id == payment.id)
        .order_by(PaymentAttachment.id.asc())
    )
    attachments = list(attachments_result.scalars().all())

    account_reference = (
        company_bank_account.iban or company_bank_account.account_number or f"Account #{company_bank_account.id}"
    )
    currency_label = company_bank_account.currency_code or "-"

    return PaymentDetailResponse(
        id=payment.id,
        company_bank_account=BankAccountLookupItem(
            id=company_bank_account.id,
            label=(
                f"{format_company_display_name(company)} | "
                f"{format_bank_display_name(bank)} | "
                f"{currency_label} | {account_reference}"
            ),
            company_id=company.id,
            company_name=format_company_display_name(company),
            bank_id=bank.id,
            bank_name=format_bank_display_name(bank),
            currency_code=company_bank_account.currency_code,
        ),
        booking_date=payment.booking_date,
        value_date=payment.value_date,
        transaction_date=payment.transaction_date,
        amount_original=payment.amount_original,
        amount_eur=payment.amount_eur,
        vat_amount_eur=breakdown.vat_amount_eur if breakdown is not None else None,
        company_commission_amount_eur=(
            breakdown.company_commission_amount_eur if breakdown is not None else None
        ),
        payment_direction=payment.payment_direction,
        payment_kind=payment.payment_kind,
        status=payment.status,
        related_company=PaymentPartySummary(
            id=related_company.id if related_company is not None else None,
            name=format_company_display_name(related_company) if related_company is not None else None,
        ),
        counterparty=PaymentPartySummary(
            id=counterparty.id if counterparty is not None else None,
            name=(
                payment.counterparty_name or get_counterparty_display_name(counterparty)
                if counterparty is not None
                else payment.counterparty_name
            ),
        ),
        client=PaymentPartySummary(
            id=client.id if client is not None else None,
            name=client.full_name if client is not None else None,
        ),
        payment_reference=payment.payment_reference,
        payment_purpose=payment.payment_purpose,
        notes=payment.notes,
        attachments=[
            {
                "id": attachment.id,
                "file_name": attachment.file_name,
                "content_type": attachment.content_type,
                "file_size": attachment.file_size,
            }
            for attachment in attachments
        ],
        created_at=payment.created_at,
    )


async def update_payment(db: AsyncSession, payment_id: int, payload: PaymentCreateRequest) -> Payment:
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise PaymentValidationError("Payment not found")

    resolved = await resolve_payment_payload(db, payload)

    validate_financial_breakdown(payload, resolved["amount_eur"])

    payment.company_id = resolved["company"].id
    payment.company_bank_account_id = resolved["company_bank_account"].id
    payment.related_company_id = resolved["related_company"].id if resolved["related_company"] else None
    payment.client_id = resolved["client"].id if resolved["client"] else None
    payment.counterparty_id = resolved["counterparty"].id if resolved["counterparty"] else None
    payment.counterparty_name = resolved["counterparty_name"]
    payment.payment_kind = resolved["payment_kind"]
    payment.payment_direction = payload.payment_direction
    payment.booking_date = payload.booking_date
    payment.value_date = payload.value_date
    payment.transaction_date = payload.transaction_date
    payment.amount_original = payload.amount_original
    payment.currency_code = resolved["currency_code"]
    payment.exchange_rate_id = payload.exchange_rate_id
    payment.exchange_rate_manual = payload.exchange_rate_manual
    payment.amount_eur = resolved["amount_eur"]
    payment.payment_reference = payload.payment_reference
    payment.payment_purpose = payload.payment_purpose
    payment.notes = payload.notes
    payment.status = PaymentStatus.PENDING_REVIEW

    await db.flush()
    await upsert_payment_financial_breakdown(db, payment=payment, payload=payload, currency_code=resolved["currency_code"])
    await replace_payment_attachments(db, payment=payment, payload=payload)
    return payment


async def delete_payment(db: AsyncSession, payment_id: int) -> None:
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise PaymentValidationError("Payment not found")

    attachments_result = await db.execute(
        select(PaymentAttachment).where(PaymentAttachment.payment_id == payment.id)
    )
    for attachment in attachments_result.scalars().all():
        await db.delete(attachment)

    breakdown_result = await db.execute(
        select(PaymentFinancialBreakdown).where(PaymentFinancialBreakdown.payment_id == payment.id)
    )
    breakdown = breakdown_result.scalar_one_or_none()
    if breakdown is not None:
        await db.delete(breakdown)

    snapshot_result = await db.execute(
        select(PaymentSettlementRuleSnapshot).where(PaymentSettlementRuleSnapshot.payment_id == payment.id)
    )
    snapshot = snapshot_result.scalar_one_or_none()
    if snapshot is not None:
        await db.delete(snapshot)

    balance_entries_result = await db.execute(
        select(ClientBalanceLedger).where(ClientBalanceLedger.payment_id == payment.id)
    )
    for entry in balance_entries_result.scalars().all():
        await db.delete(entry)

    ledger_entries_result = await db.execute(
        select(LedgerEntry).where(LedgerEntry.payment_id == payment.id)
    )
    for ledger_entry in ledger_entries_result.scalars().all():
        postings_result = await db.execute(
            select(LedgerPosting).where(LedgerPosting.ledger_entry_id == ledger_entry.id)
        )
        for posting in postings_result.scalars().all():
            await db.delete(posting)
        await db.delete(ledger_entry)

    await db.delete(payment)


async def create_payments_batch(db: AsyncSession, payloads: list[PaymentCreateRequest]) -> list[Payment]:
    payments: list[Payment] = []
    for index, payload in enumerate(payloads, start=1):
        try:
            payments.append(await create_payment(db, payload))
        except PaymentValidationError as exc:
            raise PaymentValidationError(f"Row {index}: {exc}") from exc
    return payments


async def resolve_payment_payload(db: AsyncSession, payload: PaymentCreateRequest) -> dict:
    company_bank_account = await db.get(CompanyBankAccount, payload.company_bank_account_id)
    if company_bank_account is None:
        raise PaymentValidationError("Company bank account not found")
    if not company_bank_account.is_active:
        raise PaymentValidationError("Company bank account is inactive")
    if company_bank_account.company_id is None:
        raise PaymentValidationError("Company is not set for bank account")

    company = await db.get(Company, company_bank_account.company_id)
    if company is None:
        raise PaymentValidationError("Company not found for bank account")

    bank = await db.get(Bank, company_bank_account.bank_id)
    if bank is None:
        raise PaymentValidationError("Bank not found for bank account")

    currency_code = (company_bank_account.currency_code or "").strip().upper()
    if not currency_code:
        raise PaymentValidationError("Currency is not set for bank account")

    related_company = None
    if payload.related_company_id is not None:
        related_company = await db.get(Company, payload.related_company_id)
        if related_company is None:
            raise PaymentValidationError("Related company not found")
        if related_company.id == company.id:
            raise PaymentValidationError("Related company must differ from the bank account company")

    client = None
    counterparty = None
    counterparty_name = payload.counterparty_name.strip() if payload.counterparty_name else None
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
            counterparty_name = get_counterparty_display_name(counterparty)
        elif payload.counterparty_name:
            counterparty = await get_or_create_counterparty(db, client.id, payload.counterparty_name)
            counterparty_name = get_counterparty_display_name(counterparty)
        else:
            raise PaymentValidationError("Client payment requires counterparty_id or counterparty_name")

        await ensure_company_client_link(db, company.id, client.id)
    else:
        if payload.counterparty_id is not None:
            raise PaymentValidationError("counterparty_id requires client_id")

    amount_eur = payload.amount_eur
    if amount_eur is None:
        if currency_code == "EUR":
            amount_eur = payload.amount_original
        else:
            raise PaymentValidationError("amount_eur is required for non-EUR payments")

    return {
        "company_bank_account": company_bank_account,
        "company": company,
        "bank": bank,
        "currency_code": currency_code,
        "related_company": related_company,
        "client": client,
        "counterparty": counterparty,
        "counterparty_name": counterparty_name,
        "payment_kind": payment_kind,
        "amount_eur": amount_eur,
    }


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


def get_counterparty_display_name(counterparty: Counterparty) -> str:
    return (counterparty.short_name or counterparty.legal_name).strip()


async def replace_payment_attachments(
    db: AsyncSession,
    *,
    payment: Payment,
    payload: PaymentCreateRequest,
) -> None:
    result = await db.execute(select(PaymentAttachment).where(PaymentAttachment.payment_id == payment.id))
    existing_attachments = list(result.scalars().all())
    keep_attachment_ids = set(payload.keep_attachment_ids)

    for existing_attachment in existing_attachments:
        if existing_attachment.id not in keep_attachment_ids:
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
