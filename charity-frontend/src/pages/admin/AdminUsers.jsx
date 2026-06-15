import { useEffect, useState } from 'react'
import { assignUserRole, blockUser, fetchAdminUsers, unblockUser } from '../../api/client'

const roles = ['donor', 'author', 'moderator', 'admin']

export default function AdminUsers() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    fetchAdminUsers().then(setUsers).finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  async function handleRoleChange(userId, role) {
    await assignUserRole(userId, role)
    load()
  }

  async function handleBlock(userId) {
    await blockUser(userId)
    load()
  }

  async function handleUnblock(userId) {
    await unblockUser(userId)
    load()
  }

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h1 className="mb-6 text-2xl font-semibold text-slate-800">Пользователи</h1>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-sky-100 text-slate-500">
              <th className="py-2 pr-4">ФИО</th>
              <th className="py-2 pr-4">Email</th>
              <th className="py-2 pr-4">Роль</th>
              <th className="py-2 pr-4">Статус</th>
              <th className="py-2">Действия</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b border-sky-50">
                <td className="py-3 pr-4">{user.full_name}</td>
                <td className="py-3 pr-4">{user.email}</td>
                <td className="py-3 pr-4">
                  <select
                    value={user.role}
                    onChange={(e) => handleRoleChange(user.id, e.target.value)}
                    className="rounded-xl border border-sky-100 px-2 py-1"
                  >
                    {roles.map((role) => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                </td>
                <td className="py-3 pr-4">{user.status}</td>
                <td className="py-3">
                  {user.status === 'blocked' ? (
                    <button
                      type="button"
                      onClick={() => handleUnblock(user.id)}
                      className="rounded-xl bg-teal-500 px-3 py-1 text-xs font-semibold text-white"
                    >
                      Разблокировать
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleBlock(user.id)}
                      className="rounded-xl bg-red-500 px-3 py-1 text-xs font-semibold text-white"
                    >
                      Заблокировать
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
