import { useEffect, useState } from 'react'
import { ArrowLeft, Save } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { createBankAccount } from '../../lib/api'
import { findLookupOption, loadLookup, requireLookupValue } from '../Payments/paymentUtils'
import './BankAccountCreatePage.css'

function createInitialState() {
  return {
    companyText: '',
    bankLookupText: '',
    bankName: '',
    bankShortName: '',
    bankSwiftCode: '',
    bankCountryCode: '',
    bankAddressLine1: '',
    bankAddressLine2: '',
    bankCity: '',
    bankPostalCode: '',
    bankWebsite: '',
    currencyText: 'EUR',
    accountName: '',
    iban: '',
    accountNumber: '',
    bic: '',
    bankBranch: '',
    openedAt: '',
    closedAt: '',
    isPrimary: false,
    isActive: true,
  }
}

export default function BankAccountCreatePage() {
  const navigate = useNavigate()
  const [formState, setFormState] = useState(() => createInitialState())
  const [lookupState, setLookupState] = useState({
    companies: [],
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

    async function loadLookups() {
      try {
        const [companies, banks, currencies] = await Promise.all([
          loadLookup('companies', ''),
          loadLookup('banks', ''),
          loadLookup('currencies', ''),
        ])

        if (!cancelled) {
          setLookupState({
            companies,
            banks,
            currencies,
            isLoading: false,
          })
        }
      } catch {
        if (!cancelled) {
          setLookupState({
            companies: [],
            banks: [],
            currencies: [],
            isLoading: false,
          })
        }
      }
    }

    loadLookups()

    return () => {
      cancelled = true
    }
  }, [])

  function updateField(name, value) {
    setFormState((current) => ({ ...current, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitState({ isSubmitting: true, error: '', success: '' })

    try {
      const company = requireLookupValue(
        'companies',
        null,
        formState.companyText,
        lookupState.companies,
        'Нужно выбрать существующую компанию',
      )

      const currency = requireLookupValue(
        'currencies',
        null,
        formState.currencyText || 'EUR',
        lookupState.currencies,
        'Нужно выбрать существующую валюту',
      )

      const matchedBank = findLookupOption('banks', formState.bankLookupText, lookupState.banks)

      const payload = {
        company_id: company.value,
        bank_id: matchedBank?.value ?? null,
        bank_name: matchedBank ? null : formState.bankName.trim() || null,
        bank_short_name: matchedBank ? null : formState.bankShortName.trim() || null,
        bank_swift_code: matchedBank ? null : formState.bankSwiftCode.trim() || null,
        bank_country_code: matchedBank ? null : formState.bankCountryCode.trim().toUpperCase() || null,
        bank_address_line1: matchedBank ? null : formState.bankAddressLine1.trim() || null,
        bank_address_line2: matchedBank ? null : formState.bankAddressLine2.trim() || null,
        bank_city: matchedBank ? null : formState.bankCity.trim() || null,
        bank_postal_code: matchedBank ? null : formState.bankPostalCode.trim() || null,
        bank_website: matchedBank ? null : formState.bankWebsite.trim() || null,
        currency_code: currency.rawLabel || currency.value,
        account_name: formState.accountName.trim() || null,
        iban: formState.iban.trim() || null,
        account_number: formState.accountNumber.trim() || null,
        bic: formState.bic.trim() || null,
        bank_branch: formState.bankBranch.trim() || null,
        is_primary: formState.isPrimary,
        is_active: formState.isActive,
        opened_at: formState.openedAt || null,
        closed_at: formState.closedAt || null,
      }

      if (!payload.bank_id && !payload.bank_name && !payload.bank_short_name) {
        throw new Error('Укажите существующий банк или заполните реквизиты нового банка')
      }

      await createBankAccount(payload)
      setSubmitState({ isSubmitting: false, error: '', success: 'Счёт сохранён' })
      window.setTimeout(() => navigate('/banks'), 500)
    } catch (error) {
      setSubmitState({
        isSubmitting: false,
        error: error.response?.data?.detail || error.message || 'Не удалось сохранить счёт',
        success: '',
      })
    }
  }

  return (
    <div className="bank-account-create-page">
      <div className="bank-account-create-shell">
        <div className="bank-account-create-heading">
          <button type="button" className="bank-account-create-back" onClick={() => navigate('/banks')}>
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1>Добавить счёт</h1>
            <p>Форма покрывает поля `banks` и `company_bank_accounts`.</p>
          </div>
        </div>

        <form className="bank-account-create-card" onSubmit={handleSubmit}>
          <section className="bank-account-create-section">
            <div className="bank-account-create-section__title">Привязка счёта</div>
            <div className="bank-account-create-grid bank-account-create-grid--3">
              <label className="bank-account-create-field">
                <span>Компания *</span>
                <input
                  list="bank-account-company-options"
                  type="text"
                  value={formState.companyText}
                  onChange={(event) => updateField('companyText', event.target.value)}
                  placeholder={lookupState.isLoading ? 'Загрузка...' : 'Выберите существующую компанию'}
                  required
                />
              </label>
              <label className="bank-account-create-field">
                <span>Банк из списка</span>
                <input
                  list="bank-account-bank-options"
                  type="text"
                  value={formState.bankLookupText}
                  onChange={(event) => updateField('bankLookupText', event.target.value)}
                  placeholder="Если банк уже существует"
                />
              </label>
              <label className="bank-account-create-field">
                <span>Валюта *</span>
                <input
                  list="bank-account-currency-options"
                  type="text"
                  value={formState.currencyText}
                  onChange={(event) => updateField('currencyText', event.target.value.toUpperCase())}
                  placeholder="Выберите существующую валюту"
                  required
                />
              </label>
            </div>

            <datalist id="bank-account-company-options">
              {lookupState.companies.map((item) => (
                <option key={item.value} value={item.label} />
              ))}
            </datalist>
            <datalist id="bank-account-bank-options">
              {lookupState.banks.map((item) => (
                <option key={item.value} value={item.label} />
              ))}
            </datalist>
            <datalist id="bank-account-currency-options">
              {lookupState.currencies.map((item) => (
                <option key={item.value} value={item.rawLabel || item.value} />
              ))}
            </datalist>
          </section>

          <section className="bank-account-create-section">
            <div className="bank-account-create-section__title">Реквизиты банка</div>
            <div className="bank-account-create-grid bank-account-create-grid--3">
              <label className="bank-account-create-field">
                <span>Полное название банка</span>
                <input
                  type="text"
                  value={formState.bankName}
                  onChange={(event) => updateField('bankName', event.target.value)}
                  placeholder="Нужно только для нового банка"
                />
              </label>
              <label className="bank-account-create-field">
                <span>Короткое название банка</span>
                <input
                  type="text"
                  value={formState.bankShortName}
                  onChange={(event) => updateField('bankShortName', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>SWIFT</span>
                <input
                  type="text"
                  value={formState.bankSwiftCode}
                  onChange={(event) => updateField('bankSwiftCode', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Код страны</span>
                <input
                  type="text"
                  value={formState.bankCountryCode}
                  onChange={(event) => updateField('bankCountryCode', event.target.value.toUpperCase())}
                  maxLength={2}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Сайт</span>
                <input
                  type="text"
                  value={formState.bankWebsite}
                  onChange={(event) => updateField('bankWebsite', event.target.value)}
                />
              </label>
            </div>
            <div className="bank-account-create-grid bank-account-create-grid--3">
              <label className="bank-account-create-field">
                <span>Адрес 1</span>
                <input
                  type="text"
                  value={formState.bankAddressLine1}
                  onChange={(event) => updateField('bankAddressLine1', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Адрес 2</span>
                <input
                  type="text"
                  value={formState.bankAddressLine2}
                  onChange={(event) => updateField('bankAddressLine2', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Город</span>
                <input
                  type="text"
                  value={formState.bankCity}
                  onChange={(event) => updateField('bankCity', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Почтовый индекс</span>
                <input
                  type="text"
                  value={formState.bankPostalCode}
                  onChange={(event) => updateField('bankPostalCode', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="bank-account-create-section">
            <div className="bank-account-create-section__title">Реквизиты счёта</div>
            <div className="bank-account-create-grid bank-account-create-grid--3">
              <label className="bank-account-create-field">
                <span>Название счёта</span>
                <input
                  type="text"
                  value={formState.accountName}
                  onChange={(event) => updateField('accountName', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>IBAN</span>
                <input
                  type="text"
                  value={formState.iban}
                  onChange={(event) => updateField('iban', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Номер счёта</span>
                <input
                  type="text"
                  value={formState.accountNumber}
                  onChange={(event) => updateField('accountNumber', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>BIC</span>
                <input
                  type="text"
                  value={formState.bic}
                  onChange={(event) => updateField('bic', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Филиал банка</span>
                <input
                  type="text"
                  value={formState.bankBranch}
                  onChange={(event) => updateField('bankBranch', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Открыт</span>
                <input
                  type="date"
                  value={formState.openedAt}
                  onChange={(event) => updateField('openedAt', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Закрыт</span>
                <input
                  type="date"
                  value={formState.closedAt}
                  onChange={(event) => updateField('closedAt', event.target.value)}
                />
              </label>
            </div>
            <div className="bank-account-create-checkrow">
              <label className="bank-account-create-check">
                <input
                  type="checkbox"
                  checked={formState.isPrimary}
                  onChange={(event) => updateField('isPrimary', event.target.checked)}
                />
                <span>Основной счёт</span>
              </label>
              <label className="bank-account-create-check">
                <input
                  type="checkbox"
                  checked={formState.isActive}
                  onChange={(event) => updateField('isActive', event.target.checked)}
                />
                <span>Активен</span>
              </label>
            </div>
          </section>

          <div className="bank-account-create-submit">
            {submitState.error ? <div className="bank-account-create-message is-error">{submitState.error}</div> : null}
            {submitState.success ? <div className="bank-account-create-message is-success">{submitState.success}</div> : null}
            <div className="bank-account-create-submit__actions">
              <button type="button" className="bank-account-create-button" onClick={() => navigate('/banks')}>
                Отмена
              </button>
              <button type="submit" className="bank-account-create-button is-primary" disabled={submitState.isSubmitting}>
                <Save size={16} />
                {submitState.isSubmitting ? 'Сохраняю...' : 'Сохранить счёт'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
