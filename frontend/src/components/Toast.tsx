interface Props {
  /** Legacy: the App.tsx component passes `error` for error toasts. */
  error?: string | null
  /** New API: a free-form message. */
  message?: string | null
  variant?: 'success' | 'info' | 'error'
  onClose: () => void
}

/**
 * Single-message toast. Auto-dismisses after 3 seconds; can be closed
 * by the user with the × button. Only renders when the message is
 * non-null.
 *
 * Backwards-compatible: legacy callers pass `error`, new callers
 * pass `message` and an optional `variant`.
 */
export default function Toast({ error, message, variant, onClose }: Props) {
  const text = message ?? error ?? null
  if (!text) return null
  const v = variant ?? (error ? 'error' : 'info')
  return (
    <div className={`rp-toast rp-toast--${v}`} role="status" aria-live="polite">
      <span>{text}</span>
      <button onClick={onClose} aria-label="Dismiss" className="rp-toast__close" type="button">
        ×
      </button>
    </div>
  )
}
