from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reference import Bank, Client, Company, CompanyBankAccount, CompanyContact, Counterparty, Currency
from app.schemas.reference import (
    BankAccountCreateRequest,
    BankAccountLookupItem,
    BankAccountOverviewItem,
    BankCreateRequest,
    ClientCreateRequest,
    ClientDetailResponse,
    ClientOverviewItem,
    CounterpartyCreateRequest,
    CounterpartyDetailResponse,
    CounterpartyOverviewItem,
    CompanyBankAccountCreateRequest,
    CompanyBankAccountResponse,
    CompanyContactCreateRequest,
    CompanyContactResponse,
    CompanyCreateRequest,
    CompanyDetailResponse,
    CompanyOverviewItem,
    CurrencyCreateRequest,
)


async def search_companies(db: AsyncSession, query: str | None, limit: int) -> list[Company]:
    stmt = select(Company).order_by(Company.legal_name.asc()).limit(limit)
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(or_(Company.legal_name.ilike(pattern), Company.short_name.ilike(pattern)))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_company(db: AsyncSession, payload: CompanyCreateRequest) -> Company:
    company = Company(
        legal_name=payload.legal_name.strip(),
        short_name=payload.short_name.strip() if payload.short_name else None,
        registration_number=payload.registration_number.strip() if payload.registration_number else None,
        vat_number=payload.vat_number.strip() if payload.vat_number else None,
        country_code=payload.country_code.strip().upper() if payload.country_code else None,
        address_line1=payload.address_line1.strip() if payload.address_line1 else None,
        address_line2=payload.address_line2.strip() if payload.address_line2 else None,
        city=payload.city.strip() if payload.city else None,
        postal_code=payload.postal_code.strip() if payload.postal_code else None,
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        status=payload.status.strip() if payload.status else "active",
    )
    db.add(company)
    await db.flush()

    for contact_payload in payload.contacts:
        await add_company_contact(db, company.id, contact_payload)

    for account_payload in payload.bank_accounts:
        await add_company_bank_account(db, company.id, account_payload)

    return company


async def add_company_contact(
    db: AsyncSession,
    company_id: int,
    payload: CompanyContactCreateRequest,
) -> CompanyContact:
    contact = CompanyContact(
        company_id=company_id,
        full_name=payload.full_name.strip(),
        role=payload.role.strip() if payload.role else None,
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        is_primary=payload.is_primary,
    )
    db.add(contact)
    await db.flush()
    return contact


async def add_company_bank_account(
    db: AsyncSession,
    company_id: int,
    payload: CompanyBankAccountCreateRequest,
) -> CompanyBankAccount:
    bank = await db.get(Bank, payload.bank_id)
    if bank is None:
        raise ValueError("Bank not found")

    currency = await db.get(Currency, payload.currency_code.strip().upper())
    if currency is None:
        raise ValueError("Currency not found")

    account = CompanyBankAccount(
        company_id=company_id,
        bank_id=bank.id,
        currency_code=currency.code,
        account_name=payload.account_name.strip() if payload.account_name else None,
        iban=payload.iban.strip() if payload.iban else None,
        account_number=payload.account_number.strip() if payload.account_number else None,
        bic=payload.bic.strip() if payload.bic else None,
        bank_branch=payload.bank_branch.strip() if payload.bank_branch else None,
        is_primary=payload.is_primary,
        is_active=payload.is_active,
        opened_at=payload.opened_at,
        closed_at=payload.closed_at,
    )
    db.add(account)
    await db.flush()
    return account


async def list_company_overview(
    db: AsyncSession,
    *,
    query: str | None,
    limit: int,
) -> list[CompanyOverviewItem]:
    stmt = (
        select(Company)
        .options(
            selectinload(Company.bank_accounts).selectinload(CompanyBankAccount.bank),
            selectinload(Company.contacts),
        )
        .order_by(Company.legal_name.asc())
        .limit(limit)
    )

    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(or_(Company.legal_name.ilike(pattern), Company.short_name.ilike(pattern)))

    result = await db.execute(stmt)
    companies = list(result.scalars().unique().all())

    overview_items: list[CompanyOverviewItem] = []
    for company in companies:
        active_accounts = [
            account
            for account in company.bank_accounts
            if account.is_active and account.bank is not None
        ]
        bank_names = sorted({account.bank.short_name or account.bank.name for account in active_accounts})

        ordered_contacts = sorted(
            company.contacts,
            key=lambda contact: (
                not bool(contact.is_primary),
                str(contact.role or "").lower() != "director",
                str(contact.role or "").lower(),
                contact.created_at,
                contact.id,
            ),
        )
        director = next(
            (
                contact
                for contact in ordered_contacts
                if (contact.role or "").strip().lower() in {"director", "ceo", "general director"}
            ),
            ordered_contacts[0] if ordered_contacts else None,
        )

        overview_items.append(
            CompanyOverviewItem(
                id=company.id,
                legal_name=company.legal_name,
                short_name=company.short_name,
                bank_names=bank_names,
                director_name=director.full_name if director is not None else None,
            )
        )

    return overview_items


async def get_company_detail(db: AsyncSession, company_id: int) -> CompanyDetailResponse | None:
    stmt = (
        select(Company)
        .options(
            selectinload(Company.contacts),
            selectinload(Company.bank_accounts).selectinload(CompanyBankAccount.bank),
        )
        .where(Company.id == company_id)
    )
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()
    if company is None:
        return None

    return CompanyDetailResponse(
        id=company.id,
        legal_name=company.legal_name,
        short_name=company.short_name,
        registration_number=company.registration_number,
        vat_number=company.vat_number,
        country_code=company.country_code,
        address_line1=company.address_line1,
        address_line2=company.address_line2,
        city=company.city,
        postal_code=company.postal_code,
        email=company.email,
        phone=company.phone,
        status=company.status,
        contacts=[
            CompanyContactResponse(
                id=contact.id,
                full_name=contact.full_name,
                role=contact.role,
                email=contact.email,
                phone=contact.phone,
                is_primary=contact.is_primary,
            )
            for contact in sorted(company.contacts, key=lambda item: (item.id,))
        ],
        bank_accounts=[
            CompanyBankAccountResponse(
                id=account.id,
                bank_id=account.bank_id,
                bank_label=(account.bank.short_name or account.bank.name)
                if account.bank is not None
                else str(account.bank_id),
                currency_code=account.currency_code,
                account_name=account.account_name,
                iban=account.iban,
                account_number=account.account_number,
                bic=account.bic,
                bank_branch=account.bank_branch,
                is_primary=account.is_primary,
                is_active=account.is_active,
                opened_at=account.opened_at,
                closed_at=account.closed_at,
            )
            for account in sorted(company.bank_accounts, key=lambda item: (item.id,))
        ],
    )


async def update_company(db: AsyncSession, company_id: int, payload: CompanyCreateRequest) -> Company:
    stmt = (
        select(Company)
        .options(
            selectinload(Company.contacts),
            selectinload(Company.bank_accounts).selectinload(CompanyBankAccount.bank),
        )
        .where(Company.id == company_id)
    )
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()
    if company is None:
        raise ValueError("Company not found")

    company.legal_name = payload.legal_name.strip()
    company.short_name = payload.short_name.strip() if payload.short_name else None
    company.registration_number = payload.registration_number.strip() if payload.registration_number else None
    company.vat_number = payload.vat_number.strip() if payload.vat_number else None
    company.country_code = payload.country_code.strip().upper() if payload.country_code else None
    company.address_line1 = payload.address_line1.strip() if payload.address_line1 else None
    company.address_line2 = payload.address_line2.strip() if payload.address_line2 else None
    company.city = payload.city.strip() if payload.city else None
    company.postal_code = payload.postal_code.strip() if payload.postal_code else None
    company.email = payload.email.strip() if payload.email else None
    company.phone = payload.phone.strip() if payload.phone else None
    company.status = payload.status.strip() if payload.status else "active"

    existing_contacts = {contact.id: contact for contact in company.contacts}
    seen_contact_ids: set[int] = set()
    for contact_payload in payload.contacts:
        if contact_payload.id is not None and contact_payload.id in existing_contacts:
            contact = existing_contacts[contact_payload.id]
            contact.full_name = contact_payload.full_name.strip()
            contact.role = contact_payload.role.strip() if contact_payload.role else None
            contact.email = contact_payload.email.strip() if contact_payload.email else None
            contact.phone = contact_payload.phone.strip() if contact_payload.phone else None
            contact.is_primary = contact_payload.is_primary
            seen_contact_ids.add(contact.id)
        else:
            contact = await add_company_contact(db, company.id, contact_payload)
            seen_contact_ids.add(contact.id)

    for contact in company.contacts:
        if contact.id not in seen_contact_ids:
            await db.delete(contact)

    existing_accounts = {account.id: account for account in company.bank_accounts}
    seen_account_ids: set[int] = set()
    for account_payload in payload.bank_accounts:
        currency = await db.get(Currency, account_payload.currency_code.strip().upper())
        if currency is None:
            raise ValueError("Currency not found")

        bank = await db.get(Bank, account_payload.bank_id)
        if bank is None:
            raise ValueError("Bank not found")

        if account_payload.id is not None and account_payload.id in existing_accounts:
            account = existing_accounts[account_payload.id]
            account.bank_id = bank.id
            account.currency_code = currency.code
            account.account_name = account_payload.account_name.strip() if account_payload.account_name else None
            account.iban = account_payload.iban.strip() if account_payload.iban else None
            account.account_number = account_payload.account_number.strip() if account_payload.account_number else None
            account.bic = account_payload.bic.strip() if account_payload.bic else None
            account.bank_branch = account_payload.bank_branch.strip() if account_payload.bank_branch else None
            account.is_primary = account_payload.is_primary
            account.is_active = account_payload.is_active
            account.opened_at = account_payload.opened_at
            account.closed_at = account_payload.closed_at
            seen_account_ids.add(account.id)
        else:
            account = await add_company_bank_account(db, company.id, account_payload)
            seen_account_ids.add(account.id)

    for account in company.bank_accounts:
        if account.id not in seen_account_ids:
            account.is_active = False

    await db.flush()
    return company


async def delete_company(db: AsyncSession, company_id: int) -> None:
    company = await db.get(Company, company_id)
    if company is None:
        raise ValueError("Company not found")
    await db.delete(company)
    await db.flush()


async def list_bank_account_overview(
    db: AsyncSession,
    *,
    query: str | None,
    limit: int,
) -> list[BankAccountOverviewItem]:
    stmt = (
        select(CompanyBankAccount)
        .options(
            selectinload(CompanyBankAccount.company),
            selectinload(CompanyBankAccount.bank),
        )
        .order_by(CompanyBankAccount.id.asc())
        .limit(limit)
    )

    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.join(CompanyBankAccount.company).join(CompanyBankAccount.bank).where(
            or_(
                Company.legal_name.ilike(pattern),
                Company.short_name.ilike(pattern),
                Bank.name.ilike(pattern),
                Bank.short_name.ilike(pattern),
                CompanyBankAccount.iban.ilike(pattern),
                CompanyBankAccount.account_number.ilike(pattern),
                CompanyBankAccount.bic.ilike(pattern),
            )
        )

    result = await db.execute(stmt)
    accounts = list(result.scalars().unique().all())

    items: list[BankAccountOverviewItem] = []
    for account in accounts:
        company = account.company
        bank = account.bank
        if company is None or bank is None:
            continue

        address_parts = [
            bank.address_line1,
            bank.address_line2,
            " ".join(part for part in [bank.postal_code, bank.city] if part),
            bank.country_code,
        ]
        bank_address = ", ".join(part for part in address_parts if part)

        items.append(
            BankAccountOverviewItem(
                id=account.id,
                company_id=company.id,
                company_name=company.short_name or company.legal_name,
                bank_id=bank.id,
                bank_label=bank.short_name or bank.name,
                bank_full_name=bank.name,
                iban=account.iban,
                account_number=account.account_number,
                swift_or_bic=account.bic or bank.swift_code,
                bank_address=bank_address or None,
                currency_code=account.currency_code,
                is_primary=account.is_primary,
                is_active=account.is_active,
                opened_at=account.opened_at,
                closed_at=account.closed_at,
            )
        )

    return items


async def search_company_bank_accounts(
    db: AsyncSession,
    *,
    query: str | None,
    limit: int,
) -> list[BankAccountLookupItem]:
    stmt = (
        select(CompanyBankAccount)
        .options(
            selectinload(CompanyBankAccount.company),
            selectinload(CompanyBankAccount.bank),
        )
        .where(CompanyBankAccount.is_active.is_(True))
        .order_by(Company.legal_name.asc(), Bank.name.asc(), CompanyBankAccount.id.asc())
        .join(CompanyBankAccount.company)
        .join(CompanyBankAccount.bank)
        .limit(limit)
    )

    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Company.legal_name.ilike(pattern),
                Company.short_name.ilike(pattern),
                Bank.name.ilike(pattern),
                Bank.short_name.ilike(pattern),
                CompanyBankAccount.currency_code.ilike(pattern),
                CompanyBankAccount.iban.ilike(pattern),
                CompanyBankAccount.account_number.ilike(pattern),
            )
        )

    result = await db.execute(stmt)
    accounts = list(result.scalars().unique().all())

    items: list[BankAccountLookupItem] = []
    for account in accounts:
        company = account.company
        bank = account.bank
        if company is None or bank is None:
            continue

        account_reference = account.iban or account.account_number or f"Account #{account.id}"
        items.append(
            BankAccountLookupItem(
                id=account.id,
                label=(
                    f"{company.short_name or company.legal_name} | "
                    f"{bank.short_name or bank.name} | "
                    f"{account.currency_code} | {account_reference}"
                ),
                company_id=company.id,
                company_name=company.short_name or company.legal_name,
                bank_id=bank.id,
                bank_name=bank.short_name or bank.name,
                currency_code=account.currency_code,
            )
        )

    return items


async def search_banks(db: AsyncSession, query: str | None, limit: int) -> list[Bank]:
    stmt = select(Bank).order_by(Bank.name.asc()).limit(limit)
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(or_(Bank.name.ilike(pattern), Bank.short_name.ilike(pattern)))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_bank(db: AsyncSession, payload: BankCreateRequest) -> Bank:
    bank = Bank(
        name=payload.name.strip(),
        short_name=payload.short_name.strip() if payload.short_name else None,
        swift_code=payload.swift_code.strip() if payload.swift_code else None,
    )
    db.add(bank)
    await db.flush()
    return bank


async def create_bank_account(db: AsyncSession, payload: BankAccountCreateRequest) -> CompanyBankAccount:
    company = await db.get(Company, payload.company_id)
    if company is None:
        raise ValueError("Company not found")

    currency = await db.get(Currency, payload.currency_code.strip().upper())
    if currency is None:
        raise ValueError("Currency not found")

    bank: Bank | None = None
    if payload.bank_id is not None:
        bank = await db.get(Bank, payload.bank_id)
        if bank is None:
            raise ValueError("Bank not found")
    else:
        normalized_name = (payload.bank_name or "").strip()
        normalized_short = (payload.bank_short_name or "").strip()
        if not normalized_name and not normalized_short:
            raise ValueError("Bank name or short name is required")

        search_name = normalized_name or normalized_short
        result = await db.execute(
            select(Bank).where(
                or_(
                    func.lower(Bank.name) == search_name.lower(),
                    func.lower(Bank.short_name) == search_name.lower(),
                )
            )
        )
        bank = result.scalar_one_or_none()
        if bank is None:
            bank = Bank(
                name=normalized_name or normalized_short,
                short_name=normalized_short or None,
                swift_code=payload.bank_swift_code.strip() if payload.bank_swift_code else None,
                country_code=payload.bank_country_code.strip().upper() if payload.bank_country_code else None,
                address_line1=payload.bank_address_line1.strip() if payload.bank_address_line1 else None,
                address_line2=payload.bank_address_line2.strip() if payload.bank_address_line2 else None,
                city=payload.bank_city.strip() if payload.bank_city else None,
                postal_code=payload.bank_postal_code.strip() if payload.bank_postal_code else None,
                website=payload.bank_website.strip() if payload.bank_website else None,
            )
            db.add(bank)
            await db.flush()

    account = CompanyBankAccount(
        company_id=company.id,
        bank_id=bank.id,
        currency_code=currency.code,
        account_name=payload.account_name.strip() if payload.account_name else None,
        iban=payload.iban.strip() if payload.iban else None,
        account_number=payload.account_number.strip() if payload.account_number else None,
        bic=payload.bic.strip() if payload.bic else None,
        bank_branch=payload.bank_branch.strip() if payload.bank_branch else None,
        is_primary=payload.is_primary,
        is_active=payload.is_active,
        opened_at=payload.opened_at,
        closed_at=payload.closed_at,
    )
    db.add(account)
    await db.flush()
    return account


async def search_clients(db: AsyncSession, query: str | None, limit: int) -> list[Client]:
    stmt = select(Client).order_by(Client.full_name.asc()).limit(limit)
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Client.full_name.ilike(pattern),
                Client.first_name.ilike(pattern),
                Client.last_name.ilike(pattern),
                Client.middle_name.ilike(pattern),
                Client.personal_id_number.ilike(pattern),
                Client.email.ilike(pattern),
                Client.phone.ilike(pattern),
            )
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_client(db: AsyncSession, payload: ClientCreateRequest) -> Client:
    client = Client(
        full_name=payload.full_name.strip(),
        first_name=payload.first_name.strip() if payload.first_name else None,
        last_name=payload.last_name.strip() if payload.last_name else None,
        middle_name=payload.middle_name.strip() if payload.middle_name else None,
        date_of_birth=payload.date_of_birth,
        personal_id_number=payload.personal_id_number.strip() if payload.personal_id_number else None,
        country_code=payload.country_code.strip().upper() if payload.country_code else None,
        tax_residency_country_code=payload.tax_residency_country_code.strip().upper()
        if payload.tax_residency_country_code
        else None,
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        address_line1=payload.address_line1.strip() if payload.address_line1 else None,
        address_line2=payload.address_line2.strip() if payload.address_line2 else None,
        city=payload.city.strip() if payload.city else None,
        postal_code=payload.postal_code.strip() if payload.postal_code else None,
        notes=payload.notes.strip() if payload.notes else None,
        status=payload.status.strip() if payload.status else "active",
    )
    db.add(client)
    await db.flush()
    return client


async def list_client_overview(
    db: AsyncSession,
    *,
    query: str | None,
    limit: int,
) -> list[ClientOverviewItem]:
    stmt = select(Client).order_by(Client.full_name.asc()).limit(limit)

    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Client.full_name.ilike(pattern),
                Client.first_name.ilike(pattern),
                Client.last_name.ilike(pattern),
                Client.middle_name.ilike(pattern),
                Client.personal_id_number.ilike(pattern),
                Client.email.ilike(pattern),
                Client.phone.ilike(pattern),
                Client.city.ilike(pattern),
            )
        )

    result = await db.execute(stmt)
    clients = list(result.scalars().all())

    return [
        ClientOverviewItem(
            id=client.id,
            full_name=client.full_name,
            personal_id_number=client.personal_id_number,
            date_of_birth=client.date_of_birth,
            country_code=client.country_code,
            tax_residency_country_code=client.tax_residency_country_code,
            email=client.email,
            phone=client.phone,
            city=client.city,
            status=client.status,
        )
        for client in clients
    ]


async def get_client_detail(db: AsyncSession, client_id: int) -> ClientDetailResponse | None:
    client = await db.get(Client, client_id)
    if client is None:
        return None

    return ClientDetailResponse(
        id=client.id,
        full_name=client.full_name,
        first_name=client.first_name,
        last_name=client.last_name,
        middle_name=client.middle_name,
        date_of_birth=client.date_of_birth,
        personal_id_number=client.personal_id_number,
        country_code=client.country_code,
        tax_residency_country_code=client.tax_residency_country_code,
        email=client.email,
        phone=client.phone,
        address_line1=client.address_line1,
        address_line2=client.address_line2,
        city=client.city,
        postal_code=client.postal_code,
        notes=client.notes,
        status=client.status,
    )


async def update_client(db: AsyncSession, client_id: int, payload: ClientCreateRequest) -> Client:
    client = await db.get(Client, client_id)
    if client is None:
        raise ValueError("Client not found")

    client.full_name = payload.full_name.strip()
    client.first_name = payload.first_name.strip() if payload.first_name else None
    client.last_name = payload.last_name.strip() if payload.last_name else None
    client.middle_name = payload.middle_name.strip() if payload.middle_name else None
    client.date_of_birth = payload.date_of_birth
    client.personal_id_number = payload.personal_id_number.strip() if payload.personal_id_number else None
    client.country_code = payload.country_code.strip().upper() if payload.country_code else None
    client.tax_residency_country_code = (
        payload.tax_residency_country_code.strip().upper() if payload.tax_residency_country_code else None
    )
    client.email = payload.email.strip() if payload.email else None
    client.phone = payload.phone.strip() if payload.phone else None
    client.address_line1 = payload.address_line1.strip() if payload.address_line1 else None
    client.address_line2 = payload.address_line2.strip() if payload.address_line2 else None
    client.city = payload.city.strip() if payload.city else None
    client.postal_code = payload.postal_code.strip() if payload.postal_code else None
    client.notes = payload.notes.strip() if payload.notes else None
    client.status = payload.status.strip() if payload.status else "active"

    await db.flush()
    return client


async def delete_client(db: AsyncSession, client_id: int) -> None:
    client = await db.get(Client, client_id)
    if client is None:
        raise ValueError("Client not found")
    await db.delete(client)
    await db.flush()


async def search_counterparties(db: AsyncSession, query: str | None, limit: int) -> list[Counterparty]:
    stmt = (
        select(Counterparty)
        .options(selectinload(Counterparty.client))
        .join(Counterparty.client)
        .order_by(Counterparty.legal_name.asc())
        .limit(limit)
    )
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Counterparty.legal_name.ilike(pattern),
                Counterparty.short_name.ilike(pattern),
                Counterparty.registration_number.ilike(pattern),
                Counterparty.email.ilike(pattern),
                Counterparty.phone.ilike(pattern),
                Counterparty.city.ilike(pattern),
                Client.full_name.ilike(pattern),
            )
        )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def create_counterparty(db: AsyncSession, payload: CounterpartyCreateRequest) -> Counterparty:
    client = await db.get(Client, payload.client_id)
    if client is None:
        raise ValueError("Client not found")

    counterparty = Counterparty(
        client_id=client.id,
        legal_name=payload.legal_name.strip(),
        short_name=payload.short_name.strip() if payload.short_name else None,
        registration_number=payload.registration_number.strip() if payload.registration_number else None,
        vat_number=payload.vat_number.strip() if payload.vat_number else None,
        country_code=payload.country_code.strip().upper() if payload.country_code else None,
        address_line1=payload.address_line1.strip() if payload.address_line1 else None,
        address_line2=payload.address_line2.strip() if payload.address_line2 else None,
        city=payload.city.strip() if payload.city else None,
        postal_code=payload.postal_code.strip() if payload.postal_code else None,
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        website=payload.website.strip() if payload.website else None,
        notes=payload.notes.strip() if payload.notes else None,
        status=payload.status.strip() if payload.status else "active",
    )
    db.add(counterparty)
    await db.flush()
    return counterparty


async def list_counterparty_overview(
    db: AsyncSession,
    *,
    query: str | None,
    limit: int,
) -> list[CounterpartyOverviewItem]:
    stmt = (
        select(Counterparty)
        .options(selectinload(Counterparty.client))
        .join(Counterparty.client)
        .order_by(Counterparty.legal_name.asc())
        .limit(limit)
    )

    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Counterparty.legal_name.ilike(pattern),
                Counterparty.short_name.ilike(pattern),
                Counterparty.registration_number.ilike(pattern),
                Counterparty.email.ilike(pattern),
                Counterparty.phone.ilike(pattern),
                Counterparty.city.ilike(pattern),
                Counterparty.website.ilike(pattern),
                Client.full_name.ilike(pattern),
            )
        )

    result = await db.execute(stmt)
    counterparties = list(result.scalars().unique().all())

    return [
        CounterpartyOverviewItem(
            id=counterparty.id,
            client_id=counterparty.client_id,
            client_name=counterparty.client.full_name if counterparty.client is not None else str(counterparty.client_id),
            legal_name=counterparty.legal_name,
            short_name=counterparty.short_name,
            registration_number=counterparty.registration_number,
            country_code=counterparty.country_code,
            email=counterparty.email,
            phone=counterparty.phone,
            city=counterparty.city,
            website=counterparty.website,
            status=counterparty.status,
        )
        for counterparty in counterparties
    ]


async def get_counterparty_detail(db: AsyncSession, counterparty_id: int) -> CounterpartyDetailResponse | None:
    stmt = (
        select(Counterparty)
        .options(selectinload(Counterparty.client))
        .where(Counterparty.id == counterparty_id)
    )
    result = await db.execute(stmt)
    counterparty = result.scalar_one_or_none()
    if counterparty is None:
        return None

    return CounterpartyDetailResponse(
        id=counterparty.id,
        client_id=counterparty.client_id,
        client_name=counterparty.client.full_name if counterparty.client is not None else str(counterparty.client_id),
        legal_name=counterparty.legal_name,
        short_name=counterparty.short_name,
        registration_number=counterparty.registration_number,
        vat_number=counterparty.vat_number,
        country_code=counterparty.country_code,
        address_line1=counterparty.address_line1,
        address_line2=counterparty.address_line2,
        city=counterparty.city,
        postal_code=counterparty.postal_code,
        email=counterparty.email,
        phone=counterparty.phone,
        website=counterparty.website,
        notes=counterparty.notes,
        status=counterparty.status,
    )


async def update_counterparty(
    db: AsyncSession,
    counterparty_id: int,
    payload: CounterpartyCreateRequest,
) -> Counterparty:
    counterparty = await db.get(Counterparty, counterparty_id)
    if counterparty is None:
        raise ValueError("Counterparty not found")

    client = await db.get(Client, payload.client_id)
    if client is None:
        raise ValueError("Client not found")

    counterparty.client_id = client.id
    counterparty.legal_name = payload.legal_name.strip()
    counterparty.short_name = payload.short_name.strip() if payload.short_name else None
    counterparty.registration_number = payload.registration_number.strip() if payload.registration_number else None
    counterparty.vat_number = payload.vat_number.strip() if payload.vat_number else None
    counterparty.country_code = payload.country_code.strip().upper() if payload.country_code else None
    counterparty.address_line1 = payload.address_line1.strip() if payload.address_line1 else None
    counterparty.address_line2 = payload.address_line2.strip() if payload.address_line2 else None
    counterparty.city = payload.city.strip() if payload.city else None
    counterparty.postal_code = payload.postal_code.strip() if payload.postal_code else None
    counterparty.email = payload.email.strip() if payload.email else None
    counterparty.phone = payload.phone.strip() if payload.phone else None
    counterparty.website = payload.website.strip() if payload.website else None
    counterparty.notes = payload.notes.strip() if payload.notes else None
    counterparty.status = payload.status.strip() if payload.status else "active"

    await db.flush()
    return counterparty


async def delete_counterparty(db: AsyncSession, counterparty_id: int) -> None:
    counterparty = await db.get(Counterparty, counterparty_id)
    if counterparty is None:
        raise ValueError("Counterparty not found")
    await db.delete(counterparty)
    await db.flush()


async def search_currencies(db: AsyncSession, query: str | None, limit: int) -> list[Currency]:
    stmt = select(Currency).order_by(Currency.code.asc()).limit(limit)
    if query:
        pattern = f"%{query.strip().upper()}%"
        stmt = stmt.where(or_(func.upper(Currency.code).ilike(pattern), Currency.name.ilike(f"%{query.strip()}%")))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_currency(db: AsyncSession, payload: CurrencyCreateRequest) -> Currency:
    code = payload.code.strip().upper()
    existing = await db.get(Currency, code)
    if existing is not None:
        return existing

    currency = Currency(
        code=code,
        name=payload.name.strip(),
        numeric_code=payload.numeric_code.strip() if payload.numeric_code else None,
        minor_units=payload.minor_units,
        is_active=True,
    )
    db.add(currency)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = await db.get(Currency, code)
        if existing is None:
            raise
        return existing
    return currency
