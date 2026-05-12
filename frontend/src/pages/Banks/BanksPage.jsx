import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import {
  ArrowLeft,
  Copy,
  Filter,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { fetchBankAccountsOverview, fetchBanksOverview } from '../../lib/api'
import './BanksPage.css'

function groupItems(items, mode) {
  const map = new Map()

  for (const item of items) {
    const key = mode === 'banks' ? item.bank_id : item.company_id
    const label = mode === 'banks' ? item.bank_label : item.company_name || 'Не привязано'
    if (!map.has(key)) {
      map.set(key, { key, label, items: [] })
    }
    map.get(key).items.push(item)
  }

  return [...map.values()]
}

function formatBalanceLabel(item) {
  if (!item.currency_code) {
    return '—'
  }
  return `— ${item.currency_code}`
}

function buildRows(accountItems, bankItems) {
  const linkedBankIds = new Set(accountItems.map((item) => item.bank_id))

  const accountRows = accountItems.map((item) => ({
    ...item,
    row_key: `account-${item.id}`,
    account_id: item.id,
    row_type: 'account',
  }))

  const bankOnlyRows = bankItems
    .filter((bank) => !linkedBankIds.has(bank.id))
    .map((bank) => ({
      row_key: `bank-${bank.id}`,
      account_id: null,
      row_type: 'bank',
      id: bank.id,
      company_id: null,
      company_name: null,
      bank_id: bank.id,
      bank_label: bank.label,
      bank_full_name: bank.name,
      iban: null,
      account_number: null,
      swift_or_bic: bank.swift_code,
      bank_address: bank.bank_address,
      currency_code: null,
      is_primary: false,
      is_active: true,
      opened_at: null,
      closed_at: null,
    }))

  return [...accountRows, ...bankOnlyRows]
}

export default function BanksPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [groupMode, setGroupMode] = useState('banks')
  const [refreshKey, setRefreshKey] = useState(0)
  const [state, setState] = useState({
    isLoading: true,
    error: '',
    accountItems: [],
    bankItems: [],
  })

  const deferredSearch = useDeferredValue(search)

  useEffect(() => {
    let cancelled = false

    async function loadAccounts() {
      setState((current) => ({ ...current, isLoading: true, error: '' }))

      try {
        const [accountItems, bankItems] = await Promise.all([
          fetchBankAccountsOverview({
            query: deferredSearch || undefined,
            limit: 300,
          }),
          fetchBanksOverview({
            query: deferredSearch || undefined,
            limit: 300,
          }),
        ])

        if (!cancelled) {
          setState({
            isLoading: false,
            error: '',
            accountItems,
            bankItems,
          })
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            isLoading: false,
            error: error.response?.data?.detail || 'Не удалось загрузить банковские счета',
            accountItems: [],
            bankItems: [],
          })
        }
      }
    }

    loadAccounts()

    return () => {
      cancelled = true
    }
  }, [deferredSearch, refreshKey])

  const rows = useMemo(
    () => buildRows(state.accountItems, state.bankItems),
    [state.accountItems, state.bankItems],
  )
  const groups = useMemo(() => groupItems(rows, groupMode), [groupMode, rows])

  return (
    <div className="banks-page">
      <div className="banks-shell">
        <div className="banks-heading">
          <button type="button" className="banks-back" aria-label="Назад">
            <ArrowLeft size={18} />
          </button>
          <h1>Банки</h1>
        </div>

        <section className="banks-card">
          <div className="banks-toolbar">
            <button type="button" className="banks-action" onClick={() => navigate('/banks/new-bank')}>
              <Plus size={16} />
              Добавить банк
            </button>
            <button type="button" className="banks-action" onClick={() => navigate('/banks/new')}>
              <Plus size={16} />
              Добавить счёт
            </button>

            <label className="banks-search">
              <Search size={16} />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Поиск..."
              />
            </label>

            <button
              type="button"
              className="banks-icon-button"
              onClick={() => setRefreshKey((current) => current + 1)}
              aria-label="Обновить список"
            >
              <RefreshCw size={16} />
            </button>
            <button type="button" className="banks-icon-button" aria-label="Фильтры">
              <Filter size={16} />
            </button>

            <div className="banks-switches">
              <label className="banks-radio">
                <span>По компаниям</span>
                <input
                  type="radio"
                  name="group_mode"
                  checked={groupMode === 'companies'}
                  onChange={() => setGroupMode('companies')}
                />
              </label>
              <label className="banks-radio">
                <span>По банкам</span>
                <input
                  type="radio"
                  name="group_mode"
                  checked={groupMode === 'banks'}
                  onChange={() => setGroupMode('banks')}
                />
              </label>
            </div>
          </div>

          <div className="banks-table-wrap">
            {state.isLoading ? (
              <div className="banks-table__empty">Загружаю банковские счета...</div>
            ) : groups.length === 0 ? (
              <div className="banks-table__empty">
                {search ? 'По текущему поиску банки и счета не найдены.' : 'Банки и банковские счета пока не добавлены.'}
              </div>
            ) : (
              <table className="banks-table">
                <thead>
                  <tr>
                    <th />
                    <th>Банк</th>
                    <th>Наименование фирмы</th>
                    <th>Остаток</th>
                    <th>IBAN</th>
                    <th>SWIFT/BIC</th>
                    <th>Полное название банка</th>
                    <th>Адрес банка</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {groups.map((group) =>
                    group.items.map((item, index) => (
                      <tr key={item.row_key}>
                        <td className="banks-table__checkbox">
                          <input type="checkbox" />
                        </td>
                        <td className="banks-table__bank">
                          {index === 0 ? group.label : ''}
                        </td>
                        <td className="banks-table__company">{item.company_name || 'Не привязано'}</td>
                        <td>{formatBalanceLabel(item)}</td>
                        <td>{item.iban || item.account_number || '-'}</td>
                        <td>{item.swift_or_bic || '-'}</td>
                        <td>{item.bank_full_name}</td>
                        <td>{item.bank_address || '-'}</td>
                        <td className="banks-table__actions">
                          <button type="button" aria-label="Копировать">
                            <Copy size={14} />
                          </button>
                          <button
                            type="button"
                            aria-label={item.account_id ? 'Редактировать счёт' : 'Создать счёт для банка'}
                            title={item.account_id ? 'Редактировать счёт' : 'Создать счёт и привязать компанию'}
                            onClick={() => {
                              if (item.account_id) {
                                navigate(`/banks/${item.account_id}/edit`)
                                return
                              }

                              const params = new URLSearchParams({ bankId: String(item.bank_id) })
                              navigate(`/banks/new?${params.toString()}`)
                            }}
                          >
                            <Pencil size={14} />
                          </button>
                          <button type="button" aria-label="Удалить">
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    )),
                  )}
                </tbody>
              </table>
            )}
          </div>
          {state.error ? <div className="banks-status__error">{state.error}</div> : null}
        </section>

        <div className="banks-footer">
          <button type="button" className="banks-export">
            Скачать Excel
            <span className="banks-export__badge">XLS</span>
          </button>
          <button type="button" className="banks-export">
            Скачать PDF
            <span className="banks-export__badge">PDF</span>
          </button>
        </div>
      </div>
    </div>
  )
}
