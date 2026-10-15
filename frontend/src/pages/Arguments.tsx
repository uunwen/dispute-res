import { useEffect, useMemo, useState } from 'react'
import { api, type AgentMessage, type Dispute } from '../api'
import StatusBadge from '../components/StatusBadge'
import { DriverMascot, RiderMascot } from '../components/DebateMascots'
import { categoryLabel, disputeStatusVariant } from '../lib/status'
import { extractRuleIdsFromMessage, ruleLabel } from '../lib/argumentRules'

interface ArgumentsProps {
  disputeId: number
  onBack: () => void
}

/* ============================================================
 * Screen 7 — Agent Arguments (side-by-side)
 * ============================================================
 *
 * Two columns, one per advocate:
 *   - Rider Advocate  (pink-tinted header, Rider mascot)
 *   - Driver Advocate (blue-tinted header, Driver mascot)
 *
 * Each column has two tabs:
 *   - "Arguments (n)"  — every brief the advocate produced, in
 *     order. R1 is always the opening. R2 only appears if the
 *     backend produced a rebuttal round for that side.
 *   - "Evidence (n)"   — the evidence_ids the advocate cited
 *     across all of their claims (deduplicated).
 *
 * Every argument card shows:
 *   - the round label  (R1, R2)
 *   - the round title  (Opening argument / Rebuttal)
 *   - the brief text   (collapses to 5 lines + "Show more")
 *   - the rule IDs cited (chips) extracted with a regex that
 *     matches the real `source#section` / snake_case format
 *     used by the project, not the placeholder IDs in the
 *     design image.
 *
 * No fake data. If the advocate only opened and never rebutted,
 * we only show R1.
 */

type Side = 'rider' | 'driver'

interface ArgumentRound {
  /** Stable id derived from the underlying message id. */
  id: string
  /** The side the argument is on. */
  side: Side
  /** 1-based round index for this side (R1, R2, ...). */
  roundIndex: number
  /** "Opening argument" or "Rebuttal". */
  title: string
  /** Full brief text. */
  text: string
  /** Rule IDs cited by this round, in first-seen order. */
  ruleIds: string[]
  /** Evidence IDs cited by this round, in first-seen order. */
  evidenceIds: string[]
  /** The original message, for the "View Full Transcript"-style header. */
  message: AgentMessage
}

interface ColumnData {
  /** All argument rounds for this side, ordered. */
  rounds: ArgumentRound[]
  /** All evidence IDs cited by this side, deduplicated. */
  evidenceIds: string[]
  /** Did the advocate open? (controls "R1 — Opening argument" copy) */
  hasOpening: boolean
  /** Did the advocate rebut? (controls whether R2 is shown at all) */
  hasRebuttal: boolean
}

/* Line-clamp for the "Show more" toggle is set in Arguments.css
 * (5 lines). Keeping the count in one place makes design tweaks easy. */

function sideFromSender(sender: string): Side | null {
  if (sender === 'RiderAdvocate') return 'rider'
  if (sender === 'DriverAdvocate') return 'driver'
  return null
}

function titleFor(round: string | undefined): string {
  return round === 'rebuttal' ? 'Rebuttal' : 'Opening argument'
}

function dedupeInOrder(ids: string[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const id of ids) {
    if (!id || seen.has(id)) continue
    seen.add(id)
    out.push(id)
  }
  return out
}

function readBriefField(content: Record<string, unknown>, key: string): string {
  const brief = (content.brief ?? {}) as Record<string, unknown>
  const v = brief[key]
  return typeof v === 'string' ? v : ''
}

function readPolicyIds(content: Record<string, unknown>): string[] {
  const brief = (content.brief ?? {}) as Record<string, unknown>
  const claims = Array.isArray(brief.claims) ? brief.claims : []
  const ids: string[] = []
  for (const c of claims) {
    if (!c || typeof c !== 'object') continue
    const polIds = (c as Record<string, unknown>).policy_section_ids
    if (Array.isArray(polIds)) {
      for (const id of polIds) if (typeof id === 'string') ids.push(id)
    }
  }
  /* Then back-fill from the helper (handles the rare case where
   * an LLM puts a section id directly in the summary text but
   * forgot to put it on the claim). */
  ids.push(...extractRuleIdsFromMessage({ content } as AgentMessage))
  return dedupeInOrder(ids)
}

function readEvidenceIds(content: Record<string, unknown>): string[] {
  const brief = (content.brief ?? {}) as Record<string, unknown>
  const claims = Array.isArray(brief.claims) ? brief.claims : []
  const ids: string[] = []
  for (const c of claims) {
    if (!c || typeof c !== 'object') continue
    const ev = (c as Record<string, unknown>).evidence_ids
    if (Array.isArray(ev)) {
      for (const id of ev) if (typeof id === 'string') ids.push(id)
    }
  }
  return dedupeInOrder(ids)
}

function buildColumn(messages: AgentMessage[], side: Side): ColumnData {
  const rounds: ArgumentRound[] = []
  let openingCount = 0
  let rebuttalCount = 0

  for (const m of messages) {
    if (m.message_type !== 'case_brief') continue
    if (sideFromSender(m.sender) !== side) continue

    const content = (m.content ?? {}) as Record<string, unknown>
    const round = (content.round as string | undefined) ?? 'opening'
    const isRebuttal = round === 'rebuttal'
    if (isRebuttal) rebuttalCount += 1
    else openingCount += 1

    const text = readBriefField(content, 'argument_summary')
    const ruleIds = readPolicyIds(content)
    const evidenceIds = readEvidenceIds(content)

    /* roundIndex is 1-based per side, in chronological order. */
    const roundIndex = rounds.length + 1

    rounds.push({
      id: `m-${m.id}`,
      side,
      roundIndex,
      title: titleFor(round),
      text,
      ruleIds,
      evidenceIds,
      message: m,
    })
  }

  return {
    rounds,
    evidenceIds: dedupeInOrder(rounds.flatMap((r) => r.evidenceIds)),
    hasOpening: openingCount > 0,
    hasRebuttal: rebuttalCount > 0,
  }
}

export default function Arguments({ disputeId, onBack }: ArgumentsProps) {
  const [dispute, setDispute] = useState<Dispute | null>(null)
  const [messages, setMessages] = useState<AgentMessage[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([api.getDispute(disputeId), api.getMessages(disputeId)])
      .then(([d, msgs]) => {
        if (cancelled) return
        setDispute(d)
        setMessages(msgs)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load arguments.')
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [disputeId])

  const rider = useMemo<ColumnData>(() => buildColumn(messages ?? [], 'rider'), [messages])
  const driver = useMemo<ColumnData>(() => buildColumn(messages ?? [], 'driver'), [messages])

  return (
    <div className="rp-page rp-arguments">
      <div className="rp-arguments__header">
        <div className="rp-arguments__title">
          <h1>
            Dispute #{disputeId}
            {dispute && (
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
            )}
          </h1>
          <p>
            {dispute ? categoryLabel(dispute.category) : 'Loading…'}
            {dispute && dispute.claim_text ? ` · ${dispute.claim_text}` : null}
          </p>
        </div>
        <button type="button" className="rp-btn rp-btn--ghost" onClick={onBack}>
          ← Back
        </button>
      </div>

      {error ? (
        <div className="rp-card rp-card--padded">
          <strong>Couldn't load the arguments.</strong>
          <p className="rp-muted">{error}</p>
        </div>
      ) : loading ? (
        <div className="rp-card rp-card--padded">Loading arguments…</div>
      ) : (
        <div className="rp-arguments__columns">
          <AdvocateColumn side="rider" data={rider} />
          <AdvocateColumn side="driver" data={driver} />
        </div>
      )}
    </div>
  )
}

/* ============================================================
 * One advocate column (header + tabs)
 * ============================================================ */

interface ColumnProps {
  side: Side
  data: ColumnData
}

function AdvocateColumn({ side, data }: ColumnProps) {
  const initialTab: 'arguments' | 'evidence' = 'arguments'
  const [tab, setTab] = useState<'arguments' | 'evidence'>(initialTab)

  const isRider = side === 'rider'
  const accent = isRider ? 'rider' : 'driver'
  const Mascot = isRider ? RiderMascot : DriverMascot
  const advocateName = isRider ? 'Rider Advocate' : 'Driver Advocate'
  const subtitle = isRider
    ? "Presents the rider's case"
    : "Presents the driver's defense"
  const argumentCount = data.rounds.length
  const evidenceCount = data.evidenceIds.length

  return (
    <section className={`rp-arguments__column rp-arguments__column--${accent}`}>
      <header className="rp-arguments__column-head">
        <div className="rp-arguments__column-head-text">
          <h2>{advocateName}</h2>
          <p>{subtitle}</p>
        </div>
        <div className="rp-arguments__column-head-mascot" aria-hidden>
          <Mascot size={84} />
        </div>
      </header>

      <div className="rp-arguments__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'arguments'}
          className={`rp-arguments__tab ${tab === 'arguments' ? 'is-active' : ''}`}
          onClick={() => setTab('arguments')}
        >
          Arguments <span className="rp-arguments__tab-count">({argumentCount})</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'evidence'}
          className={`rp-arguments__tab ${tab === 'evidence' ? 'is-active' : ''}`}
          onClick={() => setTab('evidence')}
        >
          Evidence <span className="rp-arguments__tab-count">({evidenceCount})</span>
        </button>
      </div>

      {tab === 'arguments' ? (
        <ArgumentsTab data={data} />
      ) : (
        <EvidenceTab evidenceIds={data.evidenceIds} />
      )}
    </section>
  )
}

/* ============================================================
 * Arguments tab
 * ============================================================ */

function ArgumentsTab({ data }: { data: ColumnData }) {
  if (data.rounds.length === 0) {
    return (
      <div className="rp-arguments__empty">
        This advocate has not filed an argument yet.
      </div>
    )
  }
  return (
    <div className="rp-arguments__list">
      {data.rounds.map((r) => (
        <ArgumentCard key={r.id} round={r} />
      ))}
    </div>
  )
}

function ArgumentCard({ round }: { round: ArgumentRound }) {
  const [expanded, setExpanded] = useState(false)
  const accent = round.side === 'rider' ? 'rider' : 'driver'
  return (
    <article className={`rp-argument-card rp-argument-card--${accent}`}>
      <div className="rp-argument-card__head">
        <span className={`rp-argument-card__round rp-argument-card__round--${accent}`}>
          R{round.roundIndex}
        </span>
        <span className="rp-argument-card__title">{round.title}</span>
      </div>

      <div
        className={`rp-argument-card__body ${expanded ? 'is-expanded' : ''}`}
        /* `body` does the line-clamp. Toggling `is-expanded` removes it. */
      >
        {round.text ? (
          <p>{round.text}</p>
        ) : (
          <p className="rp-argument-card__placeholder">No brief produced (LLM unavailable).</p>
        )}
      </div>

      {round.text && round.text.length > 200 && (
        <button
          type="button"
          className="rp-argument-card__toggle"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}

      {round.ruleIds.length > 0 && (
        <div className="rp-argument-card__chips" aria-label="Rules cited">
          {round.ruleIds.map((id) => (
            <span
              key={id}
              className={`rp-argument-card__chip rp-argument-card__chip--${accent}`}
              title={ruleLabel(id)}
            >
              {id}
            </span>
          ))}
        </div>
      )}
    </article>
  )
}

/* ============================================================
 * Evidence tab — flat list of every evidence_id this advocate cited
 * ============================================================ */

function EvidenceTab({ evidenceIds }: { evidenceIds: string[] }) {
  if (evidenceIds.length === 0) {
    return (
      <div className="rp-arguments__empty">
        No evidence was cited in this advocate's arguments.
      </div>
    )
  }
  return (
    <ul className="rp-arguments__evidence-list">
      {evidenceIds.map((id) => (
        <li key={id} className="rp-arguments__evidence-item">
          <span className="rp-arguments__evidence-id">{id}</span>
        </li>
      ))}
    </ul>
  )
}
