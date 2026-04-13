from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PaymentDirection, PaymentKind, PaymentStatus


class PaymentPartySummary(BaseModel):
    id: int | None = None
    name: str | None = None


class PaymentBankSummary(BaseModel):
    id: int
    name: str


class PaymentAttachmentSummary(BaseModel):
    id: int
    file_name: str
    content_type: str | None = None
    file_size: int


class PaymentRow(BaseModel):
    id: int
    booking_date: date | None = None
    value_date: date | None = None
    transaction_date: date | None = None
    company: PaymentPartySummary
    bank: PaymentBankSummary
    counterparty: PaymentPartySummary
    client: PaymentPartySummary
    amount_original: Decimal
    signed_amount: Decimal
    amount_eur: Decimal
    currency_code: str
    vat_amount_eur: Decimal | None = None
    income_expense_eur: Decimal | None = None
    payment_direction: PaymentDirection
    payment_kind: PaymentKind
    status: PaymentStatus
    payment_reference: str | None = None
    payment_purpose: str | None = None
    notes: str | None = None
    attachments: list[PaymentAttachmentSummary] = Field(default_factory=list)
    created_at: datetime


class PaymentListResponse(BaseModel):
    total: int
    items: list[PaymentRow]


class PaymentCreateRequest(BaseModel):
    company_bank_account_id: int
    booking_date: date
    value_date: date | None = None
    transaction_date: date | None = None
    amount_original: Decimal = Field(gt=0)
    amount_eur: Decimal | None = Field(default=None, gt=0)
    vat_amount_eur: Decimal = Field(default=Decimal("0"), ge=0)
    company_commission_amount_eur: Decimal = Decimal("0")
    payment_direction: PaymentDirection
    client_id: int | None = None
    counterparty_id: int | None = None
    counterparty_name: str | None = Field(default=None, max_length=255)
    payment_reference: str | None = Field(default=None, max_length=255)
    payment_purpose: str | None = None
    notes: str | None = None
    exchange_rate_id: int | None = None
    exchange_rate_manual: Decimal | None = None
    attachments: list["PaymentAttachmentCreateRequest"] = Field(default_factory=list, max_length=20)


class PaymentAttachmentCreateRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=128)
    file_content_base64: str = Field(min_length=1)


class PaymentCreateResponse(BaseModel):
    id: int
    payment_kind: PaymentKind
    payment_direction: PaymentDirection
    company_bank_account_id: int


class PaymentBatchCreateRequest(BaseModel):
    items: list[PaymentCreateRequest] = Field(min_length=1, max_length=500)


class PaymentBatchCreateResponse(BaseModel):
    items: list[PaymentCreateResponse]


PaymentCreateRequest.model_rebuild()
