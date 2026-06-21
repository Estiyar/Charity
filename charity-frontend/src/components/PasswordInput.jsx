import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

const inputClassName =
  'w-full rounded-2xl border border-sky-100 px-4 py-3 pr-12 text-sm outline-none focus:border-teal-500'

export default function PasswordInput({
  value,
  onChange,
  placeholder,
  required = false,
  minLength,
}) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="relative">
      <input
        type={visible ? 'text' : 'password'}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required={required}
        minLength={minLength}
        className={inputClassName}
      />
      <button
        type="button"
        onClick={() => setVisible((current) => !current)}
        className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 transition hover:text-slate-600"
        aria-label={visible ? 'Скрыть пароль' : 'Показать пароль'}
      >
        {visible ? <EyeOff size={18} strokeWidth={2} /> : <Eye size={18} strokeWidth={2} />}
      </button>
    </div>
  )
}
