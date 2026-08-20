import { clearToken } from '../../api/auth'
import DonorCabinetPanel from '../../components/DonorCabinetPanel'
import { Link } from 'react-router-dom'

export default function DonorDashboard() {
  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Личный кабинет донора</h1>
          <p className="text-slate-600">Профиль, баланс и история пожертвований</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/profile"
            className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600"
          >
            Профиль
          </Link>
          <button
            type="button"
            onClick={() => {
              clearToken()
              window.location.href = '/'
            }}
            className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600"
          >
            Выйти
          </button>
        </div>
      </div>

      <DonorCabinetPanel showProfile />
    </div>
  )
}
