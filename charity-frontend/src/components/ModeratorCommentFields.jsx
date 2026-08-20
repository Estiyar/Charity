export default function ModeratorCommentFields({
  revisionComment,
  onRevisionChange,
  internalComment,
  onInternalChange,
}) {
  return (
    <div className="space-y-3">
      <textarea
        value={revisionComment}
        onChange={(event) => onRevisionChange(event.target.value)}
        placeholder="Что исправить автору (обязательно при доработке и отклонении)"
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        rows={4}
      />
      <textarea
        value={internalComment}
        onChange={(event) => onInternalChange(event.target.value)}
        placeholder="Внутренний комментарий (виден только сотрудникам)"
        className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-teal-500"
        rows={3}
      />
    </div>
  )
}

export function CommentHistory({ comments, emptyText = 'Комментариев пока нет' }) {
  if (!comments?.length) {
    return <p className="text-sm text-slate-500">{emptyText}</p>
  }
  return (
    <div className="space-y-2">
      {comments.map((item) => (
        <div key={item.id} className="rounded-2xl bg-sky-50 p-3 text-sm">
          <p className="font-medium text-slate-800">
            {item.comment_type === 'internal_comment' ? 'Внутренний комментарий' : 'Для автора'}
            {item.author?.name ? ` · ${item.author.name}` : ''}
          </p>
          <p className="text-slate-700">{item.body}</p>
          {item.edited_at ? <p className="text-xs text-slate-400">Изменён</p> : null}
          {(item.edits || []).map((edit) => (
            <p key={edit.id} className="mt-1 text-xs text-slate-500">
              Было: {edit.previous_body}
            </p>
          ))}
        </div>
      ))}
    </div>
  )
}
