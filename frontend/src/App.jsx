import { Navigate, Route, Routes } from 'react-router-dom'
import BankAccountCreatePage from './pages/Banks/BankAccountCreatePage'
import BanksPage from './pages/Banks/BanksPage'
import ClientCreatePage from './pages/Clients/ClientCreatePage'
import ClientsPage from './pages/Clients/ClientsPage'
import CounterpartiesPage from './pages/Counterparties/CounterpartiesPage'
import CounterpartyCreatePage from './pages/Counterparties/CounterpartyCreatePage'
import Navbar from './components/Navbar/Navbar'
import CompanyCreatePage from './pages/Companies/CompanyCreatePage'
import CompaniesPage from './pages/Companies/CompaniesPage'
import AddPaymentsPage from './pages/Payments/AddPaymentsPage'
import PaymentsPage from './pages/Payments/PaymentsPage'

function PlaceholderPage({ title }) {
  return (
    <section className="placeholder-page">
      <div className="placeholder-page__card">
        <span className="placeholder-page__eyebrow">Раздел в работе</span>
        <h1>{title}</h1>
        <p>Dashboard будет прям вызовом, но как говорил Бурунов:'Но мы рискнем!'. Сейчас уже собраны разделы платежей, компаний, банков и клиентов.</p>
      </div>
    </section>
  )
}

function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<PlaceholderPage title="Главная" />} />
          <Route path="/payments" element={<PaymentsPage />} />
          <Route path="/payments/new" element={<AddPaymentsPage />} />
          <Route path="/companies" element={<CompaniesPage />} />
          <Route path="/companies/new" element={<CompanyCreatePage />} />
          <Route path="/companies/:companyId/edit" element={<CompanyCreatePage />} />
          <Route path="/banks" element={<BanksPage />} />
          <Route path="/banks/new" element={<BankAccountCreatePage />} />
          <Route path="/clients" element={<ClientsPage />} />
          <Route path="/clients/new" element={<ClientCreatePage />} />
          <Route path="/clients/:clientId/edit" element={<ClientCreatePage />} />
          <Route path="/counterparties" element={<CounterpartiesPage />} />
          <Route path="/counterparties/new" element={<CounterpartyCreatePage />} />
          <Route path="/counterparties/:counterpartyId/edit" element={<CounterpartyCreatePage />} />
          <Route path="*" element={<Navigate to="/payments" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
