import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Plus, Save, Trash2 } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { createCompany, fetchCompany, updateCompany } from '../../lib/api'
import { loadLookup, requireLookupValue } from '../Payments/paymentUtils'
import './CompanyCreatePage.css'

function createContact() {
  return {
    id: crypto.randomUUID(),
    recordId: null,
    fullName: '',
    role: '',
    email: '',
    phone: '',
    isPrimary: false,
  }
}

function createBankAccount() {
  return {
    recordId: null,
    id: crypto.randomUUID(),
    bankText: '',
    currencyText: 'EUR',
    accountName: '',
    iban: '',
    accountNumber: '',
    bic: '',
    bankBranch: '',
    isPrimary: false,
    isActive: true,
    openedAt: '',
    closedAt: '',
  }
}

function createInitialState() {
  return {
    legalName: '',
    shortName: '',
    registrationNumber: '',
    vatNumber: '',
    countryCode: '',
    addressLine1: '',
    addressLine2: '',
    city: '',
    postalCode: '',
    email: '',
    phone: '',
    status: 'active',
    contacts: [createContact()],
    bankAccounts: [createBankAccount()],
  }
}

export default function CompanyCreatePage() {
  const { companyId } = useParams()
  const isEditMode = Boolean(companyId)
  const navigate = useNavigate()
  const [formState, setFormState] = useState(() => createInitialState())
  const [lookupState, setLookupState] = useState({
    banks: [],
    currencies: [],
    isLoading: true,
  })
  const [submitState, setSubmitState] = useState({
    isSubmitting: false,
    error: '',
    success: '',
  })

  useEffect(() => {
    let cancelled = false

    async function loadLookupsAndCompany() {
      try {
        const [banks, currencies] = await Promise.all([
          loadLookup('banks', ''),
          loadLookup('currencies', ''),
        ])

        if (cancelled) {
          return
        }

        setLookupState({
          banks,
          currencies,
          isLoading: false,
        })

        if (isEditMode && companyId) {
          const company = await fetchCompany(companyId)
          if (cancelled) {
            return
          }

          setFormState({
            legalName: company.legal_name || '',
            shortName: company.short_name || '',
            registrationNumber: company.registration_number || '',
            vatNumber: company.vat_number || '',
            countryCode: company.country_code || '',
            addressLine1: company.address_line1 || '',
            addressLine2: company.address_line2 || '',
            city: company.city || '',
            postalCode: company.postal_code || '',
            email: company.email || '',
            phone: company.phone || '',
            status: company.status || 'active',
            contacts:
              company.contacts?.length > 0
                ? company.contacts.map((contact) => ({
                    id: crypto.randomUUID(),
                    recordId: contact.id,
                    fullName: contact.full_name || '',
                    role: contact.role || '',
                    email: contact.email || '',
                    phone: contact.phone || '',
                    isPrimary: contact.is_primary,
                  }))
                : [createContact()],
            bankAccounts:
              company.bank_accounts?.length > 0
                ? company.bank_accounts.map((account) => ({
                    id: crypto.randomUUID(),
                    recordId: account.id,
                    bankText: account.bank_label || '',
                    currencyText: account.currency_code || 'EUR',
                    accountName: account.account_name || '',
                    iban: account.iban || '',
                    accountNumber: account.account_number || '',
                    bic: account.bic || '',
                    bankBranch: account.bank_branch || '',
                    isPrimary: account.is_primary,
                    isActive: account.is_active,
                    openedAt: account.opened_at || '',
                    closedAt: account.closed_at || '',
                  }))
                : [createBankAccount()],
          })
        }
      } catch {
        if (!cancelled) {
          setLookupState({
            banks: [],
            currencies: [],
            isLoading: false,
          })
        }
      }
    }

    loadLookupsAndCompany()

    return () => {
      cancelled = true
    }
  }, [companyId, isEditMode])

  const contactsCount = useMemo(
    () => formState.contacts.filter((contact) => contact.fullName.trim()).length,
    [formState.contacts],
  )

  const accountsCount = useMemo(
    () =>
      formState.bankAccounts.filter(
        (account) => account.bankText.trim() || account.accountName.trim() || account.iban.trim(),
      ).length,
    [formState.bankAccounts],
  )

  function updateField(name, value) {
    setFormState((current) => ({
      ...current,
      [name]: value,
    }))
  }

  function updateContact(contactId, patch) {
    setFormState((current) => ({
      ...current,
      contacts: current.contacts.map((contact) =>
        contact.id === contactId ? { ...contact, ...patch } : contact,
      ),
    }))
  }

  function updateAccount(accountId, patch) {
    setFormState((current) => ({
      ...current,
      bankAccounts: current.bankAccounts.map((account) =>
        account.id === accountId ? { ...account, ...patch } : account,
      ),
    }))
  }

  function addContact() {
    setFormState((current) => ({
      ...current,
      contacts: [...current.contacts, createContact()],
    }))
  }

  function removeContact(contactId) {
    setFormState((current) => ({
      ...current,
      contacts:
        current.contacts.length === 1
          ? [createContact()]
          : current.contacts.filter((contact) => contact.id !== contactId),
    }))
  }

  function addAccount() {
    setFormState((current) => ({
      ...current,
      bankAccounts: [...current.bankAccounts, createBankAccount()],
    }))
  }

  function removeAccount(accountId) {
    setFormState((current) => ({
      ...current,
      bankAccounts:
        current.bankAccounts.length === 1
          ? [createBankAccount()]
          : current.bankAccounts.filter((account) => account.id !== accountId),
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitState({
      isSubmitting: true,
      error: '',
      success: '',
    })

    try {
      if (!formState.legalName.trim()) {
        throw new Error('Поле "Наименование" обязательно')
      }

      const preparedAccounts = []
      for (const account of formState.bankAccounts) {
        const hasAnyValue =
          account.bankText.trim() ||
          account.accountName.trim() ||
          account.iban.trim() ||
          account.accountNumber.trim()

        if (!hasAnyValue) {
          continue
        }

        if (!account.bankText.trim()) {
          throw new Error('Для банковского счёта нужно указать банк')
        }

        const bank = requireLookupValue(
          'banks',
          null,
          account.bankText,
          lookupState.banks,
          `Банк "${account.bankText.trim()}" не найден в справочнике`,
        )
        const currency = requireLookupValue(
          'currencies',
          null,
          account.currencyText || 'EUR',
          lookupState.currencies,
          `Валюта "${(account.currencyText || 'EUR').trim()}" не найдена в справочнике`,
        )

        preparedAccounts.push({
          id: account.recordId ?? null,
          bank_id: bank.value,
          currency_code: currency.rawLabel || currency.value,
          account_name: account.accountName.trim() || null,
          iban: account.iban.trim() || null,
          account_number: account.accountNumber.trim() || null,
          bic: account.bic.trim() || null,
          bank_branch: account.bankBranch.trim() || null,
          is_primary: account.isPrimary,
          is_active: account.isActive,
          opened_at: account.openedAt || null,
          closed_at: account.closedAt || null,
        })
      }

      const preparedContacts = formState.contacts
        .filter((contact) => contact.fullName.trim())
        .map((contact) => ({
          id: contact.recordId ?? null,
          full_name: contact.fullName.trim(),
          role: contact.role.trim() || null,
          email: contact.email.trim() || null,
          phone: contact.phone.trim() || null,
          is_primary: contact.isPrimary,
        }))

      const payload = {
        legal_name: formState.legalName.trim(),
        short_name: formState.shortName.trim() || null,
        registration_number: formState.registrationNumber.trim() || null,
        vat_number: formState.vatNumber.trim() || null,
        country_code: formState.countryCode.trim().toUpperCase() || null,
        address_line1: formState.addressLine1.trim() || null,
        address_line2: formState.addressLine2.trim() || null,
        city: formState.city.trim() || null,
        postal_code: formState.postalCode.trim() || null,
        email: formState.email.trim() || null,
        phone: formState.phone.trim() || null,
        status: formState.status.trim() || 'active',
        contacts: preparedContacts,
        bank_accounts: preparedAccounts,
      }

      if (isEditMode && companyId) {
        await updateCompany(companyId, payload)
      } else {
        await createCompany(payload)
      }
      setSubmitState({
        isSubmitting: false,
        error: '',
        success: isEditMode ? 'Компания обновлена' : 'Компания сохранена',
      })
      window.setTimeout(() => navigate('/companies'), 500)
    } catch (error) {
      setSubmitState({
        isSubmitting: false,
        error: error.response?.data?.detail || error.message || 'Не удалось сохранить компанию',
        success: '',
      })
    }
  }

  return (
    <div className="company-create-page">
      <div className="company-create-shell">
        <div className="company-create-heading">
          <button type="button" className="company-create-back" onClick={() => navigate('/companies')}>
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1>{isEditMode ? 'Редактировать компанию' : 'Добавить компанию'}</h1>
            <p>Форма покрывает поля `companies`, `company_contacts` и `company_bank_accounts`.</p>
          </div>
        </div>

        <form className="company-create-card" onSubmit={handleSubmit}>
          <section className="company-create-section">
            <div className="company-create-section__title">Основная информация</div>
            <div className="company-create-grid company-create-grid--3">
              <label className="company-create-field">
                <span>Наименование *</span>
                <input
                  type="text"
                  value={formState.legalName}
                  onChange={(event) => updateField('legalName', event.target.value)}
                  placeholder="Полное название компании"
                  required
                />
              </label>
              <label className="company-create-field">
                <span>Короткое наименование</span>
                <input
                  type="text"
                  value={formState.shortName}
                  onChange={(event) => updateField('shortName', event.target.value)}
                  placeholder="Например, BDS OU"
                />
              </label>
              <label className="company-create-field">
                <span>Статус</span>
                <input
                  type="text"
                  value={formState.status}
                  onChange={(event) => updateField('status', event.target.value)}
                  placeholder="active"
                />
              </label>
              <label className="company-create-field">
                <span>Регистрационный номер</span>
                <input
                  type="text"
                  value={formState.registrationNumber}
                  onChange={(event) => updateField('registrationNumber', event.target.value)}
                />
              </label>
              <label className="company-create-field">
                <span>VAT номер</span>
                <input
                  type="text"
                  value={formState.vatNumber}
                  onChange={(event) => updateField('vatNumber', event.target.value)}
                />
              </label>
              <label className="company-create-field">
                <span>Код страны</span>
                <input
                  type="text"
                  value={formState.countryCode}
                  onChange={(event) => updateField('countryCode', event.target.value.toUpperCase())}
                  maxLength={2}
                  placeholder="EE"
                />
              </label>
              <label className="company-create-field">
                <span>Email</span>
                <input
                  type="email"
                  value={formState.email}
                  onChange={(event) => updateField('email', event.target.value)}
                />
              </label>
              <label className="company-create-field">
                <span>Телефон</span>
                <input
                  type="text"
                  value={formState.phone}
                  onChange={(event) => updateField('phone', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="company-create-section">
            <div className="company-create-section__title">Адрес</div>
            <div className="company-create-grid company-create-grid--2">
              <label className="company-create-field">
                <span>Адрес 1</span>
                <input
                  type="text"
                  value={formState.addressLine1}
                  onChange={(event) => updateField('addressLine1', event.target.value)}
                />
              </label>
              <label className="company-create-field">
                <span>Адрес 2</span>
                <input
                  type="text"
                  value={formState.addressLine2}
                  onChange={(event) => updateField('addressLine2', event.target.value)}
                />
              </label>
              <label className="company-create-field">
                <span>Город</span>
                <input
                  type="text"
                  value={formState.city}
                  onChange={(event) => updateField('city', event.target.value)}
                />
              </label>
              <label className="company-create-field">
                <span>Почтовый индекс</span>
                <input
                  type="text"
                  value={formState.postalCode}
                  onChange={(event) => updateField('postalCode', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="company-create-section">
            <div className="company-create-section__header">
              <div>
                <div className="company-create-section__title">Контакты</div>
                <div className="company-create-section__meta">Заполнено контактов: {contactsCount}</div>
              </div>
              <button type="button" className="company-create-add" onClick={addContact}>
                <Plus size={16} />
                Добавить контакт
              </button>
            </div>

            <div className="company-create-stack">
              {formState.contacts.map((contact, index) => (
                <div key={contact.id} className="company-create-cardline">
                  <div className="company-create-cardline__top">
                    <strong>Контакт {index + 1}</strong>
                    <button type="button" className="company-create-delete" onClick={() => removeContact(contact.id)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="company-create-grid company-create-grid--4">
                    <label className="company-create-field">
                      <span>ФИО</span>
                      <input
                        type="text"
                        value={contact.fullName}
                        onChange={(event) => updateContact(contact.id, { fullName: event.target.value })}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>Роль</span>
                      <input
                        type="text"
                        value={contact.role}
                        onChange={(event) => updateContact(contact.id, { role: event.target.value })}
                        placeholder="director"
                      />
                    </label>
                    <label className="company-create-field">
                      <span>Email</span>
                      <input
                        type="email"
                        value={contact.email}
                        onChange={(event) => updateContact(contact.id, { email: event.target.value })}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>Телефон</span>
                      <input
                        type="text"
                        value={contact.phone}
                        onChange={(event) => updateContact(contact.id, { phone: event.target.value })}
                      />
                    </label>
                  </div>
                  <label className="company-create-check">
                    <input
                      type="checkbox"
                      checked={contact.isPrimary}
                      onChange={(event) => updateContact(contact.id, { isPrimary: event.target.checked })}
                    />
                    <span>Основной контакт</span>
                  </label>
                </div>
              ))}
            </div>
          </section>

          <section className="company-create-section">
            <div className="company-create-section__header">
              <div>
                <div className="company-create-section__title">Банковские счета</div>
                <div className="company-create-section__meta">Подготовлено счетов: {accountsCount}</div>
              </div>
              <button type="button" className="company-create-add" onClick={addAccount}>
                <Plus size={16} />
                Добавить счёт
              </button>
            </div>

            <datalist id="company-bank-options">
              {lookupState.banks.map((bank) => (
                <option key={bank.value} value={bank.label} />
              ))}
            </datalist>
            <datalist id="company-currency-options">
              {lookupState.currencies.map((currency) => (
                <option key={currency.value} value={currency.rawLabel || currency.value} />
              ))}
            </datalist>

            <div className="company-create-stack">
              {formState.bankAccounts.map((account, index) => (
                <div key={account.id} className="company-create-cardline">
                  <div className="company-create-cardline__top">
                    <strong>Счёт {index + 1}</strong>
                    <button type="button" className="company-create-delete" onClick={() => removeAccount(account.id)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="company-create-grid company-create-grid--4">
                    <label className="company-create-field">
                      <span>Банк</span>
                      <input
                        list="company-bank-options"
                        type="text"
                        value={account.bankText}
                        onChange={(event) => updateAccount(account.id, { bankText: event.target.value })}
                        placeholder={lookupState.isLoading ? 'Загрузка...' : 'Выберите существующий банк'}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>Валюта</span>
                      <input
                        list="company-currency-options"
                        type="text"
                        value={account.currencyText}
                        onChange={(event) => updateAccount(account.id, { currencyText: event.target.value.toUpperCase() })}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>Название счёта</span>
                      <input
                        type="text"
                        value={account.accountName}
                        onChange={(event) => updateAccount(account.id, { accountName: event.target.value })}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>IBAN</span>
                      <input
                        type="text"
                        value={account.iban}
                        onChange={(event) => updateAccount(account.id, { iban: event.target.value })}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>Номер счёта</span>
                      <input
                        type="text"
                        value={account.accountNumber}
                        onChange={(event) => updateAccount(account.id, { accountNumber: event.target.value })}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>BIC</span>
                      <input
                        type="text"
                        value={account.bic}
                        onChange={(event) => updateAccount(account.id, { bic: event.target.value })}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>Филиал банка</span>
                      <input
                        type="text"
                        value={account.bankBranch}
                        onChange={(event) => updateAccount(account.id, { bankBranch: event.target.value })}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>Открыт</span>
                      <input
                        type="date"
                        value={account.openedAt}
                        onChange={(event) => updateAccount(account.id, { openedAt: event.target.value })}
                      />
                    </label>
                    <label className="company-create-field">
                      <span>Закрыт</span>
                      <input
                        type="date"
                        value={account.closedAt}
                        onChange={(event) => updateAccount(account.id, { closedAt: event.target.value })}
                      />
                    </label>
                  </div>
                  <div className="company-create-checkrow">
                    <label className="company-create-check">
                      <input
                        type="checkbox"
                        checked={account.isPrimary}
                        onChange={(event) => updateAccount(account.id, { isPrimary: event.target.checked })}
                      />
                      <span>Основной счёт</span>
                    </label>
                    <label className="company-create-check">
                      <input
                        type="checkbox"
                        checked={account.isActive}
                        onChange={(event) => updateAccount(account.id, { isActive: event.target.checked })}
                      />
                      <span>Активен</span>
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="company-create-submit">
            {submitState.error ? <div className="company-create-message is-error">{submitState.error}</div> : null}
            {submitState.success ? <div className="company-create-message is-success">{submitState.success}</div> : null}
            <div className="company-create-submit__actions">
              <button type="button" className="company-create-button" onClick={() => navigate('/companies')}>
                Отмена
              </button>
              <button type="submit" className="company-create-button is-primary" disabled={submitState.isSubmitting}>
                <Save size={16} />
                {submitState.isSubmitting ? 'Сохраняю...' : isEditMode ? 'Сохранить изменения' : 'Сохранить компанию'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
