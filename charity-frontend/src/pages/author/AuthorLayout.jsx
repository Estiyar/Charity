import { Link, NavLink, Outlet } from 'react-router-dom'
import { clearToken } from '../../api/auth'

const tabs = [
  { to: '/author', label: 'Мои сборы', end: true },
  { to: '/author/donor', label: 'Мои пожертвования' },
]

const tabClass = ({ isActive }) =>
  `rounded-t-2xl px-5 py-3 text-sm font-semibold transition ${
    isActive
      ? 'bg-white text-teal-700 shadow-sm'
      : 'text-slate-600 hover:bg-white/60 hover:text-slate-800'
  }`

export default function AuthorLayout() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Личный кабинет автора</h1>
          <p className="text-slate-600">Мои сборы, расходы и пожертвования</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/author/create"
            className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
          >
            Создать сбор
          </Link>
          <Link
            to="/author/profile"
            className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600"
          >
            Профиль
          </Link>
          <button
            type="button"
            onClick={() => {
              clearToken()
              window.location.href = '/login'
            }}
            className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600"
          >
            Выйти
          </button>
        </div>
      </div>

      <nav className="flex flex-wrap gap-1 rounded-3xl bg-sky-100 p-2">
        {tabs.map((tab) => (
          <NavLink key={tab.to} to={tab.to} end={tab.end} className={tabClass}>
            {tab.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  )
}
