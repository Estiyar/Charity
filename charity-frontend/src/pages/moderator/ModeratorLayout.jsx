import { NavLink, Outlet } from 'react-router-dom'
import { clearToken } from '../../api/auth'

const sections = [
  { to: '/moderator', label: 'Новые заявки', status: 'pending_moderation', end: true },
  { to: '/moderator/revision', label: 'На доработке', status: 'revision_required' },
  { to: '/moderator/approved', label: 'Одобренные', status: 'approved' },
  { to: '/moderator/rejected', label: 'Отклонённые', status: 'rejected' },
  { to: '/moderator/documents', label: 'Документы на проверке' },
  { to: '/moderator/expenses', label: 'Расходы на проверке' },
  { to: '/moderator/redistribution', label: 'Перераспределение' },
]

export { sections }

const linkClass = ({ isActive }) =>
  `block rounded-2xl px-4 py-3 text-sm font-medium transition ${
    isActive ? 'bg-teal-500 text-white' : 'text-slate-600 hover:bg-sky-100'
  }`

export default function ModeratorLayout() {
  return (
    <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 lg:grid-cols-[240px_1fr]">
      <aside className="rounded-3xl bg-white p-4 shadow-md">
        <h2 className="mb-4 px-2 text-lg font-semibold text-slate-800">Панель модератора</h2>
        <nav className="space-y-2">
          {sections.map((section) => (
            <NavLink key={section.to} to={section.to} end={section.end} className={linkClass}>
              {section.label}
            </NavLink>
          ))}
        </nav>
        <button
          type="button"
          onClick={() => {
            clearToken()
            window.location.href = '/login'
          }}
          className="mt-6 w-full rounded-2xl border border-sky-200 px-4 py-3 text-sm text-slate-600 hover:bg-sky-50"
        >
          Выйти
        </button>
      </aside>
      <div>
        <Outlet />
      </div>
    </div>
  )
}
