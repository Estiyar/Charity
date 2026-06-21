export default function FileUploadField({ id, accept, multiple, label, files, onChange }) {
  const selectedFiles = multiple ? files : files ? [files] : []

  return (
    <div className="space-y-2">
      <input
        id={id}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={onChange}
        className="sr-only"
      />
      <label
        htmlFor={id}
        className="inline-flex cursor-pointer items-center rounded-2xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-semibold text-teal-700 transition hover:bg-teal-100"
      >
        {label}
      </label>
      {selectedFiles.length > 0 && (
        <ul className="space-y-1 text-xs text-slate-500">
          {selectedFiles.map((file) => (
            <li key={`${file.name}-${file.lastModified}`}>{file.name}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
