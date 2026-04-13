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
import { deleteClient, fetchClientsOverview } from '../../lib/api'
import './ClientsPage.css'

function EmptyState({ search }) {
  return (
    <div className="clients-table__empty">
      {search ? 'По текущему поиску клиенты не найдены.' : 'Клиенты пока не добавлены.'}
    </div>
  )
}

function formatDate(value) {
  if (!value) {
    return '-'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('ru-RU').format(date)
}

function buildContactLabel(client) {
  const parts = [client.email, client.phone].filter(Boolean)
  return parts.length > 0 ? parts.join(' / ') : '-'
}

export default function ClientsPage() {
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

    async function loadClients() {
      setState((current) => ({ ...current, isLoading: true, error: '' }))

      try {
        const items = await fetchClientsOverview({
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
            error: error.response?.data?.detail || 'Не удалось загрузить клиентов',
            items: [],
          })
        }
      }
    }

    loadClients()

    return () => {
      cancelled = true
    }
  }, [deferredSearch, refreshKey])

  const activeClientsCount = useMemo(
    () => state.items.filter((item) => (item.status || '').toLowerCase() === 'active').length,
    [state.items],
  )

  async function handleCopyClient(client) {
    const text = [
      `ФИО: ${client.full_name}`,
      `Личный код: ${client.personal_id_number || '-'}`,
      `Дата рождения: ${formatDate(client.date_of_birth)}`,
      `Страна / налоговое резидентство: ${client.country_code || '-'} / ${client.tax_residency_country_code || '-'}`,
      `Контакты: ${buildContactLabel(client)}`,
      `Город: ${client.city || '-'}`,
      `Статус: ${client.status || '-'}`,
    ].join('\n')

    try {
      await navigator.clipboard.writeText(text)
      setActionState({
        success: 'Данные клиента скопированы',
        error: '',
      })
    } catch {
      setActionState({
        success: '',
        error: 'Не удалось скопировать данные клиента',
      })
    }
  }

  function handleEditClient(clientId) {
    navigate(`/clients/${clientId}/edit`)
  }

  async function handleDeleteClient(client) {
    const isConfirmed = window.confirm(`Удалить клиента "${client.full_name}"?`)
    if (!isConfirmed) {
      return
    }

    try {
      await deleteClient(client.id)
      setActionState({
        success: 'Клиент удалён',
        error: '',
      })
      setRefreshKey((current) => current + 1)
    } catch (error) {
      setActionState({
        success: '',
        error: error.response?.data?.detail || 'Не удалось удалить клиента',
      })
    }
  }

  return (
    <div className="clients-page">
      <div className="clients-shell">
        <div className="clients-heading">
          <button type="button" className="clients-back" aria-label="Назад" onClick={() => navigate(-1)}>
            <ArrowLeft size={18} />
          </button>
          <h1>Клиенты</h1>
        </div>

        <section className="clients-card">
          <div className="clients-toolbar">
            <button type="button" className="clients-action" onClick={() => navigate('/clients/new')}>
              <Plus size={16} />
              Добавить клиента
            </button>

            <label className="clients-search">
              <Search size={16} />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Поиск по ФИО, email, телефону, ID..."
              />
            </label>

            <button
              type="button"
              className="clients-icon-button"
              onClick={() => setRefreshKey((current) => current + 1)}
              aria-label="Обновить список"
            >
              <RefreshCw size={16} />
            </button>
            <button type="button" className="clients-icon-button" aria-label="Фильтры">
              <Filter size={16} />
            </button>
            <button type="button" className="clients-icon-button" aria-label="Параметры таблицы">
              <SlidersHorizontal size={16} />
            </button>
          </div>

          <div className="clients-status">
            <div>
              Найдено <strong>{state.items.length}</strong> клиентов
            </div>
            <div>
              Активных: <strong>{activeClientsCount}</strong>
            </div>
            <div>{actionState.success ? <span className="clients-status__success">{actionState.success}</span> : null}</div>
            <div>{actionState.error ? <span className="clients-status__error">{actionState.error}</span> : null}</div>
            <div>{state.error ? <span className="clients-status__error">{state.error}</span> : null}</div>
          </div>

          <div className="clients-table-wrap">
            {state.isLoading ? (
              <div className="clients-table__empty">Загружаю клиентов...</div>
            ) : state.items.length === 0 ? (
              <EmptyState search={Boolean(search)} />
            ) : (
              <table className="clients-table">
                <thead>
                  <tr>
                    <th />
                    <th>ФИО</th>
                    <th>Личный код</th>
                    <th>Дата рождения</th>
                    <th>Страна / налог</th>
                    <th>Контакты</th>
                    <th>Город</th>
                    <th>Статус</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {state.items.map((client) => (
                    <tr key={client.id}>
                      <td className="clients-table__checkbox">
                        <input type="checkbox" />
                      </td>
                      <td className="clients-table__name">{client.full_name}</td>
                      <td>{client.personal_id_number || '-'}</td>
                      <td>{formatDate(client.date_of_birth)}</td>
                      <td>
                        {[client.country_code || '-', client.tax_residency_country_code || '-'].join(' / ')}
                      </td>
                      <td>{buildContactLabel(client)}</td>
                      <td>{client.city || '-'}</td>
                      <td>
                        <span className={`clients-status-chip ${client.status ? 'is-filled' : ''}`}>
                          {client.status || '-'}
                        </span>
                      </td>
                      <td className="clients-table__actions">
                        <button type="button" aria-label="Копировать" onClick={() => handleCopyClient(client)}>
                          <Copy size={14} />
                        </button>
                        <button type="button" aria-label="Редактировать" onClick={() => handleEditClient(client.id)}>
                          <Pencil size={14} />
                        </button>
                        <button type="button" aria-label="Удалить" onClick={() => handleDeleteClient(client)}>
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

        <div className="clients-footer">
          <button type="button" className="clients-export">
            Скачать Excel
            <span className="clients-export__badge">XLS</span>
          </button>
          <button type="button" className="clients-export">
            Скачать PDF
            <span className="clients-export__badge">PDF</span>
          </button>
        </div>
      </div>
    </div>
  )
}
