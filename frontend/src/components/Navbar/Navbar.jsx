import { NavLink } from 'react-router-dom'
import { RefreshCcwDot, UserCircle2 } from 'lucide-react'
import './Navbar.css'

const navItems = [
  { path: '/', label: 'Главная' },
  { path: '/payments', label: 'Платежи' },
  { path: '/companies', label: 'Компании' },
  { path: '/banks', label: 'Банки' },
  { path: '/clients', label: 'Клиенты' },
  { path: '/counterparties', label: 'Контрагенты' },
]

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar__container">
        <div className="navbar__left">
          <NavLink to="/" className="navbar__logo" aria-label="На главную">
            <RefreshCcwDot size={28} strokeWidth={2.25} />
          </NavLink>

          <nav className="navbar__nav" aria-label="Основная навигация">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `navbar__link ${isActive ? 'is-active' : ''}`}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <button type="button" className="navbar__profile" aria-label="Профиль">
          <UserCircle2 size={28} strokeWidth={1.8} />
        </button>
      </div>
    </header>
  )
}
