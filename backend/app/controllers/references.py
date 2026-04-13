from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.reference import (
    BankAccountCreateRequest,
    BankAccountCreateResponse,
    BankAccountLookupItem,
    BankAccountOverviewItem,
    BankCreateRequest,
    ClientDetailResponse,
    BankResponse,
    ClientCreateRequest,
    ClientOverviewItem,
    ClientResponse,
    CounterpartyCreateRequest,
    CounterpartyDetailResponse,
    CounterpartyOverviewItem,
    CounterpartyResponse,
    CompanyCreateRequest,
    CompanyDetailResponse,
    CompanyOverviewItem,
    CompanyResponse,
    CurrencyCreateRequest,
    CurrencyLookupItem,
    CurrencyResponse,
    LookupItem,
)
from app.services.reference import (
    create_bank,
    create_bank_account,
    create_client,
    create_company,
    create_counterparty,
    create_currency,
    delete_client,
    delete_company,
    delete_counterparty,
    get_client_detail,
    get_company_detail,
    get_counterparty_detail,
    list_bank_account_overview,
    list_client_overview,
    list_company_overview,
    list_counterparty_overview,
    search_company_bank_accounts,
    search_banks,
    search_clients,
    search_companies,
    search_counterparties,
    search_currencies,
    update_client,
    update_company,
    update_counterparty,
)


router = APIRouter(tags=["references"])


@router.get("/companies", response_model=list[LookupItem])
async def get_companies(
    query: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[LookupItem]:
    companies = await search_companies(db, query=query, limit=limit)
    return [LookupItem(id=item.id, label=item.short_name or item.legal_name) for item in companies]


@router.post("/companies", response_model=CompanyResponse, status_code=201)
async def post_company(payload: CompanyCreateRequest, db: AsyncSession = Depends(get_db)) -> CompanyResponse:
    try:
        company = await create_company(db, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create company") from exc
    return CompanyResponse(id=company.id, legal_name=company.legal_name, short_name=company.short_name)


@router.get("/companies/overview", response_model=list[CompanyOverviewItem])
async def get_companies_overview(
    query: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[CompanyOverviewItem]:
    return await list_company_overview(db, query=query, limit=limit)


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)) -> CompanyDetailResponse:
    company = await get_company_detail(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def put_company(
    company_id: int,
    payload: CompanyCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    try:
        company = await update_company(db, company_id, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update company") from exc

    return CompanyResponse(id=company.id, legal_name=company.legal_name, short_name=company.short_name)


@router.delete("/companies/{company_id}", status_code=204)
async def delete_company_endpoint(company_id: int, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await delete_company(db, company_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Company cannot be deleted because it has related records") from exc


@router.get("/banks", response_model=list[LookupItem])
async def get_banks(
    query: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[LookupItem]:
    banks = await search_banks(db, query=query, limit=limit)
    return [LookupItem(id=item.id, label=item.short_name or item.name) for item in banks]


@router.post("/banks", response_model=BankResponse, status_code=201)
async def post_bank(payload: BankCreateRequest, db: AsyncSession = Depends(get_db)) -> BankResponse:
    try:
        bank = await create_bank(db, payload)
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create bank") from exc
    return BankResponse(id=bank.id, name=bank.name, short_name=bank.short_name, swift_code=bank.swift_code)


@router.get("/bank-accounts/overview", response_model=list[BankAccountOverviewItem])
async def get_bank_accounts_overview(
    query: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[BankAccountOverviewItem]:
    return await list_bank_account_overview(db, query=query, limit=limit)


@router.get("/company-bank-accounts", response_model=list[BankAccountLookupItem])
async def get_company_bank_accounts(
    query: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[BankAccountLookupItem]:
    return await search_company_bank_accounts(db, query=query, limit=limit)


@router.post("/bank-accounts", response_model=BankAccountCreateResponse, status_code=201)
async def post_bank_account(
    payload: BankAccountCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> BankAccountCreateResponse:
    try:
        account = await create_bank_account(db, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create bank account") from exc

    return BankAccountCreateResponse(
        id=account.id,
        company_id=account.company_id,
        bank_id=account.bank_id,
        currency_code=account.currency_code,
    )


@router.get("/clients", response_model=list[LookupItem])
async def get_clients(
    query: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[LookupItem]:
    clients = await search_clients(db, query=query, limit=limit)
    return [LookupItem(id=item.id, label=item.full_name) for item in clients]


@router.post("/clients", response_model=ClientResponse, status_code=201)
async def post_client(payload: ClientCreateRequest, db: AsyncSession = Depends(get_db)) -> ClientResponse:
    try:
        client = await create_client(db, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create client") from exc
    return ClientResponse(
        id=client.id,
        full_name=client.full_name,
        first_name=client.first_name,
        last_name=client.last_name,
        middle_name=client.middle_name,
    )


@router.get("/clients/overview", response_model=list[ClientOverviewItem])
async def get_clients_overview(
    query: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[ClientOverviewItem]:
    return await list_client_overview(db, query=query, limit=limit)


@router.get("/clients/{client_id}", response_model=ClientDetailResponse)
async def get_client(client_id: int, db: AsyncSession = Depends(get_db)) -> ClientDetailResponse:
    client = await get_client_detail(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/clients/{client_id}", response_model=ClientResponse)
async def put_client(
    client_id: int,
    payload: ClientCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    try:
        client = await update_client(db, client_id, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update client") from exc

    return ClientResponse(
        id=client.id,
        full_name=client.full_name,
        first_name=client.first_name,
        last_name=client.last_name,
        middle_name=client.middle_name,
    )


@router.delete("/clients/{client_id}", status_code=204)
async def delete_client_endpoint(client_id: int, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await delete_client(db, client_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Client cannot be deleted because it has related records") from exc


@router.get("/counterparties", response_model=list[LookupItem])
async def get_counterparties(
    query: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[LookupItem]:
    counterparties = await search_counterparties(db, query=query, limit=limit)
    return [LookupItem(id=item.id, label=item.short_name or item.legal_name) for item in counterparties]


@router.post("/counterparties", response_model=CounterpartyResponse, status_code=201)
async def post_counterparty(
    payload: CounterpartyCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> CounterpartyResponse:
    try:
        counterparty = await create_counterparty(db, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create counterparty") from exc
    return CounterpartyResponse(
        id=counterparty.id,
        client_id=counterparty.client_id,
        legal_name=counterparty.legal_name,
        short_name=counterparty.short_name,
    )


@router.get("/counterparties/overview", response_model=list[CounterpartyOverviewItem])
async def get_counterparties_overview(
    query: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[CounterpartyOverviewItem]:
    return await list_counterparty_overview(db, query=query, limit=limit)


@router.get("/counterparties/{counterparty_id}", response_model=CounterpartyDetailResponse)
async def get_counterparty(
    counterparty_id: int,
    db: AsyncSession = Depends(get_db),
) -> CounterpartyDetailResponse:
    counterparty = await get_counterparty_detail(db, counterparty_id)
    if counterparty is None:
        raise HTTPException(status_code=404, detail="Counterparty not found")
    return counterparty


@router.put("/counterparties/{counterparty_id}", response_model=CounterpartyResponse)
async def put_counterparty(
    counterparty_id: int,
    payload: CounterpartyCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> CounterpartyResponse:
    try:
        counterparty = await update_counterparty(db, counterparty_id, payload)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update counterparty") from exc

    return CounterpartyResponse(
        id=counterparty.id,
        client_id=counterparty.client_id,
        legal_name=counterparty.legal_name,
        short_name=counterparty.short_name,
    )


@router.delete("/counterparties/{counterparty_id}", status_code=204)
async def delete_counterparty_endpoint(counterparty_id: int, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await delete_counterparty(db, counterparty_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Counterparty cannot be deleted because it has related records") from exc


@router.get("/currencies", response_model=list[CurrencyLookupItem])
async def get_currencies(
    query: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[CurrencyLookupItem]:
    currencies = await search_currencies(db, query=query, limit=limit)
    return [CurrencyLookupItem(code=item.code, label=f"{item.code} - {item.name}") for item in currencies]


@router.post("/currencies", response_model=CurrencyResponse, status_code=201)
async def post_currency(payload: CurrencyCreateRequest, db: AsyncSession = Depends(get_db)) -> CurrencyResponse:
    try:
        currency = await create_currency(db, payload)
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create currency") from exc
    return CurrencyResponse(
        code=currency.code,
        name=currency.name,
        numeric_code=currency.numeric_code,
        minor_units=currency.minor_units,
    )
