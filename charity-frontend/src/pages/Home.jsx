import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchCards, fetchStats } from '../api/client'
import CardGrid from '../components/CardGrid'
import StatsBlock from '../components/StatsBlock'
import { getCreateCollectionPath, useCurrentUser } from '../hooks/useCurrentUser'

export default function Home() {
  const { user } = useCurrentUser()
  const createCollectionPath = getCreateCollectionPath(user)
  const [stats, setStats] = useState(null)
  const [cards, setCards] = useState([])

  useEffect(() => {
    fetchStats().then(setStats).catch(() => setStats({}))
    fetchCards({ status: 'active' })
      .then((data) => setCards(data.results || []))
      .catch(() => setCards([]))
  }, [])

  return (
    <div>
      <section className="bg-gradient-to-br from-sky-100 via-white to-mint-100">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-16 lg:grid-cols-2 lg:items-center">
          <div>
            <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-teal-600">
              Благотворительность с прозрачностью
            </p>
            <h1 className="text-4xl font-bold leading-tight text-slate-800 md:text-5xl">
              Помогайте проверенным сборам с уверенностью
            </h1>
            <p className="mt-4 text-lg text-slate-600">
              Платформа цифровизации пожертвований: модерация заявок, эскроу-счета,
              публичная история расходов и защита персональных данных.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/catalog"
                className="rounded-full bg-teal-500 px-6 py-4 text-base font-semibold text-white shadow-md transition hover:bg-teal-600"
              >
                Помочь сейчас
              </Link>
              <Link
                to={createCollectionPath}
                className="rounded-full border border-teal-500 px-6 py-4 text-base font-semibold text-teal-600 transition hover:bg-white"
              >
                Создать сбор
              </Link>
            </div>
          </div>
          <div className="rounded-[2rem] bg-white p-8 shadow-lg">
            <h2 className="text-2xl font-semibold text-slate-800">Доверие и прозрачность</h2>
            <p className="mt-3 text-slate-600">
              Каждая карточка проходит модерацию, документы проверяются, а средства
              учитываются отдельно по каждому сбору.
            </p>
            <ul className="mt-6 space-y-3 text-sm text-slate-600">
              <li>✓ Проверенные документы и маскирование конфиденциальных данных</li>
              <li>✓ Демо-платёж в MVP и подготовка к банковскому шлюзу</li>
              <li>✓ Публичная статистика и история пожертвований</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12">
        <h2 className="mb-6 text-2xl font-semibold text-slate-800">Статистика платформы</h2>
        <StatsBlock stats={stats} />
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-slate-800">Активные сборы</h2>
          <Link to="/catalog" className="text-sm font-semibold text-teal-600 hover:underline">
            Смотреть все
          </Link>
        </div>
        <CardGrid cards={cards} emptyMessage="Пока нет активных сборов" />
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12">
        <h2 className="mb-6 text-2xl font-semibold text-slate-800">Как это работает</h2>
        <div className="grid gap-4 md:grid-cols-4">
          {[
            ['1', 'Автор создаёт сбор', 'Заполняет анкету и загружает документы'],
            ['2', 'Модератор проверяет', 'Проверяет данные и одобряет публикацию'],
            ['3', 'Доноры помогают', 'Выбирают сумму и совершают демо-пожертвование'],
            ['4', 'Прозрачные расходы', 'Подтверждённые расходы видны публично'],
          ].map(([step, title, text]) => (
            <div key={step} className="rounded-3xl bg-white p-6 shadow-md">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-teal-500 text-white">
                {step}
              </div>
              <h3 className="font-semibold text-slate-800">{title}</h3>
              <p className="mt-2 text-sm text-slate-600">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12">
        <div className="rounded-[2rem] bg-white p-8 shadow-md">
          <h2 className="text-2xl font-semibold text-slate-800">Блок доверия</h2>
          <p className="mt-3 max-w-3xl text-slate-600">
            Мы скрываем конфиденциальные данные, проверяем документы и показываем только
            подтверждённую информацию. В production-версии платежи будут проходить через
            платёжный шлюз на эскроу-счёт.
          </p>
        </div>
      </section>
    </div>
  )
}
