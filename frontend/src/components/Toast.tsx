interface Props {
  error: string | null
  onClose: () => void
}

export default function Toast({ error, onClose }: Props) {
  if (!error) return null
  return (
    <div className="toast">
      <span>{error}</span>
      <button onClick={onClose} aria-label="Dismiss">
        ×
      </button>
    </div>
  )
}
