import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeft,
  CalendarDays,
  ChevronDown,
  ChevronUp,
  Eye,
  GripVertical,
  Paperclip,
  Plus,
  Save,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import LookupField from '../../components/LookupField/LookupField'
import { createPaymentsBatch } from '../../lib/api'
import {
  findLookupOption,
  formatAmount,
  loadLookup,
  requireLookupValue,
  toDateInputValue,
  toNumber,
} from './paymentUtils'
import './AddPaymentsPage.css'

const DRAFT_STORAGE_KEY = 'acc-app:add-payments-draft'

function createRow() {
  return {
    id: crypto.randomUUID(),
    counterpartyName: '',
    amount: '',
    tax: '',
    incomeExpense: '',
    clientText: '',
    comment: '',
    expanded: false,
    attachments: [],
  }
}

function createInitialState() {
  return {
    bookingDate: toDateInputValue(new Date()),
    bankAccount: null,
    bankAccountText: '',
    rows: [createRow(), createRow()],
  }
}

function buildRowNotes(row) {
  return row.comment.trim() || null
}

function buildDraftState(state) {
  return {
    ...state,
    rows: state.rows.map((row) => ({
      ...row,
      attachments: [],
    })),
  }
}

export default function AddPaymentsPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const [optionsState, setOptionsState] = useState({
    clients: [],
    isLoading: true,
    error: '',
  })
  const [formState, setFormState] = useState(() => createInitialState())
  const [message, setMessage] = useState({ type: '', text: '' })
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadReferenceData() {
      try {
        const clients = await loadLookup('clients', '')

        if (cancelled) {
          return
        }

        const draftRaw = window.localStorage.getItem(DRAFT_STORAGE_KEY)
        if (draftRaw) {
          try {
            const draft = JSON.parse(draftRaw)
            setFormState({
              bookingDate: draft.bookingDate || toDateInputValue(new Date()),
              bankAccount: draft.bankAccount || null,
              bankAccountText: draft.bankAccountText || draft.bankAccount?.label || '',
              rows:
                draft.rows?.length
                  ? draft.rows.map((row) => ({
                      ...createRow(),
                      ...row,
                      attachments: [],
                    }))
                  : [createRow()],
            })
          } catch {
            // Ignore malformed drafts and keep the default form state.
          }
        }

        setOptionsState({
          clients,
          isLoading: false,
          error: '',
        })
      } catch {
        if (!cancelled) {
          setOptionsState({
            clients: [],
            isLoading: false,
            error: 'Не удалось загрузить справочники',
          })
        }
      }
    }

    loadReferenceData()

    return () => {
      cancelled = true
    }
  }, [])

  const totals = useMemo(() => {
    const incoming = formState.rows.reduce((total, row) => {
      const amount = toNumber(row.amount)
      return amount > 0 ? total + amount : total
    }, 0)
    const outgoing = formState.rows.reduce((total, row) => {
      const amount = toNumber(row.amount)
      return amount < 0 ? total + Math.abs(amount) : total
    }, 0)

    return { incoming, outgoing }
  }, [formState.rows])

  function updateFormField(name, value) {
    setFormState((current) => ({ ...current, [name]: value }))
  }

  function updateRow(rowId, patch) {
    setFormState((current) => ({
      ...current,
      rows: current.rows.map((row) => (row.id === rowId ? { ...row, ...patch } : row)),
    }))
  }

  function addRow(afterRowId = null) {
    setFormState((current) => {
      const nextRow = createRow()
      if (!afterRowId) {
        return { ...current, rows: [...current.rows, nextRow] }
      }

      const index = current.rows.findIndex((row) => row.id === afterRowId)
      if (index === -1) {
        return { ...current, rows: [...current.rows, nextRow] }
      }

      const nextRows = [...current.rows]
      nextRows.splice(index + 1, 0, nextRow)
      return { ...current, rows: nextRows }
    })
  }

  function removeRow(rowId) {
    setFormState((current) => {
      if (current.rows.length === 1) {
        return { ...current, rows: [createRow()] }
      }

      return {
        ...current,
        rows: current.rows.filter((row) => row.id !== rowId),
      }
    })
  }

  function toggleExpanded(rowId) {
    setFormState((current) => ({
      ...current,
      rows: current.rows.map((row) =>
        row.id === rowId ? { ...row, expanded: !row.expanded } : { ...row, expanded: false },
      ),
    }))
  }

  function handleSaveDraft() {
    window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(buildDraftState(formState)))
    setMessage({ type: 'success', text: 'Черновик сохранён локально' })
  }

  function handleReset() {
    setFormState(createInitialState())
    setMessage({ type: '', text: '' })
  }

  function handleClearRows() {
    setFormState((current) => ({
      ...current,
      rows: [createRow()],
    }))
    setMessage({ type: '', text: '' })
  }

  function handleLoadDraft() {
    const draftRaw = window.localStorage.getItem(DRAFT_STORAGE_KEY)
    if (!draftRaw) {
      setMessage({ type: 'error', text: 'Сохранённый черновик не найден' })
      return
    }

    try {
      const draft = JSON.parse(draftRaw)
      setFormState({
        bookingDate: draft.bookingDate || toDateInputValue(new Date()),
        bankAccount: draft.bankAccount || null,
        bankAccountText: draft.bankAccountText || draft.bankAccount?.label || '',
        rows:
          draft.rows?.length
            ? draft.rows.map((row) => ({
                ...createRow(),
                ...row,
                attachments: [],
              }))
            : [createRow()],
      })
      setMessage({ type: 'success', text: 'Черновик загружен' })
    } catch {
      setMessage({ type: 'error', text: 'Не удалось прочитать черновик' })
    }
  }

  async function handleSave() {
    setMessage({ type: '', text: '' })
    setIsSaving(true)

    try {
      const bankAccount = requireLookupValue(
        'companyBankAccounts',
        formState.bankAccount,
        formState.bankAccountText,
        [],
        'Нужно выбрать существующий банковский счёт компании',
      )

      const rowsToSave = formState.rows.filter(
        (row) => row.counterpartyName.trim() || row.clientText.trim() || row.comment.trim() || row.amount,
      )

      if (rowsToSave.length === 0) {
        throw new Error('Добавьте хотя бы одну строку платежа')
      }

      const items = []
      for (const row of rowsToSave) {
        const amount = toNumber(row.amount)
        if (!amount) {
          throw new Error('Каждая строка должна содержать сумму')
        }

        const matchedClient = findLookupOption('clients', row.clientText, optionsState.clients)
        if (row.clientText.trim() && !matchedClient) {
          throw new Error(`Клиент "${row.clientText.trim()}" не найден в справочнике`)
        }
        const client = matchedClient || null

        if (client && !row.counterpartyName.trim()) {
          throw new Error('Для строк с клиентом нужно указать контрагента')
        }

        items.push({
          company_bank_account_id: bankAccount.value,
          booking_date: formState.bookingDate,
          value_date: formState.bookingDate,
          transaction_date: formState.bookingDate,
          amount_original: Math.abs(amount),
          amount_eur: bankAccount.currencyCode === 'EUR' ? null : Math.abs(amount),
          vat_amount_eur: Math.abs(toNumber(row.tax)),
          company_commission_amount_eur: toNumber(row.incomeExpense),
          payment_direction: amount >= 0 ? 'incoming' : 'outgoing',
          client_id: client?.value ?? null,
          counterparty_name: client ? row.counterpartyName.trim() : null,
          payment_purpose: row.counterpartyName.trim() || null,
          notes: buildRowNotes(row),
          attachments: row.attachments.map((attachment) => ({
            file_name: attachment.fileName,
            content_type: attachment.contentType,
            file_content_base64: attachment.base64,
          })),
        })
      }

      await createPaymentsBatch(items)
      window.localStorage.removeItem(DRAFT_STORAGE_KEY)
      setMessage({ type: 'success', text: 'Платежи сохранены' })
      window.setTimeout(() => navigate('/payments'), 600)
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || error.message || 'Не удалось сохранить платежи',
      })
    } finally {
      setIsSaving(false)
    }
  }

  function handleFilePick(event) {
    const [file] = event.target.files || []
    if (!file) {
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      try {
        const draft = JSON.parse(String(reader.result))
        setFormState({
          bookingDate: draft.bookingDate || toDateInputValue(new Date()),
          bankAccount: draft.bankAccount || null,
          bankAccountText: draft.bankAccountText || draft.bankAccount?.label || '',
          rows:
            draft.rows?.length
              ? draft.rows.map((row) => ({
                  ...createRow(),
                  ...row,
                  attachments: [],
                }))
              : [createRow()],
        })
        setMessage({ type: 'success', text: `Файл ${file.name} загружен` })
      } catch {
        setMessage({ type: 'error', text: 'Поддерживается только JSON-черновик этой страницы' })
      } finally {
        event.target.value = ''
      }
    }
    reader.readAsText(file)
  }

  function readAttachmentFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => {
        const result = String(reader.result || '')
        const commaIndex = result.indexOf(',')
        if (commaIndex === -1) {
          reject(new Error('Не удалось прочитать вложение'))
          return
        }

        const metadataPart = result.slice(0, commaIndex)
        const base64 = result.slice(commaIndex + 1)
        const contentTypeMatch = metadataPart.match(/^data:(.*?);base64$/)

        resolve({
          id: crypto.randomUUID(),
          fileName: file.name,
          contentType: contentTypeMatch?.[1] || file.type || 'application/octet-stream',
          base64,
          fileSize: file.size,
        })
      }
      reader.onerror = () => reject(new Error('Не удалось прочитать вложение'))
      reader.readAsDataURL(file)
    })
  }

  async function handleAttachmentPick(rowId, event) {
    const files = [...(event.target.files || [])]
    event.target.value = ''

    if (files.length === 0) {
      return
    }

    const oversizedFile = files.find((file) => file.size > 10 * 1024 * 1024)
    if (oversizedFile) {
      setMessage({ type: 'error', text: `Файл ${oversizedFile.name} не должен превышать 10 МБ` })
      return
    }

    try {
      const attachments = await Promise.all(files.map((file) => readAttachmentFile(file)))
      setFormState((current) => ({
        ...current,
        rows: current.rows.map((row) =>
          row.id === rowId
            ? {
                ...row,
                attachments: [...row.attachments, ...attachments],
              }
            : row,
        ),
      }))
      setMessage({
        type: 'success',
        text:
          attachments.length === 1
            ? `Файл ${attachments[0].fileName} прикреплён`
            : `Прикреплено файлов: ${attachments.length}`,
      })
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Не удалось прочитать вложение' })
    }
  }

  function handleAttachmentPreview(attachment) {
    if (!attachment?.base64 || !attachment?.contentType) {
      setMessage({ type: 'error', text: 'Не удалось открыть вложение' })
      return
    }

    const previewUrl = `data:${attachment.contentType};base64,${attachment.base64}`
    window.open(previewUrl, '_blank', 'noopener,noreferrer')
  }

  function removeAttachment(rowId, attachmentId) {
    setFormState((current) => ({
      ...current,
      rows: current.rows.map((row) =>
        row.id === rowId
          ? {
              ...row,
              attachments: row.attachments.filter((attachment) => attachment.id !== attachmentId),
            }
          : row,
      ),
    }))
  }

  return (
    <div className="add-payments-page">
      <div className="add-payments-shell">
        <div className="add-payments-card">
          <div className="add-payments-header">
            <button type="button" className="add-payments-back" onClick={() => navigate('/payments')}>
              <ArrowLeft size={18} />
            </button>
            <h1>Добавление платежей</h1>
          </div>

          <div className="add-payments-toolbar">
            <div className="add-payments-topline">
              <label className="add-payments-field add-payments-field--date">
                <span>Дата:</span>
                <div className="add-payments-input-wrap">
                  <input
                    type="date"
                    value={formState.bookingDate}
                    onChange={(event) => updateFormField('bookingDate', event.target.value)}
                  />
                  <CalendarDays size={16} />
                </div>
              </label>

              <div className="add-payments-field add-payments-field--lookup">
                <span>Счёт компании:</span>
                <LookupField
                  placeholder="Выберите существующий счёт"
                  textValue={formState.bankAccountText}
                  selectedOption={formState.bankAccount}
                  onTextChange={(value) =>
                    setFormState((current) => ({
                      ...current,
                      bankAccountText: value,
                      bankAccount:
                        current.bankAccount && value !== current.bankAccount.label ? null : current.bankAccount,
                    }))
                  }
                  onSelect={(option) =>
                    setFormState((current) => ({
                      ...current,
                      bankAccount: option,
                      bankAccountText: option?.label ?? '',
                    }))
                  }
                  fetchOptions={(query) => loadLookup('companyBankAccounts', query)}
                  helperText={
                    formState.bankAccount
                      ? `${formState.bankAccount.companyName} / ${formState.bankAccount.bankName} / ${formState.bankAccount.currencyCode}`
                      : 'Без выбора счёта пакет не сохранится'
                  }
                />
              </div>
            </div>

            <div className="add-payments-actions">
              <button type="button" className="add-payments-action" onClick={() => addRow()}>
                <Plus size={16} />
                Добавить
              </button>
              <button type="button" className="add-payments-action" onClick={handleLoadDraft}>
                <Upload size={16} />
                Загрузить
              </button>
              <button type="button" className="add-payments-action" onClick={() => fileInputRef.current?.click()}>
                <Upload size={16} />
                Импорт JSON
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/json"
                hidden
                onChange={handleFilePick}
              />
            </div>

            <datalist id="clients-options">
              {optionsState.clients.map((option) => (
                <option key={option.value} value={option.label} />
              ))}
            </datalist>
          </div>

          {message.text ? (
            <div className={`add-payments-message ${message.type === 'error' ? 'is-error' : 'is-success'}`}>
              {message.text}
            </div>
          ) : null}
          {optionsState.error ? <div className="add-payments-message is-error">{optionsState.error}</div> : null}

          <div className="add-payments-table-wrap">
            <table className="add-payments-table">
              <thead>
                <tr>
                  <th />
                  <th>Контрагент</th>
                  <th>Сумма</th>
                  <th>Налог</th>
                  <th>Доходы/Расходы</th>
                  <th>Клиент</th>
                  <th>Комментарий</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {formState.rows.map((row) => {
                  const amount = toNumber(row.amount)
                  const tax = Math.abs(toNumber(row.tax))
                  const amountWithoutTax = Math.abs(amount) - tax
                  const settlementEffect = amountWithoutTax + toNumber(row.incomeExpense)

                  return (
                    <Fragment key={row.id}>
                      <tr>
                        <td className="add-payments-table__move">
                          <GripVertical size={14} />
                        </td>
                        <td className="add-payments-table__counterparty">
                          <div className="add-payments-table__counterparty-inner">
                            <button
                              type="button"
                              className="add-payments-expand"
                              onClick={() => toggleExpanded(row.id)}
                              aria-label={row.expanded ? 'Свернуть строку' : 'Развернуть строку'}
                            >
                              {row.expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            </button>
                            <input
                              type="text"
                              value={row.counterpartyName}
                              onChange={(event) => updateRow(row.id, { counterpartyName: event.target.value })}
                              placeholder="Название контрагента"
                            />
                          </div>
                        </td>
                        <td>
                          <input
                            type="number"
                            step="0.01"
                            value={row.amount}
                            onChange={(event) => updateRow(row.id, { amount: event.target.value })}
                            placeholder="0.00"
                            className={amount > 0 ? 'is-positive' : ''}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            step="0.01"
                            value={row.tax}
                            onChange={(event) => updateRow(row.id, { tax: event.target.value })}
                            placeholder="-"
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            step="0.01"
                            value={row.incomeExpense}
                            onChange={(event) => updateRow(row.id, { incomeExpense: event.target.value })}
                            placeholder="-"
                            className={toNumber(row.incomeExpense) > 0 ? 'is-positive' : ''}
                          />
                        </td>
                        <td>
                          <input
                            list="clients-options"
                            type="text"
                            value={row.clientText}
                            onChange={(event) => updateRow(row.id, { clientText: event.target.value })}
                            placeholder="-"
                          />
                        </td>
                        <td>
                          <div className="add-payments-table__comment-cell">
                            <input
                              type="text"
                              value={row.comment}
                              onChange={(event) => updateRow(row.id, { comment: event.target.value })}
                              placeholder="-"
                            />
                            {row.attachments.length > 0 ? (
                              <div className="add-payments-attachments-list">
                                {row.attachments.map((attachment) => (
                                  <div key={attachment.id} className="add-payments-attachment-item">
                                    <button
                                      type="button"
                                      className="add-payments-attachment-link"
                                      onClick={() => handleAttachmentPreview(attachment)}
                                      title={attachment.fileName}
                                    >
                                      <Eye size={14} />
                                      {attachment.fileName}
                                    </button>
                                    <button
                                      type="button"
                                      className="add-payments-attachment-remove"
                                      onClick={() => removeAttachment(row.id, attachment.id)}
                                      aria-label="Удалить вложение"
                                    >
                                      <X size={12} />
                                    </button>
                                  </div>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        </td>
                        <td className="add-payments-table__actions">
                          <div className="add-payments-table__actions-inner">
                            <label className="add-payments-table__icon-button" aria-label="Прикрепить файл">
                              <Paperclip size={14} />
                              <input
                                type="file"
                                hidden
                                multiple
                                accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.xml,.txt"
                                onChange={(event) => handleAttachmentPick(row.id, event)}
                              />
                            </label>
                            <button type="button" onClick={() => removeRow(row.id)} aria-label="Удалить строку">
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                      {row.expanded ? (
                        <tr className="add-payments-breakdown-row">
                          <td />
                          <td colSpan={7}>
                            <div className="add-payments-breakdown">
                              <div>
                                <span>Сумма без налога:</span>
                                <strong>{formatAmount(amountWithoutTax)}</strong>
                              </div>
                              <div>
                                <span>Налог:</span>
                                <strong>{formatAmount(tax)}</strong>
                              </div>
                              <div>
                                <span>Сумма с налогом:</span>
                                <strong>{formatAmount(Math.abs(amount))}</strong>
                              </div>
                              <div>
                                <span>В ваш зачёт:</span>
                                <strong>{formatAmount(toNumber(row.incomeExpense))}</strong>
                              </div>
                              <div>
                                <span>В зачёт клиента:</span>
                                <strong>{formatAmount(settlementEffect)}</strong>
                              </div>
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="add-payments-bottom">
            <div className="add-payments-balance">
              <div>
                <span>Остаток счёта:</span>
                <strong>не рассчитывается на этой форме</strong>
              </div>
              <div>
                <span>Почему:</span>
                <strong>нужны данные банка и уже проведённые движения</strong>
              </div>
            </div>
            <div className="add-payments-balance">
              <div>
                <span>Поступления:</span>
                <strong>{formatAmount(totals.incoming)}</strong>
              </div>
              <div>
                <span>Списания:</span>
                <strong>{formatAmount(totals.outgoing)}</strong>
              </div>
            </div>
          </div>
        </div>

        <div className="add-payments-footer">
          <div className="add-payments-footer__group">
            <button type="button" className="add-payments-footer__button is-danger" onClick={handleReset}>
              Сбросить
            </button>
            <button type="button" className="add-payments-footer__button" onClick={handleClearRows}>
              Очистить
            </button>
          </div>
          <div className="add-payments-footer__group">
            <button type="button" className="add-payments-footer__button" onClick={handleSaveDraft}>
              <Save size={16} />
              Сохранить черновик
            </button>
            <button type="button" className="add-payments-footer__button is-primary" onClick={handleSave} disabled={isSaving}>
              <Save size={16} />
              {isSaving ? 'Сохраняю...' : 'Сохранить'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
