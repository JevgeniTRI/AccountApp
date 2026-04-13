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
import { deleteCounterparty, fetchCounterpartiesOverview } from '../../lib/api'
import './CounterpartiesPage.css'

function EmptyState({ search }) {
  return (
    <div className="counterparties-table__empty">
      {search ? 'По текущему поиску контрагенты не найдены.' : 'Контрагенты пока не добавлены.'}
    </div>
  )
}

function buildContactLabel(item) {
  const parts = [item.email, item.phone].filter(Boolean)
  return parts.length > 0 ? parts.join(' / ') : '-'
}

export default function CounterpartiesPage() {
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

    async function loadCounterparties() {
      setState((current) => ({ ...current, isLoading: true, error: '' }))

      try {
        const items = await fetchCounterpartiesOverview({
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
            error: error.response?.data?.detail || 'Не удалось загрузить контрагентов',
            items: [],
          })
        }
      }
    }

    loadCounterparties()

    return () => {
      cancelled = true
    }
  }, [deferredSearch, refreshKey])

  const activeCounterpartiesCount = useMemo(
    () => state.items.filter((item) => (item.status || '').toLowerCase() === 'active').length,
    [state.items],
  )

  async function handleCopyCounterparty(item) {
    const text = [
      `Наименование: ${item.legal_name}`,
      `Короткое наименование: ${item.short_name || '-'}`,
      `Клиент: ${item.client_name}`,
      `Регистрационный номер: ${item.registration_number || '-'}`,
      `Страна: ${item.country_code || '-'}`,
      `Контакты: ${buildContactLabel(item)}`,
      `Город: ${item.city || '-'}`,
      `Сайт: ${item.website || '-'}`,
      `Статус: ${item.status || '-'}`,
    ].join('\n')

    try {
      await navigator.clipboard.writeText(text)
      setActionState({
        success: 'Данные контрагента скопированы',
        error: '',
      })
    } catch {
      setActionState({
        success: '',
        error: 'Не удалось скопировать данные контрагента',
      })
    }
  }

  async function handleDeleteCounterparty(item) {
    const isConfirmed = window.confirm(`Удалить контрагента "${item.legal_name}"?`)
    if (!isConfirmed) {
      return
    }

    try {
      await deleteCounterparty(item.id)
      setActionState({
        success: 'Контрагент удалён',
        error: '',
      })
      setRefreshKey((current) => current + 1)
    } catch (error) {
      setActionState({
        success: '',
        error: error.response?.data?.detail || 'Не удалось удалить контрагента',
      })
    }
  }

  return (
    <div className="counterparties-page">
      <div className="counterparties-shell">
        <div className="counterparties-heading">
          <button type="button" className="counterparties-back" aria-label="Назад" onClick={() => navigate(-1)}>
            <ArrowLeft size={18} />
          </button>
          <h1>Контрагенты</h1>
        </div>

        <section className="counterparties-card">
          <div className="counterparties-toolbar">
            <button type="button" className="counterparties-action" onClick={() => navigate('/counterparties/new')}>
              <Plus size={16} />
              Добавить контрагента
            </button>

            <label className="counterparties-search">
              <Search size={16} />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Поиск по названию, клиенту, email, номеру..."
              />
            </label>

            <button
              type="button"
              className="counterparties-icon-button"
              onClick={() => setRefreshKey((current) => current + 1)}
              aria-label="Обновить список"
            >
              <RefreshCw size={16} />
            </button>
            <button type="button" className="counterparties-icon-button" aria-label="Фильтры">
              <Filter size={16} />
            </button>
            <button type="button" className="counterparties-icon-button" aria-label="Параметры таблицы">
              <SlidersHorizontal size={16} />
            </button>
          </div>

          <div className="counterparties-status">
            <div>
              Найдено <strong>{state.items.length}</strong> контрагентов
            </div>
            <div>
              Активных: <strong>{activeCounterpartiesCount}</strong>
            </div>
            <div>
              {actionState.success ? <span className="counterparties-status__success">{actionState.success}</span> : null}
            </div>
            <div>
              {actionState.error ? <span className="counterparties-status__error">{actionState.error}</span> : null}
            </div>
            <div>{state.error ? <span className="counterparties-status__error">{state.error}</span> : null}</div>
          </div>

          <div className="counterparties-table-wrap">
            {state.isLoading ? (
              <div className="counterparties-table__empty">Загружаю контрагентов...</div>
            ) : state.items.length === 0 ? (
              <EmptyState search={Boolean(search)} />
            ) : (
              <table className="counterparties-table">
                <thead>
                  <tr>
                    <th />
                    <th>Наименование</th>
                    <th>Клиент</th>
                    <th>Рег. номер</th>
                    <th>Страна</th>
                    <th>Контакты</th>
                    <th>Город</th>
                    <th>Сайт</th>
                    <th>Статус</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {state.items.map((item) => (
                    <tr key={item.id}>
                      <td className="counterparties-table__checkbox">
                        <input type="checkbox" />
                      </td>
                      <td className="counterparties-table__name">
                        {item.legal_name}
                        {item.short_name ? <div className="counterparties-table__subname">{item.short_name}</div> : null}
                      </td>
                      <td>{item.client_name}</td>
                      <td>{item.registration_number || '-'}</td>
                      <td>{item.country_code || '-'}</td>
                      <td>{buildContactLabel(item)}</td>
                      <td>{item.city || '-'}</td>
                      <td>{item.website || '-'}</td>
                      <td>
                        <span className={`counterparties-status-chip ${item.status ? 'is-filled' : ''}`}>
                          {item.status || '-'}
                        </span>
                      </td>
                      <td className="counterparties-table__actions">
                        <button type="button" aria-label="Копировать" onClick={() => handleCopyCounterparty(item)}>
                          <Copy size={14} />
                        </button>
                        <button type="button" aria-label="Редактировать" onClick={() => navigate(`/counterparties/${item.id}/edit`)}>
                          <Pencil size={14} />
                        </button>
                        <button type="button" aria-label="Удалить" onClick={() => handleDeleteCounterparty(item)}>
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

        <div className="counterparties-footer">
          <button type="button" className="counterparties-export">
            Скачать Excel
            <span className="counterparties-export__badge">XLS</span>
          </button>
          <button type="button" className="counterparties-export">
            Скачать PDF
            <span className="counterparties-export__badge">PDF</span>
          </button>
        </div>
      </div>
    </div>
  )
}
