import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { CloseIcon } from './icons'

interface ModalProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  /** Optional footer (typically action buttons). */
  footer?: ReactNode
  /** Max-width preset. */
  size?: 'sm' | 'md' | 'lg'
}

/**
 * Lightweight modal — focus-traps roughly, closes on Escape and on
 * backdrop click. Used by the Final Ruling page for the refund
 * confirmation, viewer assignment, view-report, and evidence upload
 * flows. The body scrolls if the content is tall; the backdrop does
 * not.
 */
export default function Modal({ open, title, onClose, children, footer, size = 'md' }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    // Move focus into the dialog so the first interactive control is reachable.
    const previouslyFocused = document.activeElement as HTMLElement | null
    const first = dialogRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea',
    )
    first?.focus()
    return () => {
      document.removeEventListener('keydown', onKey)
      previouslyFocused?.focus()
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="rp-modal__backdrop"
      role="presentation"
      onMouseDown={(e) => {
        // Only close on a direct backdrop click, not on a click that
        // bubbled up from inside the dialog.
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        ref={dialogRef}
        className={`rp-modal rp-modal--${size}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="rp-modal__head">
          <h2>{title}</h2>
          <button
            type="button"
            className="rp-modal__close"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <CloseIcon size={16} />
          </button>
        </header>
        <div className="rp-modal__body">{children}</div>
        {footer && <footer className="rp-modal__foot">{footer}</footer>}
      </div>
    </div>
  )
}
