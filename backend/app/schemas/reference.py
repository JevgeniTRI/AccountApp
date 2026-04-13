from datetime import date

from pydantic import BaseModel, Field


class LookupQuery(BaseModel):
    query: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class LookupItem(BaseModel):
    id: int
    label: str


class CurrencyLookupItem(BaseModel):
    code: str
    label: str


class CompanyCreateRequest(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    short_name: str | None = Field(default=None, max_length=128)
    registration_number: str | None = Field(default=None, max_length=64)
    vat_number: str | None = Field(default=None, max_length=64)
    country_code: str | None = Field(default=None, max_length=2)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default="active", max_length=32)
    contacts: list["CompanyContactCreateRequest"] = Field(default_factory=list)
    bank_accounts: list["CompanyBankAccountCreateRequest"] = Field(default_factory=list)


class CompanyResponse(BaseModel):
    id: int
    legal_name: str
    short_name: str | None = None


class CompanyOverviewItem(BaseModel):
    id: int
    legal_name: str
    short_name: str | None = None
    bank_names: list[str]
    director_name: str | None = None


class BankAccountOverviewItem(BaseModel):
    id: int
    company_id: int
    company_name: str
    bank_id: int
    bank_label: str
    bank_full_name: str
    iban: str | None = None
    account_number: str | None = None
    swift_or_bic: str | None = None
    bank_address: str | None = None
    currency_code: str
    is_primary: bool
    is_active: bool
    opened_at: date | None = None
    closed_at: date | None = None


class BankAccountLookupItem(BaseModel):
    id: int
    label: str
    company_id: int
    company_name: str
    bank_id: int
    bank_name: str
    currency_code: str


class CompanyContactCreateRequest(BaseModel):
    id: int | None = None
    full_name: str = Field(min_length=1, max_length=255)
    role: str | None = Field(default=None, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    is_primary: bool = False


class CompanyBankAccountCreateRequest(BaseModel):
    id: int | None = None
    bank_id: int
    currency_code: str = Field(min_length=3, max_length=3)
    account_name: str | None = Field(default=None, max_length=255)
    iban: str | None = Field(default=None, max_length=64)
    account_number: str | None = Field(default=None, max_length=64)
    bic: str | None = Field(default=None, max_length=32)
    bank_branch: str | None = Field(default=None, max_length=255)
    is_primary: bool = False
    is_active: bool = True
    opened_at: date | None = None
    closed_at: date | None = None


class BankAccountCreateRequest(BaseModel):
    company_id: int
    bank_id: int | None = None
    bank_name: str | None = Field(default=None, max_length=255)
    bank_short_name: str | None = Field(default=None, max_length=128)
    bank_swift_code: str | None = Field(default=None, max_length=32)
    bank_country_code: str | None = Field(default=None, max_length=2)
    bank_address_line1: str | None = Field(default=None, max_length=255)
    bank_address_line2: str | None = Field(default=None, max_length=255)
    bank_city: str | None = Field(default=None, max_length=128)
    bank_postal_code: str | None = Field(default=None, max_length=32)
    bank_website: str | None = Field(default=None, max_length=255)
    currency_code: str = Field(min_length=3, max_length=3)
    account_name: str | None = Field(default=None, max_length=255)
    iban: str | None = Field(default=None, max_length=64)
    account_number: str | None = Field(default=None, max_length=64)
    bic: str | None = Field(default=None, max_length=32)
    bank_branch: str | None = Field(default=None, max_length=255)
    is_primary: bool = False
    is_active: bool = True
    opened_at: date | None = None
    closed_at: date | None = None


class BankAccountCreateResponse(BaseModel):
    id: int
    company_id: int
    bank_id: int
    currency_code: str


class CompanyContactResponse(BaseModel):
    id: int
    full_name: str
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    is_primary: bool


class CompanyBankAccountResponse(BaseModel):
    id: int
    bank_id: int
    bank_label: str
    currency_code: str
    account_name: str | None = None
    iban: str | None = None
    account_number: str | None = None
    bic: str | None = None
    bank_branch: str | None = None
    is_primary: bool
    is_active: bool
    opened_at: date | None = None
    closed_at: date | None = None


class CompanyDetailResponse(BaseModel):
    id: int
    legal_name: str
    short_name: str | None = None
    registration_number: str | None = None
    vat_number: str | None = None
    country_code: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    postal_code: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    contacts: list[CompanyContactResponse]
    bank_accounts: list[CompanyBankAccountResponse]


class BankCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    short_name: str | None = Field(default=None, max_length=128)
    swift_code: str | None = Field(default=None, max_length=32)


class BankResponse(BaseModel):
    id: int
    name: str
    short_name: str | None = None
    swift_code: str | None = None


class ClientCreateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    first_name: str | None = Field(default=None, max_length=128)
    last_name: str | None = Field(default=None, max_length=128)
    middle_name: str | None = Field(default=None, max_length=128)
    date_of_birth: date | None = None
    personal_id_number: str | None = Field(default=None, max_length=64)
    country_code: str | None = Field(default=None, max_length=2)
    tax_residency_country_code: str | None = Field(default=None, max_length=2)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=32)
    notes: str | None = None
    status: str | None = Field(default="active", max_length=32)


class ClientResponse(BaseModel):
    id: int
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None


class ClientOverviewItem(BaseModel):
    id: int
    full_name: str
    personal_id_number: str | None = None
    date_of_birth: date | None = None
    country_code: str | None = None
    tax_residency_country_code: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    status: str | None = None


class ClientDetailResponse(BaseModel):
    id: int
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    date_of_birth: date | None = None
    personal_id_number: str | None = None
    country_code: str | None = None
    tax_residency_country_code: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    postal_code: str | None = None
    notes: str | None = None
    status: str | None = None


class CounterpartyCreateRequest(BaseModel):
    client_id: int
    legal_name: str = Field(min_length=1, max_length=255)
    short_name: str | None = Field(default=None, max_length=128)
    registration_number: str | None = Field(default=None, max_length=64)
    vat_number: str | None = Field(default=None, max_length=64)
    country_code: str | None = Field(default=None, max_length=2)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    website: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    status: str | None = Field(default="active", max_length=32)


class CounterpartyResponse(BaseModel):
    id: int
    client_id: int
    legal_name: str
    short_name: str | None = None


class CounterpartyOverviewItem(BaseModel):
    id: int
    client_id: int
    client_name: str
    legal_name: str
    short_name: str | None = None
    registration_number: str | None = None
    country_code: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    website: str | None = None
    status: str | None = None


class CounterpartyDetailResponse(BaseModel):
    id: int
    client_id: int
    client_name: str
    legal_name: str
    short_name: str | None = None
    registration_number: str | None = None
    vat_number: str | None = None
    country_code: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    postal_code: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    notes: str | None = None
    status: str | None = None


class CurrencyCreateRequest(BaseModel):
    code: str = Field(min_length=3, max_length=3)
    name: str = Field(min_length=1, max_length=64)
    numeric_code: str | None = Field(default=None, max_length=3)
    minor_units: int | None = Field(default=2, ge=0, le=6)


class CurrencyResponse(BaseModel):
    code: str
    name: str
    numeric_code: str | None = None
    minor_units: int | None = None


CompanyCreateRequest.model_rebuild()
