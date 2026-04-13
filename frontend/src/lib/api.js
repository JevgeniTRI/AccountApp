import axios from 'axios'

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()

export const api = axios.create({
  baseURL: rawBaseUrl ? rawBaseUrl.replace(/\/+$/, '') : 'http://127.0.0.1:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function fetchLookup(path, query = '', limit = 20) {
  const { data } = await api.get(path, {
    params: {
      query: query || undefined,
      limit,
    },
  })
  return data
}

export async function fetchPayments(params) {
  const { data } = await api.get('/payments', { params })
  return data
}

export async function createPayment(payload) {
  const { data } = await api.post('/payments', payload)
  return data
}

export async function createPaymentsBatch(items) {
  const { data } = await api.post('/payments/batch', { items })
  return data
}

export function buildPaymentAttachmentUrl(attachmentId) {
  return `${api.defaults.baseURL}/payments/attachments/${attachmentId}/content`
}

export async function fetchCompaniesOverview(params) {
  const { data } = await api.get('/companies/overview', { params })
  return data
}

export async function createCompany(payload) {
  const { data } = await api.post('/companies', payload)
  return data
}

export async function fetchCompany(companyId) {
  const { data } = await api.get(`/companies/${companyId}`)
  return data
}

export async function updateCompany(companyId, payload) {
  const { data } = await api.put(`/companies/${companyId}`, payload)
  return data
}

export async function deleteCompany(companyId) {
  await api.delete(`/companies/${companyId}`)
}

export async function fetchBankAccountsOverview(params) {
  const { data } = await api.get('/bank-accounts/overview', { params })
  return data
}

export async function fetchCompanyBankAccountsLookup(query = '', limit = 20) {
  const { data } = await api.get('/company-bank-accounts', {
    params: {
      query: query || undefined,
      limit,
    },
  })
  return data
}

export async function createBankAccount(payload) {
  const { data } = await api.post('/bank-accounts', payload)
  return data
}

export async function fetchClientsOverview(params) {
  const { data } = await api.get('/clients/overview', { params })
  return data
}

export async function createClient(payload) {
  const { data } = await api.post('/clients', payload)
  return data
}

export async function fetchClient(clientId) {
  const { data } = await api.get(`/clients/${clientId}`)
  return data
}

export async function updateClient(clientId, payload) {
  const { data } = await api.put(`/clients/${clientId}`, payload)
  return data
}

export async function deleteClient(clientId) {
  await api.delete(`/clients/${clientId}`)
}

export async function fetchCounterpartiesOverview(params) {
  const { data } = await api.get('/counterparties/overview', { params })
  return data
}

export async function createCounterparty(payload) {
  const { data } = await api.post('/counterparties', payload)
  return data
}

export async function fetchCounterparty(counterpartyId) {
  const { data } = await api.get(`/counterparties/${counterpartyId}`)
  return data
}

export async function updateCounterparty(counterpartyId, payload) {
  const { data } = await api.put(`/counterparties/${counterpartyId}`, payload)
  return data
}

export async function deleteCounterparty(counterpartyId) {
  await api.delete(`/counterparties/${counterpartyId}`)
}
