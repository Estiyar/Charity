import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchCard, fetchCardHistory, fetchDonations, fetchPublicCardDocuments, fetchPublicExpenseReport, mediaUrl } from '../api/client'
import ReportProblemForm from '../components/ReportProblemForm'
import ApprovedExpensesTable from '../components/ApprovedExpensesTable'
import CardTimeline from '../components/CardTimeline'
import DonationForm from '../components/DonationForm'
import EscrowBlock from '../components/EscrowBlock'
import ProgressBar from '../components/ProgressBar'
import PublicDocumentList from '../components/PublicDocumentList'
import TrustBadges from '../components/TrustBadges'
import { formatDate, formatMoney, statusBadgeClass, statusLabel } from '../utils/format'

const OWN_FUNDRAISER_DONATION_MESSAGE = 'Нельзя жертвовать в собственный сбор.'

export default function CardDetail() {
  const { id } = useParams()
  const [card, setCard] = useState(null)
  const [donations, setDonations] = useState([])
  const [expenseReport, setExpenseReport] = useState(null)
  const [history, setHistory] = useState([])
  const [documents, setDocuments] = useState([])
  const [error, setError] = useState('')

  function loadCard() {
    fetchCard(id)
      .then(setCard)
      .catch(() => setError('Сбор не найден или недоступен публично.'))
  }

  useEffect(() => {
    loadCard()
    fetchDonations(id).then(setDonations).catch(() => setDonations([]))
    fetchPublicExpenseReport(id).then(setExpenseReport).catch(() => setExpenseReport(null))
    fetchCardHistory(id).then(setHistory).catch(() => setHistory([]))
    fetchPublicCardDocuments(id).then(setDocuments).catch(() => setDocuments([]))
  }, [id])

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="text-slate-600">{error}</p>
        <Link to="/catalog" className="mt-4 inline-block text-teal-600 hover:underline">
          Вернуться в каталог
        </Link>
      </div>
    )
  }

  if (!card) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center text-slate-500">
        Загрузка...
      </div>
    )
  }

  const photo = mediaUrl(card.photo_url)
  const canDonate = card.status === 'active' && card.can_donate !== false

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-10">
      <Link to="/catalog" className="text-sm font-medium text-teal-600 hover:underline">
        ← Назад в каталог
      </Link>

      <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <section className="overflow-hidden rounded-3xl bg-white shadow-md">
            <div className="aspect-[16/9] bg-sky-100">
              {photo ? (
                <img src={photo} alt={card.full_name} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center text-slate-400">Нет фото</div>
              )}
            </div>
            <div className="space-y-4 p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h1 className="text-3xl font-bold text-slate-800">{card.full_name}</h1>
                <span className={`rounded-full px-4 py-2 text-sm font-medium ${statusBadgeClass(card.status)}`}>
                  {statusLabel(card.status)}
                </span>
              </div>
              <p className="text-lg text-slate-600">{card.diagnosis}</p>
              <div className="grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
                <p><span className="font-medium text-slate-800">Город:</span> {card.city}</p>
                <p><span className="font-medium text-slate-800">Поликлиника:</span> {card.clinic || '—'}</p>
                <p><span className="font-medium text-slate-800">Возраст:</span> {card.age || '—'}</p>
                <p><span className="font-medium text-slate-800">Пол:</span> {card.gender || '—'}</p>
                <p><span className="font-medium text-slate-800">Дата окончания:</span> {formatDate(card.end_date)}</p>
                <p><span className="font-medium text-slate-800">ИИН:</span> {card.iin_masked || '—'}</p>
              </div>
              <p className="text-slate-700">{card.description || 'Описание не указано.'}</p>
              {card.status === 'suspended' ? (
                <div className="rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-700">
                  Сбор временно приостановлен. История и документы остаются доступны, новые пожертвования не принимаются.
                </div>
              ) : null}
              <div>
                <div className="mb-2 flex justify-between text-sm">
                  <span className="font-semibold text-slate-800">
                    {formatMoney(card.collected_amount)} собрано
                  </span>
                  <span className="text-slate-500">Цель {formatMoney(card.target_amount)}</span>
                </div>
                <ProgressBar percent={card.progress_percent} />
              </div>
            </div>
          </section>

          <TrustBadges trustStatus={card.trust_status} />

          <PublicDocumentList documents={documents} />

          <CardTimeline events={history} />

          <EscrowBlock card={card} />

          <section className="rounded-3xl bg-white p-6 shadow-md">
            <h2 className="text-xl font-semibold text-slate-800">Блок прозрачности</h2>
            <p className="mt-2 text-sm text-slate-600">
              История пожертвований по этому сбору.
            </p>
            {donations.length ? (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-sky-100 text-slate-500">
                      <th className="py-2 pr-4">Донор</th>
                      <th className="py-2 pr-4">Сумма</th>
                      <th className="py-2">Дата</th>
                    </tr>
                  </thead>
                  <tbody>
                    {donations.map((donation) => (
                      <tr key={donation.id} className="border-b border-sky-50">
                        <td className="py-3 pr-4">{donation.donor_name}</td>
                        <td className="py-3 pr-4">{formatMoney(donation.amount)}</td>
                        <td className="py-3">{formatDate(donation.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-500">Пожертвований пока нет.</p>
            )}
          </section>

          <ApprovedExpensesTable report={expenseReport} />

          <ReportProblemForm cardId={card.id} />
        </div>

        <div id="donate">
          {canDonate ? (
            <DonationForm cardId={card.id} />
          ) : card.status === 'completed' ? (
            <div className="rounded-3xl bg-white p-6 shadow-md">
              <h3 className="text-xl font-semibold text-slate-800">Сделать пожертвование</h3>
              <p className="mt-3 text-sm text-slate-600">
                Сбор завершён. Цель достигнута, новые пожертвования не принимаются.
              </p>
            </div>
          ) : card.status === 'suspended' ? (
            <div className="rounded-3xl bg-white p-6 shadow-md">
              <h3 className="text-xl font-semibold text-slate-800">Сделать пожертвование</h3>
              <p className="mt-3 text-sm text-slate-600">
                Сбор приостановлен модерацией. Новые пожертвования временно недоступны.
              </p>
            </div>
          ) : card.status === 'active' && card.can_donate === false ? (
            <div className="rounded-3xl bg-white p-6 shadow-md">
              <h3 className="text-xl font-semibold text-slate-800">Сделать пожертвование</h3>
              <p className="mt-3 text-sm text-slate-600">{OWN_FUNDRAISER_DONATION_MESSAGE}</p>
            </div>
          ) : (
            <div className="rounded-3xl bg-white p-6 shadow-md">
              <h3 className="text-xl font-semibold text-slate-800">Сделать пожертвование</h3>
              <p className="mt-3 text-sm text-slate-600">
                Пожертвования принимаются только для активных сборов.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
