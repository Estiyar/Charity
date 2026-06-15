export default function ProgressBar({ percent = 0 }) {
  const value = Math.min(100, Math.max(0, Number(percent) || 0))
  return (
    <div className="h-3 w-full overflow-hidden rounded-full bg-sky-100">
      <div
        className="h-full rounded-full bg-gradient-to-r from-teal-500 to-sky-400 transition-all"
        style={{ width: `${value}%` }}
      />
    </div>
  )
}
