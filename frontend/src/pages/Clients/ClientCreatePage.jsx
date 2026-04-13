import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Save } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { createClient, fetchClient, updateClient } from '../../lib/api'
import './ClientCreatePage.css'

function createInitialState() {
  return {
    fullName: '',
    firstName: '',
    lastName: '',
    middleName: '',
    dateOfBirth: '',
    personalIdNumber: '',
    countryCode: '',
    taxResidencyCountryCode: '',
    email: '',
    phone: '',
    addressLine1: '',
    addressLine2: '',
    city: '',
    postalCode: '',
    notes: '',
    status: 'active',
  }
}

export default function ClientCreatePage() {
  const { clientId } = useParams()
  const isEditMode = Boolean(clientId)
  const navigate = useNavigate()
  const [formState, setFormState] = useState(() => createInitialState())
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
    if (!isEditMode || !clientId) {
      return undefined
    }

    let cancelled = false

    async function loadClient() {
      setPageState({
        isLoading: true,
        error: '',
      })

      try {
        const client = await fetchClient(clientId)
        if (cancelled) {
          return
        }

        setFormState({
          fullName: client.full_name || '',
          firstName: client.first_name || '',
          lastName: client.last_name || '',
          middleName: client.middle_name || '',
          dateOfBirth: client.date_of_birth || '',
          personalIdNumber: client.personal_id_number || '',
          countryCode: client.country_code || '',
          taxResidencyCountryCode: client.tax_residency_country_code || '',
          email: client.email || '',
          phone: client.phone || '',
          addressLine1: client.address_line1 || '',
          addressLine2: client.address_line2 || '',
          city: client.city || '',
          postalCode: client.postal_code || '',
          notes: client.notes || '',
          status: client.status || 'active',
        })
        setPageState({
          isLoading: false,
          error: '',
        })
      } catch (error) {
        if (!cancelled) {
          setPageState({
            isLoading: false,
            error: error.response?.data?.detail || 'Не удалось загрузить клиента',
          })
        }
      }
    }

    loadClient()

    return () => {
      cancelled = true
    }
  }, [clientId, isEditMode])

  const filledCoreFields = useMemo(
    () =>
      [
        formState.fullName,
        formState.firstName,
        formState.lastName,
        formState.middleName,
        formState.dateOfBirth,
        formState.personalIdNumber,
        formState.status,
      ].filter((value) => String(value || '').trim()).length,
    [formState],
  )

  const filledContactFields = useMemo(
    () =>
      [
        formState.countryCode,
        formState.taxResidencyCountryCode,
        formState.email,
        formState.phone,
        formState.addressLine1,
        formState.addressLine2,
        formState.city,
        formState.postalCode,
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
      if (!formState.fullName.trim()) {
        throw new Error('Поле "Полное имя" обязательно')
      }

      const payload = {
        full_name: formState.fullName.trim(),
        first_name: formState.firstName.trim() || null,
        last_name: formState.lastName.trim() || null,
        middle_name: formState.middleName.trim() || null,
        date_of_birth: formState.dateOfBirth || null,
        personal_id_number: formState.personalIdNumber.trim() || null,
        country_code: formState.countryCode.trim().toUpperCase() || null,
        tax_residency_country_code: formState.taxResidencyCountryCode.trim().toUpperCase() || null,
        email: formState.email.trim() || null,
        phone: formState.phone.trim() || null,
        address_line1: formState.addressLine1.trim() || null,
        address_line2: formState.addressLine2.trim() || null,
        city: formState.city.trim() || null,
        postal_code: formState.postalCode.trim() || null,
        notes: formState.notes.trim() || null,
        status: formState.status.trim() || 'active',
      }

      if (isEditMode && clientId) {
        await updateClient(clientId, payload)
      } else {
        await createClient(payload)
      }

      setSubmitState({
        isSubmitting: false,
        error: '',
        success: isEditMode ? 'Клиент обновлён' : 'Клиент сохранён',
      })
      window.setTimeout(() => navigate('/clients'), 500)
    } catch (error) {
      setSubmitState({
        isSubmitting: false,
        error: error.response?.data?.detail || error.message || 'Не удалось сохранить клиента',
        success: '',
      })
    }
  }

  return (
    <div className="client-create-page">
      <div className="client-create-shell">
        <div className="client-create-heading">
          <button type="button" className="client-create-back" onClick={() => navigate('/clients')}>
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1>{isEditMode ? 'Редактировать клиента' : 'Добавить клиента'}</h1>
            <p>Форма покрывает поля таблицы `clients` из базы данных.</p>
          </div>
        </div>

        <form className="client-create-card" onSubmit={handleSubmit}>
          <section className="client-create-section">
            <div className="client-create-section__header">
              <div>
                <div className="client-create-section__title">Основная информация</div>
                <div className="client-create-section__meta">Заполнено полей: {filledCoreFields}</div>
              </div>
            </div>
            <div className="client-create-grid client-create-grid--3">
              <label className="client-create-field">
                <span>Полное имя *</span>
                <input
                  type="text"
                  value={formState.fullName}
                  onChange={(event) => updateField('fullName', event.target.value)}
                  placeholder="Имя клиента как в документах"
                  required
                />
              </label>
              <label className="client-create-field">
                <span>Имя</span>
                <input
                  type="text"
                  value={formState.firstName}
                  onChange={(event) => updateField('firstName', event.target.value)}
                />
              </label>
              <label className="client-create-field">
                <span>Фамилия</span>
                <input
                  type="text"
                  value={formState.lastName}
                  onChange={(event) => updateField('lastName', event.target.value)}
                />
              </label>
              <label className="client-create-field">
                <span>Отчество / middle name</span>
                <input
                  type="text"
                  value={formState.middleName}
                  onChange={(event) => updateField('middleName', event.target.value)}
                />
              </label>
              <label className="client-create-field">
                <span>Дата рождения</span>
                <input
                  type="date"
                  value={formState.dateOfBirth}
                  onChange={(event) => updateField('dateOfBirth', event.target.value)}
                />
              </label>
              <label className="client-create-field">
                <span>Личный код / ID номер</span>
                <input
                  type="text"
                  value={formState.personalIdNumber}
                  onChange={(event) => updateField('personalIdNumber', event.target.value)}
                />
              </label>
              <label className="client-create-field">
                <span>Статус</span>
                <input
                  type="text"
                  value={formState.status}
                  onChange={(event) => updateField('status', event.target.value)}
                  placeholder="active"
                />
              </label>
            </div>
          </section>

          <section className="client-create-section">
            <div className="client-create-section__header">
              <div>
                <div className="client-create-section__title">Контакты и налоговая привязка</div>
                <div className="client-create-section__meta">Заполнено полей: {filledContactFields}</div>
              </div>
            </div>
            <div className="client-create-grid client-create-grid--3">
              <label className="client-create-field">
                <span>Код страны</span>
                <input
                  type="text"
                  value={formState.countryCode}
                  onChange={(event) => updateField('countryCode', event.target.value.toUpperCase())}
                  maxLength={2}
                  placeholder="EE"
                />
              </label>
              <label className="client-create-field">
                <span>Налоговое резидентство</span>
                <input
                  type="text"
                  value={formState.taxResidencyCountryCode}
                  onChange={(event) => updateField('taxResidencyCountryCode', event.target.value.toUpperCase())}
                  maxLength={2}
                  placeholder="EE"
                />
              </label>
              <label className="client-create-field">
                <span>Email</span>
                <input
                  type="email"
                  value={formState.email}
                  onChange={(event) => updateField('email', event.target.value)}
                />
              </label>
              <label className="client-create-field">
                <span>Телефон</span>
                <input
                  type="text"
                  value={formState.phone}
                  onChange={(event) => updateField('phone', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="client-create-section">
            <div className="client-create-section__title">Адрес</div>
            <div className="client-create-grid client-create-grid--2">
              <label className="client-create-field">
                <span>Адрес 1</span>
                <input
                  type="text"
                  value={formState.addressLine1}
                  onChange={(event) => updateField('addressLine1', event.target.value)}
                />
              </label>
              <label className="client-create-field">
                <span>Адрес 2</span>
                <input
                  type="text"
                  value={formState.addressLine2}
                  onChange={(event) => updateField('addressLine2', event.target.value)}
                />
              </label>
              <label className="client-create-field">
                <span>Город</span>
                <input
                  type="text"
                  value={formState.city}
                  onChange={(event) => updateField('city', event.target.value)}
                />
              </label>
              <label className="client-create-field">
                <span>Почтовый индекс</span>
                <input
                  type="text"
                  value={formState.postalCode}
                  onChange={(event) => updateField('postalCode', event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="client-create-section">
            <div className="client-create-section__title">Примечание</div>
            <label className="client-create-field">
              <span>Notes</span>
              <textarea
                value={formState.notes}
                onChange={(event) => updateField('notes', event.target.value)}
                placeholder="Дополнительная информация по клиенту"
              />
            </label>
          </section>

          {pageState.error ? <div className="client-create-message is-error">{pageState.error}</div> : null}

          <div className="client-create-submit">
            {submitState.error ? <div className="client-create-message is-error">{submitState.error}</div> : null}
            {submitState.success ? <div className="client-create-message is-success">{submitState.success}</div> : null}
            <div className="client-create-submit__actions">
              <button type="button" className="client-create-button" onClick={() => navigate('/clients')}>
                Отмена
              </button>
              <button type="submit" className="client-create-button is-primary" disabled={submitState.isSubmitting || pageState.isLoading}>
                <Save size={16} />
                {pageState.isLoading
                  ? 'Загружаю...'
                  : submitState.isSubmitting
                    ? 'Сохраняю...'
                    : isEditMode
                      ? 'Сохранить изменения'
                      : 'Сохранить клиента'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
