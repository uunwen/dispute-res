import { useEffect, useMemo, useRef, useState } from 'react'
import { api, type AgentMessage, type Dispute } from '../api'
import StatusBadge from '../components/StatusBadge'
import { DriverMascot, JudgeMascot, RiderMascot } from '../components/DebateMascots'
import PlaybackBar from '../components/PlaybackBar'
import SpeechBubble from '../components/SpeechBubble'
import { useDisputeStream } from '../hooks/useDisputeStream'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { buildRounds, type DebateRound, type Speaker } from '../lib/rounds'
import { categoryLabel, disputeStatusVariant } from '../lib/status'
import { CheckIcon, CloseIcon } from '../components/icons'

interface DebateProps {
  disputeId: number
  onBack: () => void
  onSeeRuling?: (id: number) => void
  onSeeEvidence?: (id: number) => void
  onSeeArguments?: (id: number) => void
}

const STEP_BASE_MS = 7000 // base time per round at 1x; scaled by speed

type DebateStageKey = 'evidence' | 'opening' | 'fraud' | 'rebuttal' | 'judge' | 'verdict'

interface DebateStep {
  key: DebateStageKey
  label: string
}

type StepState = 'done' | 'active' | 'future'

function messageRound(m: AgentMessage): string {
  const c = (m.content ?? {}) as Record<string, unknown>
  return typeof c.round === 'string' ? c.round : 'opening'
}

/** Derive the fixed pipeline stages from the streamed messages + finish state. */
function computeDebateProgress(messages: AgentMessage[], finished: boolean, rebuttalEnabled: boolean) {
  const opening = (sender: 'RiderAdvocate' | 'DriverAdvocate') =>
    messages.some((m) => m.sender === sender && m.message_type === 'case_brief' && messageRound(m) === 'opening')
  const rebuttal = (sender: 'RiderAdvocate' | 'DriverAdvocate') =>
    messages.some((m) => m.sender === sender && m.message_type === 'case_brief' && messageRound(m) === 'rebuttal')

  const hasOpeningRider = opening('RiderAdvocate')
  const hasOpeningDriver = opening('DriverAdvocate')
  const hasFraud = messages.some((m) => m.message_type === 'fraud_signal')
  const hasRebuttalRider = rebuttal('RiderAdvocate')
  const hasRebuttalDriver = rebuttal('DriverAdvocate')

  const steps: DebateStep[] = [
    { key: 'evidence', label: 'Evidence gathering' },
    { key: 'opening', label: 'Opening arguments' },
    { key: 'fraud', label: 'Fraud check' },
  ]
  if (rebuttalEnabled) steps.push({ key: 'rebuttal', label: 'Rebuttal round' })
  steps.push({ key: 'judge', label: 'Judge deliberation' })
  steps.push({ key: 'verdict', label: 'Final verdict' })

  const done: Record<DebateStageKey, boolean> = {
    evidence: hasOpeningRider || hasOpeningDriver,
    opening: hasOpeningRider && hasOpeningDriver,
    fraud: hasFraud,
    rebuttal: hasRebuttalRider && hasRebuttalDriver,
    judge: finished,
    verdict: finished,
  }

  let states: StepState[]
  if (finished) {
    states = steps.map(() => 'done' as StepState)
  } else {
    const firstUndone = steps.findIndex((s) => !done[s.key])
    states = steps.map((_, i): StepState => {
      if (firstUndone === -1 || i < firstUndone) return 'done'
      if (i === firstUndone) return 'active'
      return 'future'
    })
  }

  return { steps, states }
}

function formatSeconds(total: number): string {
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

interface DebateProgressProps {
  steps: DebateStep[]
  states: StepState[]
  finished: boolean
  degraded: boolean
  slow: boolean
  elapsed: number
  reducedMotion: boolean
  onViewVerdict?: () => void
}

function DebateProgress({
  steps,
  states,
  finished,
  degraded,
  slow,
  elapsed,
  reducedMotion,
  onViewVerdict,
}: DebateProgressProps) {
  const statusText = finished
    ? 'Verdict ready'
    : slow
      ? 'Still working, the LLM is slow'
      : 'Agents are still debating, the verdict appears when the Judge finishes'

  return (
    <div className="rp-debate-progress" aria-label="Debate progress">
      <div className="rp-debate-progress__row">
        <ol className="rp-debate-steps">
          {steps.map((s, i) => {
            const state = states[i] ?? 'future'
            return (
              <li
                key={s.key}
                className={`rp-debate-step is-${state} ${reducedMotion ? 'is-no-anim' : ''}`}
              >
                <span className="rp-debate-step__dot" aria-hidden>
                  {state === 'done' ? <CheckIcon size={12} strokeWidth={3} /> : null}
                </span>
                <span className="rp-debate-step__label">
                  {s.label}
                  {state === 'active' && <span className="rp-debate-step__working">working…</span>}
                </span>
              </li>
            )
          })}
        </ol>
        <div className="rp-debate-progress__meta">
          <span className="rp-debate-progress__timer">{formatSeconds(elapsed)}</span>
          <span className="rp-debate-progress__status">{statusText}</span>
        </div>
      </div>

      {degraded && (
        <div className="rp-debate-progress__warning" role="status">
          Finished with deterministic fallback
        </div>
      )}

      {finished && onViewVerdict && (
        <div className="rp-debate-progress__verdict">
          <button type="button" className="rp-btn rp-btn--primary" onClick={onViewVerdict}>
            View verdict →
          </button>
        </div>
      )}
    </div>
  )
}

export default function Debate({ disputeId, onBack, onSeeRuling, onSeeEvidence, onSeeArguments }: DebateProps) {
  const { dispute, messages, events, live, loading, error } = useDisputeStream(disputeId)

  const reducedMotion = useReducedMotion()

  const [rebuttalEnabled, setRebuttalEnabled] = useState(true)
  const [rulingDegraded, setRulingDegraded] = useState<boolean | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [slow, setSlow] = useState(false)

  const finished =
    (dispute !== null && dispute.status !== 'open') || events.some((e) => e.type === 'ruling_ready')

  const progress = useMemo(
    () => computeDebateProgress(messages, finished, rebuttalEnabled),
    [messages, finished, rebuttalEnabled],
  )

  useEffect(() => {
    api
      .getSettings()
      .then((s) => setRebuttalEnabled(s.rebuttal_enabled !== false))
      .catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!finished) return
    let cancelled = false
    api
      .getRuling(disputeId)
      .then((r) => {
        if (!cancelled) setRulingDegraded(r.llm_degraded)
      })
      .catch(() => {
        if (!cancelled) setRulingDegraded(false)
      })
    return () => {
      cancelled = true
    }
  }, [finished, disputeId])

  const lastMessageRef = useRef<number>(0)
  useEffect(() => {
    lastMessageRef.current = Date.now()
  }, [messages.length])

  useEffect(() => {
    if (!live || finished) return
    lastMessageRef.current = Date.now()
    const start = Date.now()
    const id = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000))
      setSlow(Date.now() - lastMessageRef.current > 90_000)
    }, 1000)
    return () => window.clearInterval(id)
  }, [live, finished])

  const degraded = error !== null || (finished && rulingDegraded === true)

  // Build the round list strictly from the messages we have. Re-derives
  // automatically as the SSE stream appends new messages.
  const rounds: DebateRound[] = useMemo(() => buildRounds(messages), [messages])

  // Playback state
  const [isPlaying, setIsPlaying] = useState<boolean>(true)
  const [speed, setSpeed] = useState<number>(1)
  const [currentIndex, setCurrentIndex] = useState<number>(0)
  const [progressInStep, setProgressInStep] = useState<number>(0) // 0..1 of the current step
  const [showTranscript, setShowTranscript] = useState<boolean>(false)

  // When new messages arrive and playback is on, advance to the latest
  // finished round automatically (so the timeline follows the stream).
  const autoFollow = useRef<boolean>(true)
  useEffect(() => {
    if (autoFollow.current && rounds.length > currentIndex) {
      setCurrentIndex(rounds.length - 1)
      setProgressInStep(0)
    }
  }, [rounds.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // Animation tick: advance the progress within the current step, and
  // roll over to the next step (or stop at the end) inside the tick
  // callback so we don't need a separate effect that calls setState.
  useEffect(() => {
    if (!isPlaying) return
    if (rounds.length === 0) return
    if (currentIndex >= rounds.length) return
    const stepMs = STEP_BASE_MS / speed
    const id = window.setInterval(() => {
      setProgressInStep((p) => {
        const next = p + 100 / stepMs
        if (next >= 1) {
          // advance to the next step on the next paint via a microtask
          autoFollow.current = true
          if (currentIndex + 1 < rounds.length) {
            setCurrentIndex(currentIndex + 1)
            return 0
          }
          // last step finished -> freeze timeline and pause
          setIsPlaying(false)
          return 1
        }
        return next
      })
    }, 100)
    return () => window.clearInterval(id)
  }, [isPlaying, speed, currentIndex, rounds.length])

  // Re-derive status / time strings
  const headerLine = useMemo(() => buildHeaderLine(dispute, live), [dispute, live])

  // Total & elapsed time
  const totalMs = rounds.length * STEP_BASE_MS
  const elapsedMs = currentIndex * STEP_BASE_MS + progressInStep * STEP_BASE_MS
  const overallProgress = rounds.length === 0 ? 0 : currentIndex / rounds.length + progressInStep / rounds.length
  const currentRound = rounds[currentIndex] ?? null
  const activeSpeaker: Speaker = currentRound?.speaker ?? 'rider'

  function handleSeek(fraction: number) {
    autoFollow.current = false
    if (rounds.length === 0) return
    const f = Math.max(0, Math.min(1, fraction))
    const idx = Math.min(rounds.length - 1, Math.floor(f * rounds.length))
    setCurrentIndex(idx)
    setProgressInStep(f * rounds.length - idx)
  }

  function jumpToRound(idx: number) {
    autoFollow.current = false
    if (idx <= currentIndex || rounds[idx]?.message) {
      // jumping to a round we have the message for is allowed
      setCurrentIndex(idx)
      setProgressInStep(0)
    } else {
      // future round not yet produced — clamp to latest
      setCurrentIndex(rounds.length - 1)
      setProgressInStep(0)
    }
  }

  if (loading) {
    return (
      <div className="rp-page rp-debate">
        <div className="rp-card rp-card--padded">Loading dispute…</div>
      </div>
    )
  }
  if (error || !dispute) {
    return (
      <div className="rp-page rp-debate">
        <div className="rp-card rp-card--padded">
          <strong>Couldn't load the dispute.</strong>
          <p className="rp-muted">{error ?? 'Dispute not found.'}</p>
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onBack}>
            ← Back
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="rp-page rp-debate">
      {/* Header */}
      <div className="rp-debate__header">
        <div className="rp-debate__title">
          <span className="rp-debate__icon" aria-hidden>
            <RiderIcon />
          </span>
          <div>
            <h1>
              Dispute #{disputeId}
              <StatusBadge
                variant={disputeStatusVariant({
                  id: dispute.id,
                  trip_id: dispute.trip_id,
                  category: dispute.category,
                  status: dispute.status,
                  priority: dispute.priority,
                  claim_text: dispute.claim_text,
                  created_at: String(dispute.created_at),
                  outcome: null,
                  refund_amount: null,
                  llm_degraded: null,
                })}
              />
              {live && (
                <span className="rp-debate__live" aria-live="polite">
                  <span className="rp-debate__live-dot" />
                  Live
                </span>
              )}
            </h1>
            <p>
              {categoryLabel(dispute.category)} · {headerLine}
            </p>
          </div>
        </div>
        <div className="rp-debate__header-actions">
          {onSeeArguments && (
            <button
              type="button"
              className="rp-btn rp-btn--ghost"
              onClick={() => onSeeArguments(disputeId)}
            >
              View Arguments
            </button>
          )}
          {onSeeEvidence && (
            <button
              type="button"
              className="rp-btn rp-btn--ghost"
              onClick={() => onSeeEvidence(disputeId)}
            >
              View Evidence
            </button>
          )}
          {rounds.length > 0 && !live && onSeeRuling && (
            <button
              type="button"
              className="rp-btn rp-btn--primary"
              onClick={() => onSeeRuling(disputeId)}
            >
              See ruling →
            </button>
          )}
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onBack}>
            ← Back
          </button>
        </div>
      </div>

      <DebateProgress
        steps={progress.steps}
        states={progress.states}
        finished={finished}
        degraded={degraded}
        slow={slow}
        elapsed={elapsed}
        reducedMotion={reducedMotion}
        onViewVerdict={onSeeRuling ? () => onSeeRuling(disputeId) : undefined}
      />

      {/* Main grid */}
      <div className="rp-debate__grid">
        {/* Stage */}
        <section className="rp-debate__stage" aria-label="Debate stage">
          <SpeakerCard
            speaker="rider"
            active={activeSpeaker === 'rider'}
            label="Rider Advocate"
            subtitle="Presents the rider's case"
            isCurrent={currentRound?.speaker === 'rider'}
            bubbleText={currentRound?.speaker === 'rider' ? currentRound.preview : ''}
            isDone={currentRound?.speaker === 'rider' && currentIndex < rounds.length - 1}
          />
          <SpeakerCard
            speaker="judge"
            active={activeSpeaker === 'judge'}
            label="Judge Agent"
            subtitle="Evaluates evidence and policy"
            isCurrent={currentRound?.speaker === 'judge'}
            bubbleText={currentRound?.speaker === 'judge' ? currentRound.preview : ''}
            isDone={currentRound?.speaker === 'judge' && currentIndex < rounds.length - 1}
            podium
          />
          <SpeakerCard
            speaker="driver"
            active={activeSpeaker === 'driver'}
            label="Driver Advocate"
            subtitle="Presents the driver's defense"
            isCurrent={currentRound?.speaker === 'driver'}
            bubbleText={currentRound?.speaker === 'driver' ? currentRound.preview : ''}
            isDone={currentRound?.speaker === 'driver' && currentIndex < rounds.length - 1}
          />

          <div className="rp-debate__playbar-wrap">
            <PlaybackBar
              isPlaying={isPlaying}
              onTogglePlay={() => setIsPlaying((p) => !p)}
              speed={speed}
              onSpeedChange={setSpeed}
              progress={overallProgress}
              onSeek={handleSeek}
              stepLabel={stepLabel(rounds, currentIndex, rounds.length)}
              elapsedLabel={fmtMmSs(elapsedMs)}
              totalLabel={fmtMmSs(totalMs)}
              scrubbingDisabled={rounds.length === 0}
            />
            {rounds.length > 0 && (
              <button
                type="button"
                className="rp-debate__transcript"
                onClick={() => setShowTranscript(true)}
              >
                View Full Transcript
              </button>
            )}
          </div>
        </section>

        {/* Right rail: Debate Rounds */}
        <aside className="rp-debate__rounds" aria-label="Debate rounds">
          <div className="rp-debate__rounds-head">
            <h2>Debate Rounds</h2>
            <p>{rounds.length} round{rounds.length === 1 ? '' : 's'}</p>
          </div>
          {rounds.length === 0 ? (
            <div className="rp-debate__rounds-empty">
              {live ? (
                <div className="rp-debate__deliberating" role="status">
                  <span className="rp-debate__deliberating-dot" />
                  <span className="rp-debate__deliberating-dot" />
                  <span className="rp-debate__deliberating-dot" />
                  <span>Agents are deliberating…</span>
                </div>
              ) : (
                <p className="rp-muted">No rounds yet.</p>
              )}
            </div>
          ) : (
            <ol className="rp-debate__rounds-list">
              {rounds.map((r, i) => {
                const isCurrent = i === currentIndex
                const isPast = i < currentIndex
                const clickable = isPast || isCurrent
                return (
                  <li
                    key={r.id}
                    className={`rp-debate__round ${isCurrent ? 'is-current' : ''} ${isPast ? 'is-past' : ''} ${clickable ? 'is-clickable' : ''}`}
                  >
                    <button
                      type="button"
                      className="rp-debate__round-btn"
                      onClick={() => clickable && jumpToRound(i)}
                      disabled={!clickable}
                    >
                      <span className="rp-debate__round-num">
                        {isPast ? <CheckMark /> : i + 1}
                      </span>
                      <span className="rp-debate__round-text">
                        <span className="rp-debate__round-label">{r.label}</span>
                        <span className="rp-debate__round-speaker">
                          {speakerShort(r.speaker)}
                        </span>
                      </span>
                    </button>
                  </li>
                )
              })}
            </ol>
          )}
        </aside>
      </div>

      {/* Polished empty state: no messages yet and not live */}
      {rounds.length === 0 && !live && (
        <div className="rp-card rp-card--padded">
          <strong>No agent activity yet for this dispute.</strong>
          <p className="rp-muted">
            The pipeline hasn't produced any messages — the dispute may not have been
            queued. Try reloading or re-submitting.
          </p>
        </div>
      )}

      <TranscriptDrawer
        open={showTranscript}
        onClose={() => setShowTranscript(false)}
        rounds={rounds}
        currentIndex={currentIndex}
        onJump={(i) => {
          jumpToRound(i)
          setShowTranscript(false)
        }}
      />
    </div>
  )
}

/* ============================================================
 * Speaker card (one of three on the stage)
 * ============================================================ */
interface SpeakerCardProps {
  speaker: Speaker
  active: boolean
  isCurrent: boolean
  isDone: boolean
  label: string
  subtitle: string
  bubbleText: string
  podium?: boolean
}

function SpeakerCard({
  speaker,
  active,
  isCurrent,
  isDone,
  label,
  subtitle,
  bubbleText,
  podium,
}: SpeakerCardProps) {
  return (
    <div
      className={[
        'rp-debate__speaker',
        `is-${speaker}`,
        active ? 'is-active' : 'is-idle',
        isCurrent ? 'is-current' : '',
        isDone ? 'is-done' : '',
      ].join(' ')}
    >
      {bubbleText && (
        <SpeechBubble
          text={bubbleText}
          active={isCurrent}
        />
      )}
      <div className={`rp-debate__mascot ${podium ? 'is-podium' : ''}`}>
        {speaker === 'rider' && <RiderMascot size={podium ? 120 : 132} />}
        {speaker === 'judge' && <JudgeMascot size={160} />}
        {speaker === 'driver' && <DriverMascot size={132} />}
      </div>
      <div className="rp-debate__speaker-card">
        <strong>{label}</strong>
        <span>{subtitle}</span>
      </div>
    </div>
  )
}

/* ============================================================
 * Transcript drawer
 * ============================================================ */
function TranscriptDrawer({
  open,
  onClose,
  rounds,
  currentIndex,
  onJump,
}: {
  open: boolean
  onClose: () => void
  rounds: DebateRound[]
  currentIndex: number
  onJump: (i: number) => void
}) {
  // close on escape
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="rp-drawer-backdrop" onClick={onClose} role="presentation">
      <aside
        className="rp-drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Full transcript"
      >
        <header className="rp-drawer__head">
          <h3>Full Transcript</h3>
          <button
            type="button"
            className="rp-drawer__close"
            onClick={onClose}
            aria-label="Close"
          >
            <CloseIcon size={14} />
          </button>
        </header>
        {rounds.length === 0 ? (
          <p className="rp-muted">No agent messages yet.</p>
        ) : (
          <ol className="rp-transcript">
            {rounds.map((r, i) => (
              <li
                key={r.id}
                className={`rp-transcript__item ${i === currentIndex ? 'is-current' : ''}`}
              >
                <div className="rp-transcript__head">
                  <span className={`rp-transcript__speaker is-${r.speaker}`}>
                    {r.label}
                  </span>
                  <button
                    type="button"
                    className="rp-transcript__jump"
                    onClick={() => onJump(i)}
                  >
                    Jump to step
                  </button>
                </div>
                <pre className="rp-transcript__body">{r.fullText}</pre>
              </li>
            ))}
          </ol>
        )}
      </aside>
    </div>
  )
}

/* ============================================================
 * Helpers
 * ============================================================ */
function buildHeaderLine(d: Dispute | null, live: boolean): string {
  if (!d) return ''
  if (live) return 'Agents are investigating this dispute in real time.'
  if (d.status === 'resolved') {
    const dt = new Date(d.created_at)
    return `Resolved on ${dt.toLocaleDateString()}, ${dt.toLocaleTimeString()}`
  }
  if (d.status === 'needs_human_review') {
    return 'Escalated to human review.'
  }
  return ''
}

function fmtMmSs(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function stepLabel(rounds: DebateRound[], currentIndex: number, total: number): string {
  if (total === 0) return 'Waiting for the first agent message…'
  const cur = rounds[currentIndex]
  if (!cur) return `Round ${Math.min(currentIndex + 1, total)} of ${total}`
  return `Round ${currentIndex + 1} of ${total} — ${cur.label}`
}

function speakerShort(s: Speaker): string {
  if (s === 'rider') return 'Rider Advocate'
  if (s === 'driver') return 'Driver Advocate'
  return 'Judge Agent'
}

function CheckMark() {
  return (
    <svg width="12" height="12" viewBox="0 0 14 14" aria-hidden>
      <path
        d="M3 7.5l3 3 5-7"
        stroke="currentColor"
        strokeWidth="2.2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function RiderIcon() {
  // small ride icon for the page header (the design uses a pink ride-icon)
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M3 17h2l1-3 4 1 1 2h9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="6" cy="19" r="2" fill="currentColor" />
      <circle cx="18" cy="19" r="2" fill="currentColor" />
    </svg>
  )
}
