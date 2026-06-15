import CardItem from './CardItem'

export default function CardGrid({ cards = [], emptyMessage = 'Сборы не найдены' }) {
  if (!cards.length) {
    return (
      <div className="rounded-3xl bg-white p-10 text-center text-slate-500 shadow-md">
        {emptyMessage}
      </div>
    )
  }
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {cards.map((card) => (
        <CardItem key={card.id} card={card} />
      ))}
    </div>
  )
}
