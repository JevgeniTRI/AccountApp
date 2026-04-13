from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import PaymentDirection
from app.schemas.payments import (
    PaymentBatchCreateRequest,
    PaymentBatchCreateResponse,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentListResponse,
    PaymentRow,
)
from app.services.payments import PaymentValidationError, create_payment, create_payments_batch, list_payments


router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=PaymentListResponse)
async def get_payments(
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    company_id: int | None = None,
    bank_id: int | None = None,
    currency_code: str | None = None,
    client_id: int | None = None,
    include_incoming: bool = True,
    include_outgoing: bool = True,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    total, rows = await list_payments(
        db,
        date_from=date_from,
        date_to=date_to,
        search=search,
        company_id=company_id,
        bank_id=bank_id,
        currency_code=currency_code,
        client_id=client_id,
        include_incoming=include_incoming,
        include_outgoing=include_outgoing,
        limit=limit,
        offset=offset,
    )

    items = []
    for row in rows:
        signed_amount = row["amount_original"]
        if row["payment_direction"] == PaymentDirection.OUTGOING:
            signed_amount = Decimal("-1") * row["amount_original"]

        items.append(
            PaymentRow(
                id=row["id"],
                booking_date=row["booking_date"],
                value_date=row["value_date"],
                transaction_date=row["transaction_date"],
                company={"id": row["company_id"], "name": row["company_name"]},
                bank={"id": row["bank_id"], "name": row["bank_name"]},
                counterparty={"id": row["counterparty_id"], "name": row["counterparty_name"]},
                client={"id": row["client_id"], "name": row["client_name"]},
                amount_original=row["amount_original"],
                signed_amount=signed_amount,
                amount_eur=row["amount_eur"],
                currency_code=row["currency_code"],
                vat_amount_eur=row["vat_amount_eur"],
                income_expense_eur=row["company_commission_amount_eur"],
                payment_direction=row["payment_direction"],
                payment_kind=row["payment_kind"],
                status=row["status"],
                payment_reference=row["payment_reference"],
                payment_purpose=row["payment_purpose"],
                notes=row["notes"],
                created_at=row["created_at"],
            )
        )

    return PaymentListResponse(total=total, items=items)


@router.post("", response_model=PaymentCreateResponse, status_code=201)
async def post_payment(payload: PaymentCreateRequest, db: AsyncSession = Depends(get_db)) -> PaymentCreateResponse:
    try:
        payment = await create_payment(db, payload)
        await db.commit()
    except PaymentValidationError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create payment") from exc

    return PaymentCreateResponse(
        id=payment.id,
        payment_kind=payment.payment_kind,
        payment_direction=payment.payment_direction,
        company_bank_account_id=payment.company_bank_account_id,
    )


@router.post("/batch", response_model=PaymentBatchCreateResponse, status_code=201)
async def post_payments_batch(
    payload: PaymentBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> PaymentBatchCreateResponse:
    try:
        payments = await create_payments_batch(db, payload.items)
        await db.commit()
    except PaymentValidationError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create payments") from exc

    return PaymentBatchCreateResponse(
        items=[
            PaymentCreateResponse(
                id=payment.id,
                payment_kind=payment.payment_kind,
                payment_direction=payment.payment_direction,
                company_bank_account_id=payment.company_bank_account_id,
            )
            for payment in payments
        ]
    )
