import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Save } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { createCounterparty, fetchCounterparty, updateCounterparty } from '../../lib/api'
import { loadLookup, requireLookupValue } from '../Payments/paymentUtils'
import './CounterpartyCreatePage.css'

function createInitialState() {
  return {
    clientText: '',
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
    website: '',
    notes: '',
    status: 'active',
  }
}

export default function CounterpartyCreatePage() {
  const { counterpartyId } = useParams()
  const isEditMode = Boolean(counterpartyId)
  const navigate = useNavigate()
  const [formState, setFormState] = useState(() => createInitialState())
  const [lookupState, setLookupState] = useState({
    clients: [],
    isLoading: true,
  })
  const [pageState, setPageState] = useState({
    isLoading: isEditMode,
    error: '',
  })
  const [submitState, setSubmitState] = useState({
    isSubmitting: false,
    error: '',
    success: '',
  })

  useEffect(() => {
    let cancelled = false

    async function loadClientsAndCounterparty() {
      try {
        const clients = await loadLookup('clients', '')

        if (cancelled) {
          return
        }

        setLookupState({
          clients,
          isLoading: false,
        })

        if (isEditMode && counterpartyId) {
          const counterparty = await fetchCounterparty(counterpartyId)
          if (cancelled) {
            return
          }

          setFormState({
            clientText: counterparty.client_name || '',
            legalName: counterparty.legal_name || '',
            shortName: counterparty.short_name || '',
            registrationNumber: counterparty.registration_number || '',
            vatNumber: counterparty.vat_number || '',
            countryCode: counterparty.country_code || '',
            addressLine1: counterparty.address_line1 || '',
            addressLine2: counterparty.address_line2 || '',
            city: counterparty.city || '',
            postalCode: counterparty.postal_code || '',
            email: counterparty.email || '',
            phone: counterparty.phone || '',
            website: counterparty.website || '',
            notes: counterparty.notes || '',
            status: counterparty.status || 'active',
          })
        }

        setPageState({
          isLoading: false,
          error: '',
        })
      } catch (error) {
        if (!cancelled) {
          setLookupState({
            clients: [],
            isLoading: false,
          })
          setPageState({
            isLoading: false,
            error: error.response?.data?.detail || 'Не удалось загрузить форму контрагента',
          })
        }
      }
    }

    loadClientsAndCounterparty()

    return () => {
      cancelled = true
    }
  }, [counterpartyId, isEditMode])

  const filledCompanyFields = useMemo(
    () =>
      [
        formState.clientText,
        formState.legalName,
        formState.shortName,
        formState.registrationNumber,
        formState.vatNumber,
        formState.status,
      ].filter((value) => String(value || '').trim()).length,
    [formState],
  )

  function updateField(name, value) {
    setFormState((current) => ({
      ...current,
      [name]: value,
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

      const client = requireLookupValue(
        'clients',
        null,
        formState.clientText,
        lookupState.clients,
        'Нужно выбрать существующего клиента',
      )

      const payload = {
        client_id: client.value,
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
        website: formState.website.trim() || null,
        notes: formState.notes.trim() || null,
        status: formState.status.trim() || 'active',
      }

      if (isEditMode && counterpartyId) {
        await updateCounterparty(counterpartyId, payload)
      } else {
        await createCounterparty(payload)
      }

      setSubmitState({
        isSubmitting: false,
        error: '',
        success: isEditMode ? 'Контрагент обновлён' : 'Контрагент сохранён',
      })
      window.setTimeout(() => navigate('/counterparties'), 500)
    } catch (error) {
      setSubmitState({
        isSubmitting: false,
        error: error.response?.data?.detail || error.message || 'Не удалось сохранить контрагента',
        success: '',
      })
    }
  }

  return (
    <div className="counterparty-create-page">
      <div className="counterparty-create-shell">
        <div className="counterparty-create-heading">
          <button type="button" className="counterparty-create-back" onClick={() => navigate('/counterparties')}>
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1>{isEditMode ? 'Редактировать контрагента' : 'Добавить контрагента'}</h1>
            <p>Форма покрывает поля таблицы `counterparties` и обязательную связку с клиентом.</p>
          </div>
        </div>

        <form className="counterparty-create-card" onSubmit={handleSubmit}>
          <section className="counterparty-create-section">
            <div className="counterparty-create-section__header">
              <div>
                <div className="counterparty-create-section__title">Основная информация</div>
                <div className="counterparty-create-section__meta">Заполнено полей: {filledCompanyFields}</div>
              </div>
            </div>
            <div className="counterparty-create-grid counterparty-create-grid--3">
              <label className="counterparty-create-field">
                <span>Клиент *</span>
                <input
                  list="counterparty-client-options"
                  type="text"
                  value={formState.clientText}
                  onChange={(event) => updateField('clientText', event.target.value)}
                  placeholder={lookupState.isLoading ? 'Загрузка...' : 'Выберите клиента из справочника'}
                  required
                />
              </label>
              <label className="counterparty-create-field">
                <span>Наименование *</span>
                <input
                  type="text"
                  value={formState.legalName}
                  onChange={(event) => updateField('legalName', event.target.value)}
                  placeholder="Полное название контрагента"
                  required
                />
              </label>
              <label className="counterparty-create-field">
                <span>Короткое наименование</span>
                <input
                  type="text"
                  value={formState.shortName}
                  onChange={(event) => updateField('shortName', event.target.value)}
                />
              </label>
              <label className="counterparty-create-field">
                <span>Регистрационный номер</span>
                <input
                  type="text"
                  value={formState.registrationNumber}
                  onChange={(event) => updateField('registrationNumber', event.target.value)}
                />
              </label>
              <label className="counterparty-create-field">
                <span>VAT номер</span>
                <input
                  type="text"
                  value={formState.vatNumber}
                  onChange={(event) => updateField('vatNumber', event.target.value)}
                />
              </label>
              <label className="counterparty-create-field">
                <span>Статус</span>
                <input
                  type="text"
                  value={formState.status}
                  onChange={(event) => updateField('status', event.target.value)}
                  placeholder="active"
                />
              </label>
            </div>

            <datalist id="counterparty-client-options">
              {lookupState.clients.map((item) => (
                <option key={item.value} value={item.label} />
              ))}
            </datalist>
          </section>

          <section className="counterparty-create-section">
            <div className="counterparty-create-section__title">Контакты</div>
            <div className="counterparty-create-grid counterparty-create-grid--3">
              <label className="counterparty-create-field">
                <span>Код страны</span>
                <input
                  type="text"
                  value={formState.countryCode}
                  onChange={(event) => updateField('countryCode', event.target.value.toUpperCase())}
                  maxLength={2}
                  placeholder="EE"
                />
              </label>
              <label className="counterparty-create-field">
                <span>Email</span>
                <input
                  type="email"
                  value={formState.email}
                  onChange={(event) => updateField('email', event.target.value)}
                />
              </label>
              <label className="counterparty-create-field">
                <span>Телефон</span>
                <input
                  type="text"
                  value={formState.phone}
                  onChange={(event) => updateField('phone', event.target.value)}
                />
              </label>
              <label className="counterparty-create-field">
                <span>Сайт</span>
                <input
                  type="text"
                  value={formState.website}
                  onChange={(event) => updateField('website', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="counterparty-create-section">
            <div className="counterparty-create-section__title">Адрес</div>
            <div className="counterparty-create-grid counterparty-create-grid--2">
              <label className="counterparty-create-field">
                <span>Адрес 1</span>
                <input
                  type="text"
                  value={formState.addressLine1}
                  onChange={(event) => updateField('addressLine1', event.target.value)}
                />
              </label>
              <label className="counterparty-create-field">
                <span>Адрес 2</span>
                <input
                  type="text"
                  value={formState.addressLine2}
                  onChange={(event) => updateField('addressLine2', event.target.value)}
                />
              </label>
              <label className="counterparty-create-field">
                <span>Город</span>
                <input
                  type="text"
                  value={formState.city}
                  onChange={(event) => updateField('city', event.target.value)}
                />
              </label>
              <label className="counterparty-create-field">
                <span>Почтовый индекс</span>
                <input
                  type="text"
                  value={formState.postalCode}
                  onChange={(event) => updateField('postalCode', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="counterparty-create-section">
            <div className="counterparty-create-section__title">Примечание</div>
            <label className="counterparty-create-field">
              <span>Notes</span>
              <textarea
                value={formState.notes}
                onChange={(event) => updateField('notes', event.target.value)}
                placeholder="Дополнительная информация по контрагенту"
              />
            </label>
          </section>

          {pageState.error ? <div className="counterparty-create-message is-error">{pageState.error}</div> : null}

          <div className="counterparty-create-submit">
            {submitState.error ? <div className="counterparty-create-message is-error">{submitState.error}</div> : null}
            {submitState.success ? <div className="counterparty-create-message is-success">{submitState.success}</div> : null}
            <div className="counterparty-create-submit__actions">
              <button type="button" className="counterparty-create-button" onClick={() => navigate('/counterparties')}>
                Отмена
              </button>
              <button
                type="submit"
                className="counterparty-create-button is-primary"
                disabled={submitState.isSubmitting || pageState.isLoading}
              >
                <Save size={16} />
                {pageState.isLoading
                  ? 'Загружаю...'
                  : submitState.isSubmitting
                    ? 'Сохраняю...'
                    : isEditMode
                      ? 'Сохранить изменения'
                      : 'Сохранить контрагента'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
