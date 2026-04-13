import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import {
  ArrowLeft,
  Copy,
  Filter,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { deleteCompany, fetchCompaniesOverview } from '../../lib/api'
import './CompaniesPage.css'

function EmptyState({ search }) {
  return (
    <div className="companies-table__empty">
      {search ? 'По текущему поиску компании не найдены.' : 'Компании пока не добавлены.'}
    </div>
  )
}

export default function CompaniesPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [actionState, setActionState] = useState({
    success: '',
    error: '',
  })
  const [state, setState] = useState({
    isLoading: true,
    error: '',
    items: [],
  })

  const deferredSearch = useDeferredValue(search)

  useEffect(() => {
    let cancelled = false

    async function loadCompanies() {
      setState((current) => ({ ...current, isLoading: true, error: '' }))

      try {
        const items = await fetchCompaniesOverview({
          query: deferredSearch || undefined,
          limit: 200,
        })

        if (!cancelled) {
          setState({
            isLoading: false,
            error: '',
            items,
          })
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            isLoading: false,
            error: error.response?.data?.detail || 'Не удалось загрузить компании',
            items: [],
          })
        }
      }
    }

    loadCompanies()

    return () => {
      cancelled = true
    }
  }, [deferredSearch, refreshKey])

  const totalBankLinks = useMemo(
    () => state.items.reduce((total, item) => total + item.bank_names.length, 0),
    [state.items],
  )

  async function handleCopyCompany(company) {
    const text = [
      `Наименование: ${company.legal_name}`,
      `Короткое наименование: ${company.short_name || '-'}`,
      `Банковские счета: ${company.bank_names.length > 0 ? company.bank_names.join(', ') : '-'}`,
      `Директор: ${company.director_name || '-'}`,
    ].join('\n')

    try {
      await navigator.clipboard.writeText(text)
      setActionState({
        success: 'Данные строки скопированы',
        error: '',
      })
    } catch {
      setActionState({
        success: '',
        error: 'Не удалось скопировать данные строки',
      })
    }
  }

  function handleEditCompany(companyId) {
    navigate(`/companies/${companyId}/edit`)
  }

  async function handleDeleteCompany(company) {
    const isConfirmed = window.confirm(`Удалить компанию "${company.legal_name}"?`)
    if (!isConfirmed) {
      return
    }

    try {
      await deleteCompany(company.id)
      setActionState({
        success: 'Компания удалена',
        error: '',
      })
      setRefreshKey((current) => current + 1)
    } catch (error) {
      setActionState({
        success: '',
        error: error.response?.data?.detail || 'Не удалось удалить компанию',
      })
    }
  }

  return (
    <div className="companies-page">
      <div className="companies-shell">
        <div className="companies-heading">
          <button type="button" className="companies-back" aria-label="Назад" onClick={() => navigate(-1)}>
            <ArrowLeft size={18} />
          </button>
          <h1>Компании</h1>
        </div>

        <section className="companies-card">
          <div className="companies-toolbar">
            <button type="button" className="companies-action" onClick={() => navigate('/companies/new')}>
              <Plus size={16} />
              Добавить компанию
            </button>

            <label className="companies-search">
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
              className="companies-icon-button"
              onClick={() => setRefreshKey((current) => current + 1)}
              aria-label="Обновить список"
            >
              <RefreshCw size={16} />
            </button>
            <button type="button" className="companies-icon-button" aria-label="Фильтры">
              <Filter size={16} />
            </button>
            <button type="button" className="companies-icon-button" aria-label="Параметры таблицы">
              <SlidersHorizontal size={16} />
            </button>
          </div>

          <div className="companies-status">
            <div>
              Найдено <strong>{state.items.length}</strong> компаний
            </div>
            <div>
              Банковских связей: <strong>{totalBankLinks}</strong>
            </div>
            <div>{actionState.success ? <span className="companies-status__success">{actionState.success}</span> : null}</div>
            <div>{actionState.error ? <span className="companies-status__error">{actionState.error}</span> : null}</div>
            <div>{state.error ? <span className="companies-status__error">{state.error}</span> : null}</div>
          </div>

          <div className="companies-table-wrap">
            {state.isLoading ? (
              <div className="companies-table__empty">Загружаю компании...</div>
            ) : state.items.length === 0 ? (
              <EmptyState search={Boolean(search)} />
            ) : (
              <table className="companies-table">
                <thead>
                  <tr>
                    <th />
                    <th>Наименование</th>
                    <th>Короткое наименование</th>
                    <th>Банковские счета</th>
                    <th>Директор</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {state.items.map((company) => (
                    <tr key={company.id}>
                      <td className="companies-table__checkbox">
                        <input type="checkbox" />
                      </td>
                      <td className="companies-table__name">{company.legal_name}</td>
                      <td>{company.short_name || '-'}</td>
                      <td>
                        {company.bank_names.length > 0 ? (
                          <div className="companies-table__banks">
                            {company.bank_names.map((bankName) => (
                              <span key={`${company.id}-${bankName}`} className="companies-table__bank-chip">
                                {bankName}
                              </span>
                            ))}
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td>{company.director_name || '-'}</td>
                      <td className="companies-table__actions">
                        <button type="button" aria-label="Копировать" onClick={() => handleCopyCompany(company)}>
                          <Copy size={14} />
                        </button>
                        <button type="button" aria-label="Редактировать" onClick={() => handleEditCompany(company.id)}>
                          <Pencil size={14} />
                        </button>
                        <button type="button" aria-label="Удалить" onClick={() => handleDeleteCompany(company)}>
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        <div className="companies-footer">
          <button type="button" className="companies-export">
            Скачать Excel
            <span className="companies-export__badge">XLS</span>
          </button>
          <button type="button" className="companies-export">
            Скачать PDF
            <span className="companies-export__badge">PDF</span>
          </button>
        </div>
      </div>
    </div>
  )
}
