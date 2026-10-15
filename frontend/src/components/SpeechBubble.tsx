import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'

interface SpeechBubbleProps {
  /** The full text to display. */
  text: string
  /** Whether the speaker is currently active. When false, bubble is dim/empty. */
  active: boolean
  /** Milliseconds per character. Default ~18ms. */
  cps?: number
  /** Called when the typing animation finishes. */
  onDone?: () => void
}

/**
 * Speech bubble that types text in one character at a time. When the
 * user prefers reduced motion, the full text is shown immediately.
 * When the speaker is no longer active, the bubble fades out.
 *
 * Implementation note: we keep a `shown` state that tracks how many
 * characters of `text` are currently rendered. The animation tick is
 * a single setInterval started inside an effect that depends only on
 * the *transition* (text changed -> reset, active changed -> start/stop).
 * A ref tracks whether the typing has finished for the current text so
 * `onDone` fires exactly once per text.
 */
export default function SpeechBubble({ text, active, cps = 22, onDone }: SpeechBubbleProps) {
  const reduced = useReducedMotion()
  // When reduced motion is on, render the full text immediately. We can
  // do this without an effect by initialising state lazily and then
  // updating it from a key.
  const initial = reduced ? text.length : 0
  const [shown, setShown] = useState<number>(initial)
  const doneRef = useRef<boolean>(initial >= text.length)
  const textRef = useRef<string>(text)

  // If `text` changes (new round), reset the typing animation.
  useEffect(() => {
    if (textRef.current === text) return
    textRef.current = text
    doneRef.current = reduced || text.length === 0
    setShown(reduced ? text.length : 0)
  }, [text, reduced])

  // Drive the typing animation. The interval is registered only while
  // the bubble is active and the text isn't fully shown yet.
  useEffect(() => {
    if (!active) return
    if (reduced) return
    if (shown >= text.length) return
    const step = Math.max(1, Math.floor(cps / 16))
    const id = window.setInterval(() => {
      setShown((s) => {
        const next = Math.min(text.length, s + step)
        if (next >= text.length && !doneRef.current) {
          doneRef.current = true
          onDone?.()
        }
        return next
      })
    }, 16)
    return () => window.clearInterval(id)
  }, [active, reduced, shown, text.length, cps, onDone])

  // If reduced motion flips on mid-animation, we still want the full
  // text to appear. We don't synchronously setShown (that would be a
  // setState-in-effect); instead we derive the effective length at
  // render time. The typing interval also early-returns when `reduced`
  // is true, so `shown` won't advance further.
  const effectiveShown = reduced ? text.length : shown
  const display = text.slice(0, effectiveShown)
  const finished = effectiveShown >= text.length

  return (
    <div
      className={`rp-bubble ${active ? 'is-active' : 'is-idle'} ${finished ? 'is-done' : 'is-typing'}`}
      role={active ? 'status' : undefined}
      aria-live={active ? 'polite' : undefined}
    >
      <p>{display}</p>
      {!finished && active && !reduced && <span className="rp-bubble__caret" aria-hidden />}
    </div>
  )
}
