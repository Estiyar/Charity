export default function Footer() {
  return (
    <footer className="mt-16 border-t border-sky-100 bg-white">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 md:grid-cols-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-800">е-Көмек</h3>
          <p className="mt-2 text-sm text-slate-600">
            Цифровая платформа благотворительности с проверкой документов и прозрачной историей расходов.
          </p>
        </div>
        <div>
          <h4 className="font-semibold text-slate-800">Как мы работаем</h4>
          <ul className="mt-2 space-y-1 text-sm text-slate-600">
            <li>Проверка каждой заявки модератором</li>
            <li>Эскроу-счёт для каждого сбора</li>
            <li>Публичная история расходов</li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold text-slate-800">Контакты</h4>
          <p className="mt-2 text-sm text-slate-600">support@charity.kz</p>
          <p className="text-sm text-slate-600">+7 777 000 00 00</p>
        </div>
      </div>
      <div className="border-t border-sky-100 py-4 text-center text-sm text-slate-500">
        © 2026 е-Көмек. MVP demo version.
      </div>
    </footer>
  )
}
