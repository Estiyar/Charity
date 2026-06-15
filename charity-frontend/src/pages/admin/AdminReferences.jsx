import { useEffect, useState } from 'react'
import {
  createCity,
  createDiagnosis,
  deleteCity,
  deleteDiagnosis,
  fetchAdminCities,
  fetchAdminDiagnoses,
} from '../../api/client'

export default function AdminReferences() {
  const [cities, setCities] = useState([])
  const [diagnoses, setDiagnoses] = useState([])
  const [cityName, setCityName] = useState('')
  const [diagnosisName, setDiagnosisName] = useState('')

  function load() {
    fetchAdminCities().then(setCities)
    fetchAdminDiagnoses().then(setDiagnoses)
  }

  useEffect(() => {
    load()
  }, [])

  async function handleAddCity(event) {
    event.preventDefault()
    if (!cityName.trim()) return
    await createCity(cityName.trim())
    setCityName('')
    load()
  }

  async function handleAddDiagnosis(event) {
    event.preventDefault()
    if (!diagnosisName.trim()) return
    await createDiagnosis(diagnosisName.trim())
    setDiagnosisName('')
    load()
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h1 className="mb-4 text-2xl font-semibold text-slate-800">Города</h1>
        <form onSubmit={handleAddCity} className="mb-4 flex gap-2">
          <input
            value={cityName}
            onChange={(e) => setCityName(e.target.value)}
            placeholder="Новый город"
            className="flex-1 rounded-2xl border border-sky-100 px-4 py-2 text-sm"
          />
          <button type="submit" className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white">
            Добавить
          </button>
        </form>
        <div className="space-y-2">
          {cities.map((city) => (
            <div key={city.id} className="flex items-center justify-between rounded-2xl bg-sky-50 px-4 py-2">
              <span>{city.name}</span>
              <button
                type="button"
                onClick={() => deleteCity(city.id).then(load)}
                className="text-xs text-red-500"
              >
                Удалить
              </button>
            </div>
          ))}
        </div>
      </section>
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-4 text-2xl font-semibold text-slate-800">Диагнозы</h2>
        <form onSubmit={handleAddDiagnosis} className="mb-4 flex gap-2">
          <input
            value={diagnosisName}
            onChange={(e) => setDiagnosisName(e.target.value)}
            placeholder="Новый диагноз"
            className="flex-1 rounded-2xl border border-sky-100 px-4 py-2 text-sm"
          />
          <button type="submit" className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white">
            Добавить
          </button>
        </form>
        <div className="space-y-2">
          {diagnoses.map((diagnosis) => (
            <div key={diagnosis.id} className="flex items-center justify-between rounded-2xl bg-sky-50 px-4 py-2">
              <span>{diagnosis.name}</span>
              <button
                type="button"
                onClick={() => deleteDiagnosis(diagnosis.id).then(load)}
                className="text-xs text-red-500"
              >
                Удалить
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
