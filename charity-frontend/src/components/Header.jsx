import { Link, NavLink } from 'react-router-dom'
import { getCreateCollectionPath, useCurrentUser } from '../hooks/useCurrentUser'

const linkClass = ({ isActive }) =>
  `rounded-full px-4 py-2 text-sm font-medium transition ${
    isActive ? 'bg-teal-500 text-white' : 'text-slate-600 hover:bg-sky-100'
  }`

export default function Header() {
  const { user } = useCurrentUser()
  const createCollectionPath = getCreateCollectionPath(user)

  const navItems = [
    { to: '/', label: 'Главная', end: true },
    { to: '/catalog', label: 'Каталог' },
  ]
  if (!user) {
    navItems.push(
      { to: '/login', label: 'Вход' },
      { to: '/register', label: 'Регистрация' },
    )
  }
  if (user?.role === 'author') {
    navItems.push({ to: '/author', label: 'Мой кабинет' })
  }
  if (user?.role === 'donor') {
    navItems.push({ to: '/donor', label: 'Мой кабинет' })
  }
  if (user?.role === 'moderator') {
    navItems.push({ to: '/moderator', label: 'Модератор' })
  }
  if (user?.role === 'admin') {
    navItems.push({ to: '/admin', label: 'Админ' })
  }

  return (
    <header className="border-b border-sky-100 bg-white/90 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 py-4">
        <div className="flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500 to-sky-400 text-lg font-bold text-white shadow-md">
              C
            </div>
            <div>
              <p className="text-lg font-semibold text-slate-800">Charity Platform</p>
              <p className="text-xs text-slate-500">Проверенная помощь</p>
            </div>
          </Link>
          <div className="flex gap-2">
            <Link
              to="/catalog"
              className="rounded-full bg-teal-500 px-4 py-2 text-sm font-semibold text-white shadow-md transition hover:bg-teal-600 sm:px-5 sm:py-3"
            >
              Помочь сейчас
            </Link>
            <Link
              to={createCollectionPath}
              className="hidden rounded-full border border-teal-500 px-5 py-3 text-sm font-semibold text-teal-600 transition hover:bg-mint-100 sm:inline-block"
            >
              Создать сбор
            </Link>
          </div>
        </div>
        <nav className="mt-3 flex flex-wrap gap-2">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
