import { useState } from 'react'
import { ArrowLeft, Save } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { createBank } from '../../lib/api'
import './BankAccountCreatePage.css'

function createInitialState() {
  return {
    name: '',
    shortName: '',
    swiftCode: '',
    countryCode: '',
    website: '',
    addressLine1: '',
    addressLine2: '',
    city: '',
    postalCode: '',
  }
}

export default function BankCreatePage() {
  const navigate = useNavigate()
  const [formState, setFormState] = useState(() => createInitialState())
  const [submitState, setSubmitState] = useState({
    isSubmitting: false,
    error: '',
    success: '',
  })

  function updateField(name, value) {
    setFormState((current) => ({ ...current, [name]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitState({ isSubmitting: true, error: '', success: '' })

    try {
      await createBank({
        name: formState.name.trim(),
        short_name: formState.shortName.trim() || null,
        swift_code: formState.swiftCode.trim() || null,
        country_code: formState.countryCode.trim().toUpperCase() || null,
        website: formState.website.trim() || null,
        address_line1: formState.addressLine1.trim() || null,
        address_line2: formState.addressLine2.trim() || null,
        city: formState.city.trim() || null,
        postal_code: formState.postalCode.trim() || null,
      })

      setSubmitState({ isSubmitting: false, error: '', success: 'Банк сохранён' })
      window.setTimeout(() => navigate('/banks'), 500)
    } catch (error) {
      setSubmitState({
        isSubmitting: false,
        error: error.response?.data?.detail || error.message || 'Не удалось сохранить банк',
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
            <h1>Добавить банк</h1>
            <p>Банк создаётся отдельно и потом может использоваться в одном или нескольких счетах.</p>
          </div>
        </div>

        <form className="bank-account-create-card" onSubmit={handleSubmit}>
          <section className="bank-account-create-section">
            <div className="bank-account-create-section__title">Реквизиты банка</div>
            <div className="bank-account-create-grid bank-account-create-grid--3">
              <label className="bank-account-create-field">
                <span>Полное название банка *</span>
                <input
                  type="text"
                  value={formState.name}
                  onChange={(event) => updateField('name', event.target.value)}
                  required
                />
              </label>
              <label className="bank-account-create-field">
                <span>Короткое название банка</span>
                <input
                  type="text"
                  value={formState.shortName}
                  onChange={(event) => updateField('shortName', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>SWIFT</span>
                <input
                  type="text"
                  value={formState.swiftCode}
                  onChange={(event) => updateField('swiftCode', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Код страны</span>
                <input
                  type="text"
                  value={formState.countryCode}
                  onChange={(event) => updateField('countryCode', event.target.value.toUpperCase())}
                  maxLength={2}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Сайт</span>
                <input
                  type="text"
                  value={formState.website}
                  onChange={(event) => updateField('website', event.target.value)}
                />
              </label>
            </div>

            <div className="bank-account-create-grid bank-account-create-grid--3">
              <label className="bank-account-create-field">
                <span>Адрес 1</span>
                <input
                  type="text"
                  value={formState.addressLine1}
                  onChange={(event) => updateField('addressLine1', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Адрес 2</span>
                <input
                  type="text"
                  value={formState.addressLine2}
                  onChange={(event) => updateField('addressLine2', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Город</span>
                <input
                  type="text"
                  value={formState.city}
                  onChange={(event) => updateField('city', event.target.value)}
                />
              </label>
              <label className="bank-account-create-field">
                <span>Почтовый индекс</span>
                <input
                  type="text"
                  value={formState.postalCode}
                  onChange={(event) => updateField('postalCode', event.target.value)}
                />
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
                {submitState.isSubmitting ? 'Сохраняю...' : 'Сохранить банк'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
