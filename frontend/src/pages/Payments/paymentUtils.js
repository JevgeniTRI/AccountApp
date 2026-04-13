import { fetchCompanyBankAccountsLookup, fetchLookup } from '../../lib/api'

export const LOOKUP_CONFIG = {
  companies: {
    path: '/companies',
  },
  banks: {
    path: '/banks',
  },
  clients: {
    path: '/clients',
  },
  counterparties: {
    path: '/counterparties',
  },
  currencies: {
    path: '/currencies',
  },
  companyBankAccounts: {
    fetcher: fetchCompanyBankAccountsLookup,
  },
}

export function toDateInputValue(date) {
  return date.toISOString().slice(0, 10)
}

export function getMonthStart() {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), 1)
}

export function formatDate(value) {
  if (!value) {
    return '-'
  }

  return new Intl.DateTimeFormat('ru-RU').format(new Date(value))
}

export function toNumber(value) {
  if (value === null || value === undefined || value === '') {
    return 0
  }

  return Number(value)
}

export function formatAmount(value, currency = 'EUR') {
  const amount = toNumber(value)
  return (
    new Intl.NumberFormat('ru-RU', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount) + ` ${currency}`
  )
}

export function normalizeLookupItems(items, type) {
  if (type === 'currencies') {
    return items.map((item) => ({
      value: item.code,
      label: item.label,
      rawLabel: item.code,
    }))
  }

  return items.map((item) => ({
    value: item.id,
    label: item.label,
    companyId: item.company_id,
    companyName: item.company_name,
    bankId: item.bank_id,
    bankName: item.bank_name,
    currencyCode: item.currency_code,
  }))
}

export async function loadLookup(type, query) {
  const config = LOOKUP_CONFIG[type]
  const items = config.fetcher
    ? await config.fetcher(query)
    : await fetchLookup(config.path, query)
  return normalizeLookupItems(items, type)
}

export function requireLookupValue(type, selectedOption, textValue, options, errorMessage) {
  const matchedOption = selectedOption || findLookupOption(type, textValue, options)
  if (!matchedOption) {
    throw new Error(errorMessage)
  }
  return matchedOption
}

export function findLookupOption(type, textValue, options) {
  const normalized = textValue.trim().toLowerCase()
  if (!normalized) {
    return null
  }

  return (
    options.find((option) => {
      if (type === 'currencies') {
        return (
          option.rawLabel?.toLowerCase() === normalized ||
          option.label.toLowerCase() === normalized
        )
      }

      return option.label.toLowerCase() === normalized
    }) || null
  )
}
