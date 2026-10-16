import { useEffect, useMemo, useState } from 'react'
import { api, type Dispute, type DisputeReview, type Ruling } from '../api'
import StatusBadge from '../components/StatusBadge'
import Modal from '../components/Modal'
import Toast from '../components/Toast'
import { JudgeMascot } from '../components/DebateMascots'
import { CheckIcon, UploadIcon } from '../components/icons'
import { categoryLabel, outcomeLabel } from '../lib/status'
import { getRuleMeta } from '../lib/rules'
import { deriveFlags, type RulingFlag } from '../components/RulingFlags'

interface RulingProps {
  disputeId: number
  onBack: () => void
  onSeeEvidence?: (id: number) => void
}

/* ============================================================
 * Screen 8 (Final Ruling — resolved) and Screen 9 (No Clear
 * Conclusion — escalated). The page chooses which view to render
 * based on `ruling.escalated` and the dispute's provisional status.
 *
 * All data comes through the data layer (api.ts), so the page works
 * identically in real and sample-data mode. Every field read here
 * tolerates a null / missing value.
 * ============================================================ */

type ModalKind =
  | { kind: 'none' }
  | { kind: 'processRefund' }
  | { kind: 'appeal' }
  | { kind: 'viewReport' }
  | { kind: 'assignReviewer' }
  | { kind: 'addEvidence' }
  | { kind: 'message'; who: 'rider' | 'driver' }

export default function RulingScreen({ disputeId, onBack, onSeeEvidence }: RulingProps) {
  const [dispute, setDispute] = useState<Dispute | null>(null)
  const [ruling, setRuling] = useState<Ruling | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [modal, setModal] = useState<ModalKind>({ kind: 'none' })
  const [toast, setToast] = useState<{ message: string; variant: 'success' | 'info' | 'error' } | null>(null)
  const [assignedReviewer, setAssignedReviewer] = useState<string | null>(null)
  const [appealSubmitted, setAppealSubmitted] = useState(false)
  const [refundProcessed, setRefundProcessed] = useState(false)
  const [reviews, setReviews] = useState<DisputeReview[]>([])

  useEffect(() => {
    let cancelled = false
    Promise.all([api.getDispute(disputeId), api.getRuling(disputeId)])
      .then(([d, r]) => {
        if (cancelled) return
        setDispute(d)
        setRuling(r)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load ruling.')
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [disputeId])

  useEffect(() => {
    let cancelled = false
    api
      .listReviews(disputeId)
      .then((items) => {
        if (cancelled) return
        setReviews(items)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [disputeId])

  const isEscalated = !!ruling?.escalated

  /* ---------- derived data (all null-safe) ---------- */

  const confidencePct = ruling ? Math.round(ruling.confidence * 100) : null

  const flags = useMemo<RulingFlag[]>(
    () => (ruling ? deriveFlags({ dispute, ruling }) : []),
    [dispute, ruling],
  )

  const citedRuleIds = useMemo<string[]>(() => {
    if (!ruling) return []
    const ro = (ruling.rule_outcome ?? {}) as Record<string, unknown>
    const rule = (ro.rule ?? {}) as Record<string, unknown>
    const matched = rule.matched_rule_ids
    if (Array.isArray(matched)) return matched.filter((x): x is string => typeof x === 'string')
    return []
  }, [ruling])

  const decidingPolicySections = useMemo<string[]>(() => {
    if (!ruling) return []
    const ro = (ruling.rule_outcome ?? {}) as Record<string, unknown>
    const v = ro.deciding_policy_sections
    if (Array.isArray(v)) return v.filter((x): x is string => typeof x === 'string')
    return []
  }, [ruling])

  const evidenceIds = useMemo<string[]>(
    () => (ruling?.evidence_ids ?? []).filter((x): x is string => typeof x === 'string'),
    [ruling],
  )

  const riderMessage = useMemo<string>(() => {
    if (!ruling) return ''
    const ro = (ruling.rule_outcome ?? {}) as Record<string, unknown>
    const v = ro.rider_explanation
    return typeof v === 'string' ? v : ''
  }, [ruling])

  const driverMessage = useMemo<string>(() => {
    if (!ruling) return ''
    const ro = (ruling.rule_outcome ?? {}) as Record<string, unknown>
    const v = ro.driver_explanation
    return typeof v === 'string' ? v : ''
  }, [ruling])

  /* ---------- action handlers ---------- */

  function showToast(message: string, variant: 'success' | 'info' | 'error' = 'success') {
    setToast({ message, variant })
    // Auto-dismiss after 3 seconds.
    window.setTimeout(() => {
      setToast((t) => (t?.message === message ? null : t))
    }, 3000)
  }

  async function refreshReviews() {
    try {
      setReviews(await api.listReviews(disputeId))
    } catch {
      /* the audit list is best-effort */
    }
  }

  async function processRefund() {
    setModal({ kind: 'none' })
    try {
      await api.reviewDispute(disputeId, 'confirm', 'Refund processed by ops')
      setRefundProcessed(true)
      await refreshReviews()
      showToast('Refund confirmed and recorded')
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to record action', 'error')
    }
  }

  async function submitAppeal(name: string, reason: string) {
    setModal({ kind: 'none' })
    try {
      const who = name.trim() || 'The rider'
      await api.reviewDispute(disputeId, 'appeal', reason.trim() ? `${who}: ${reason.trim()}` : who)
      setAppealSubmitted(true)
      await refreshReviews()
      showToast(`${who}'s appeal has been submitted for review`)
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to submit appeal', 'error')
    }
  }

  async function assignReviewer(name: string) {
    setModal({ kind: 'none' })
    try {
      const who = name.trim() || 'Human reviewer'
      await api.reviewDispute(disputeId, 'assign', `Assigned to ${who}`)
      setAssignedReviewer(who)
      await refreshReviews()
      showToast(`Assigned to ${who}`, 'info')
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Failed to assign reviewer', 'error')
    }
  }

  /* ---------- rendering ---------- */

  if (loading) {
    return (
      <div className="rp-page">
        <div className="rp-card rp-card--padded">Loading ruling…</div>
      </div>
    )
  }

  if (error || !ruling) {
    return (
      <div className="rp-page">
        <div className="rp-page-header">
          <div>
            <h1>Dispute #{disputeId} · Final Ruling</h1>
            <p>The judge has not yet delivered a ruling for this dispute.</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {onSeeEvidence && (
              <button
                type="button"
                className="rp-btn rp-btn--ghost"
                onClick={() => onSeeEvidence(disputeId)}
              >
                View Evidence
              </button>
            )}
            <button type="button" className="rp-btn rp-btn--ghost" onClick={onBack}>
              ← Back
            </button>
          </div>
        </div>
        <div className="rp-card rp-card--padded">
          <strong>Couldn't load the ruling.</strong>
          <p className="rp-muted">{error ?? 'No ruling data was returned.'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="rp-page rp-ruling">
      {/* Header */}
      <div className="rp-ruling__header">
        <div className="rp-ruling__title">
          <span className="rp-ruling__brandmark" aria-label="ryde">ryde</span>
          <div>
            <h1>
              Dispute #{disputeId}
              {isEscalated ? (
                <StatusBadge variant="escalated" label="Escalated" />
              ) : (
                <StatusBadge variant="resolved" label="Resolved" />
              )}
              {dispute && (
                <span className="rp-ruling__category">· {categoryLabel(dispute.category)}</span>
              )}
            </h1>
            {dispute && <p>{dispute.claim_text}</p>}
          </div>
        </div>
        <div className="rp-ruling__header-actions">
          {onSeeEvidence && (
            <button
              type="button"
              className="rp-btn rp-btn--ghost"
              onClick={() => onSeeEvidence(disputeId)}
            >
              View Evidence
            </button>
          )}
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onBack}>
            ← Back
          </button>
        </div>
      </div>

      {isEscalated ? (
        <EscalatedView
          ruling={ruling}
          dispute={dispute}
          confidencePct={confidencePct}
          flags={flags}
          decidingPolicySections={decidingPolicySections}
          evidenceIds={evidenceIds}
          assignedReviewer={assignedReviewer}
          onAssignReviewer={() => setModal({ kind: 'assignReviewer' })}
          onAddEvidence={() => setModal({ kind: 'addEvidence' })}
        />
      ) : (
        <ResolvedView
          ruling={ruling}
          confidencePct={confidencePct}
          flags={flags}
          citedRuleIds={citedRuleIds}
          decidingPolicySections={decidingPolicySections}
          evidenceIds={evidenceIds}
          riderMessage={riderMessage}
          driverMessage={driverMessage}
          refundProcessed={refundProcessed}
          appealSubmitted={appealSubmitted}
          onProcessRefund={() => setModal({ kind: 'processRefund' })}
          onAppeal={() => setModal({ kind: 'appeal' })}
          onViewReport={() => setModal({ kind: 'viewReport' })}
          onShowMessage={(who) => setModal({ kind: 'message', who })}
        />
      )}

      {reviews.length > 0 && (
        <section className="rp-ruling__section">
          <h3>Review actions</h3>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {reviews.map((r) => (
              <li
                key={r.id}
                style={{
                  display: 'flex',
                  gap: 8,
                  alignItems: 'baseline',
                  padding: '6px 0',
                  borderBottom: '1px solid var(--rp-border)',
                }}
              >
                <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{r.action}</span>
                {r.note && <span className="rp-muted">{r.note}</span>}
                <span className="rp-muted rp-small" style={{ marginLeft: 'auto' }}>
                  {formatDate(r.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Modals */}
      {modal.kind === 'processRefund' && (
        <ProcessRefundModal
          ruling={ruling}
          onCancel={() => setModal({ kind: 'none' })}
          onConfirm={processRefund}
        />
      )}
      {modal.kind === 'appeal' && (
        <AppealModal
          onCancel={() => setModal({ kind: 'none' })}
          onSubmit={submitAppeal}
        />
      )}
      {modal.kind === 'viewReport' && (
        <ViewReportModal
          ruling={ruling}
          dispute={dispute}
          flags={flags}
          citedRuleIds={citedRuleIds}
          evidenceIds={evidenceIds}
          riderMessage={riderMessage}
          driverMessage={driverMessage}
          onClose={() => setModal({ kind: 'none' })}
        />
      )}
      {modal.kind === 'assignReviewer' && (
        <AssignReviewerModal
          onCancel={() => setModal({ kind: 'none' })}
          onAssign={assignReviewer}
        />
      )}
      {modal.kind === 'addEvidence' && (
        <AddEvidenceModal
          onCancel={() => setModal({ kind: 'none' })}
          onSubmit={() => {
            setModal({ kind: 'none' })
            showToast('Evidence added to the dispute', 'info')
          }}
        />
      )}
      {modal.kind === 'message' && (
        <MessageModal
          who={modal.who}
          text={modal.who === 'rider' ? riderMessage : driverMessage}
          onClose={() => setModal({ kind: 'none' })}
        />
      )}

      <Toast
        message={toast?.message ?? null}
        variant={toast?.variant}
        onClose={() => setToast(null)}
      />
    </div>
  )
}

/* ============================================================
 * Resolved view (Screen 8)
 * ============================================================ */

interface ResolvedViewProps {
  ruling: Ruling
  confidencePct: number | null
  flags: RulingFlag[]
  citedRuleIds: string[]
  decidingPolicySections: string[]
  evidenceIds: string[]
  riderMessage: string
  driverMessage: string
  refundProcessed: boolean
  appealSubmitted: boolean
  onProcessRefund: () => void
  onAppeal: () => void
  onViewReport: () => void
  onShowMessage: (who: 'rider' | 'driver') => void
}

function ResolvedView(props: ResolvedViewProps) {
  const {
    ruling,
    confidencePct,
    flags,
    citedRuleIds,
    decidingPolicySections,
    evidenceIds,
    riderMessage,
    driverMessage,
    refundProcessed,
    appealSubmitted,
    onProcessRefund,
    onAppeal,
    onViewReport,
    onShowMessage,
  } = props

  const headline = headlineFor(ruling.outcome)
  const summaryLine = summaryLineFor(ruling)

  return (
    <div className="rp-ruling__layout">
      {/* Main column */}
      <div className="rp-ruling__main">
        <section className="rp-ruling__hero">
          <div className="rp-ruling__hero-icon" aria-hidden>
            <span className="rp-ruling__check">
              <CheckIcon size={36} strokeWidth={3} />
            </span>
            <JudgeMascot size={140} className="rp-ruling__mascot" />
          </div>
          <h2 className="rp-ruling__outcome">{headline}</h2>
          {confidencePct !== null && (
            <span className="rp-ruling__confidence">Confidence {confidencePct}%</span>
          )}
          <p className="rp-ruling__summary">{summaryLine}</p>
        </section>

        <section className="rp-ruling__section">
          <h3>Reasoning</h3>
          <p className="rp-ruling__reasoning">
            {ruling.reasoning || 'No reasoning was recorded for this ruling.'}
          </p>
        </section>

        {flags.length > 0 && (
          <section className="rp-ruling__section">
            <h3>Flags</h3>
            <ul className="rp-ruling__flags" aria-label="Flags raised by this ruling">
              {flags.map((f) => (
                <li key={f.key} className={`rp-ruling__flag rp-ruling__flag--${f.tone}`}>
                  <span className="rp-ruling__flag-dot" aria-hidden />
                  {f.label}
                </li>
              ))}
            </ul>
          </section>
        )}

        {(riderMessage || driverMessage) && (
          <section className="rp-ruling__section">
            <h3>Messages</h3>
            <div className="rp-ruling__messages">
              {riderMessage && (
                <button
                  type="button"
                  className="rp-ruling__message-card rp-ruling__message-card--rider"
                  onClick={() => onShowMessage('rider')}
                >
                  <span className="rp-ruling__message-tag">To rider</span>
                  <span className="rp-ruling__message-preview">
                    {truncate(riderMessage, 120)}
                  </span>
                  <span className="rp-ruling__message-cta">View full message →</span>
                </button>
              )}
              {driverMessage && (
                <button
                  type="button"
                  className="rp-ruling__message-card rp-ruling__message-card--driver"
                  onClick={() => onShowMessage('driver')}
                >
                  <span className="rp-ruling__message-tag">To driver</span>
                  <span className="rp-ruling__message-preview">
                    {truncate(driverMessage, 120)}
                  </span>
                  <span className="rp-ruling__message-cta">View full message →</span>
                </button>
              )}
            </div>
          </section>
        )}

        <section className="rp-ruling__actions" aria-label="Ruling actions">
          <button
            type="button"
            className="rp-btn rp-btn--primary"
            onClick={onProcessRefund}
            disabled={refundProcessed}
          >
            {refundProcessed ? 'Refund recorded' : 'Process Refund'}
          </button>
          <button
            type="button"
            className="rp-btn rp-btn--ghost"
            onClick={onAppeal}
            disabled={appealSubmitted}
          >
            {appealSubmitted ? 'Appeal submitted' : 'Appeal Decision'}
          </button>
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onViewReport}>
            View Report
          </button>
        </section>
      </div>

      {/* Right column */}
      <aside className="rp-ruling__side">
        <PolicyAppliedCard
          citedRuleIds={citedRuleIds}
          decidingPolicySections={decidingPolicySections}
        />
        <PrecedentsCard
          citedRuleIds={citedRuleIds}
          decidingPolicySections={decidingPolicySections}
        />
        <EvidenceUsedCard evidenceIds={evidenceIds} />
      </aside>
    </div>
  )
}

/* ============================================================
 * Escalated view (Screen 9)
 * ============================================================ */

interface EscalatedViewProps {
  ruling: Ruling
  dispute: Dispute | null
  confidencePct: number | null
  flags: RulingFlag[]
  decidingPolicySections: string[]
  evidenceIds: string[]
  assignedReviewer: string | null
  onAssignReviewer: () => void
  onAddEvidence: () => void
}

function EscalatedView(props: EscalatedViewProps) {
  const {
    ruling,
    confidencePct,
    flags,
    decidingPolicySections,
    evidenceIds,
    assignedReviewer,
    onAssignReviewer,
    onAddEvidence,
  } = props

  // Use the rule outcome as the provisional outcome if present.
  const ro = (ruling.rule_outcome ?? {}) as Record<string, unknown>
  const ruleSub = (ro.rule ?? {}) as Record<string, unknown>
  const provisionalOutcome =
    typeof ruleSub.outcome === 'string' && ruleSub.outcome.length > 0
      ? String(ruleSub.outcome)
      : null
  const provisionalRefund = typeof ruleSub.refund_amount === 'number' ? ruleSub.refund_amount : null

  // Reasons for escalation — combine escalation_reason (comma-list
  // from the backend) with the cited policy sections.
  const escalationReasonText =
    ruling.human_review_summary && typeof ruling.human_review_summary === 'object'
      ? (ruling.human_review_summary as unknown as Record<string, unknown>).escalation_reason
      : null
  const reasonBlob = typeof escalationReasonText === 'string' ? escalationReasonText : ''
  const reasonBullets = parseReasonBlob(reasonBlob, decidingPolicySections)

  return (
    <div className="rp-ruling__layout">
      <div className="rp-ruling__main">
        <section className="rp-ruling__hero rp-ruling__hero--escalated">
          <div className="rp-ruling__hero-icon" aria-hidden>
            <JudgeMascot size={140} className="rp-ruling__mascot" />
          </div>
          <h2 className="rp-ruling__outcome">ESCALATED TO HUMAN REVIEW</h2>
          {confidencePct !== null && (
            <span className="rp-ruling__confidence rp-ruling__confidence--escalated">
              Confidence {confidencePct}%
            </span>
          )}
          <p className="rp-ruling__summary">
            Unable to reach a conclusive decision based on the available evidence.
          </p>
          {assignedReviewer && (
            <p className="rp-ruling__assigned">
              <strong>Assigned to:</strong> {assignedReviewer}
            </p>
          )}
        </section>

        <section className="rp-ruling__section">
          <h3>Reason for escalation</h3>
          {reasonBullets.length > 0 ? (
            <ul className="rp-ruling__bullets">
              {reasonBullets.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          ) : (
            <p className="rp-muted">No specific reason was recorded.</p>
          )}
        </section>

        {provisionalOutcome && (
          <section className="rp-ruling__section">
            <h3>Provisional outcome</h3>
            <p className="rp-ruling__provisional">
              <strong>{outcomeLabel(provisionalOutcome)}</strong>
              {provisionalRefund !== null && provisionalRefund > 0 && (
                <>
                  {' '}
                  — {money(provisionalRefund)} would be refunded
                </>
              )}
              . A human reviewer will confirm or override this decision.
            </p>
          </section>
        )}

        {flags.length > 0 && (
          <section className="rp-ruling__section">
            <h3>Flags</h3>
            <ul className="rp-ruling__flags" aria-label="Flags raised by this ruling">
              {flags.map((f) => (
                <li key={f.key} className={`rp-ruling__flag rp-ruling__flag--${f.tone}`}>
                  <span className="rp-ruling__flag-dot" aria-hidden />
                  {f.label}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="rp-ruling__actions" aria-label="Escalation actions">
          <button
            type="button"
            className="rp-btn rp-btn--primary"
            onClick={onAssignReviewer}
            disabled={!!assignedReviewer}
          >
            {assignedReviewer ? 'Assigned' : 'Assign to Human Reviewer'}
          </button>
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onAddEvidence}>
            <UploadIcon size={16} strokeWidth={1.8} />
            Add Evidence
          </button>
        </section>
      </div>

      <aside className="rp-ruling__side">
        <EscalationSummaryCard ruling={ruling} />
        <EvidenceUsedCard evidenceIds={evidenceIds} />
      </aside>
    </div>
  )
}

/* ============================================================
 * Right-rail cards
 * ============================================================ */

function PolicyAppliedCard({
  citedRuleIds,
  decidingPolicySections,
}: {
  citedRuleIds: string[]
  decidingPolicySections: string[]
}) {
  // Prefer the canonical rule IDs (matched_rule_ids) since they map
  // to the static rules.ts metadata. The "source#section" policy
  // sections are surfaced separately as a sub-row.
  const rules = citedRuleIds
    .map((id) => ({ id, meta: getRuleMeta(id) }))
    .filter((r) => !!r.meta)

  return (
    <section className="rp-ruling__side-card">
      <h3>Policies Applied</h3>
      {rules.length === 0 ? (
        <p className="rp-muted">No policies were cited by the judge.</p>
      ) : (
        <ul className="rp-ruling__rule-list">
          {rules.map(({ id, meta }) => (
            <li key={id} className="rp-ruling__rule">
              <span className="rp-ruling__rule-id">{id}</span>
              <span className="rp-ruling__rule-title">{meta!.title}</span>
            </li>
          ))}
        </ul>
      )}
      {decidingPolicySections.length > 0 && (
        <div className="rp-ruling__policy-sections">
          <span className="rp-ruling__subhead">Policy sections</span>
          <ul className="rp-ruling__chip-list">
            {decidingPolicySections.map((s) => (
              <li key={s} className="rp-ruling__chip">
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

/**
 * Precedents are NOT a backend concept. We surface a small card
 * anyway, populated from the cited rule ids and policy sections, so
 * the page reads consistently with the design. If the backend had a
 * real "precedents" field on the ruling, we'd read it from there.
 */
function PrecedentsCard({
  citedRuleIds,
  decidingPolicySections,
}: {
  citedRuleIds: string[]
  decidingPolicySections: string[]
}) {
  // Best-effort: if there are cited rule ids, treat them as the
  // precedents the system drew on. If both lists are empty, hide.
  const items: { id: string; title: string }[] = []
  for (const id of citedRuleIds) {
    const meta = getRuleMeta(id)
    if (meta) items.push({ id, title: meta.title })
  }
  if (items.length === 0 && decidingPolicySections.length === 0) return null

  return (
    <section className="rp-ruling__side-card">
      <h3>Precedents Used</h3>
      {items.length === 0 ? (
        <p className="rp-muted">No prior decisions were cited.</p>
      ) : (
        <ul className="rp-ruling__rule-list">
          {items.map((it) => (
            <li key={it.id} className="rp-ruling__rule">
              <span className="rp-ruling__rule-id">{it.id}</span>
              <span className="rp-ruling__rule-title">{it.title}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function EvidenceUsedCard({ evidenceIds }: { evidenceIds: string[] }) {
  return (
    <section className="rp-ruling__side-card">
      <h3>Evidence Used</h3>
      {evidenceIds.length === 0 ? (
        <p className="rp-muted">No evidence was cited by the judge.</p>
      ) : (
        <ul className="rp-ruling__chip-list" aria-label="Evidence identifiers">
          {evidenceIds.map((id) => (
            <li key={id} className="rp-ruling__chip">
              {id}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function EscalationSummaryCard({ ruling }: { ruling: Ruling }) {
  const h = ruling.human_review_summary
  if (!h || typeof h !== 'object') {
    return (
      <section className="rp-ruling__side-card">
        <h3>Escalation summary</h3>
        <p className="rp-muted">No escalation summary is available.</p>
      </section>
    )
  }
  const summary = h as unknown as Record<string, unknown>
  return (
    <section className="rp-ruling__side-card">
      <h3>Escalation summary</h3>
      {typeof summary.dispute === 'string' && summary.dispute && (
        <p className="rp-ruling__side-line">
          <strong>Dispute:</strong> {summary.dispute}
        </p>
      )}
      {typeof summary.ruling === 'string' && summary.ruling && (
        <p className="rp-ruling__side-line">
          <strong>Ruling:</strong> {summary.ruling}
        </p>
      )}
      {typeof summary.escalation_reason === 'string' && summary.escalation_reason && (
        <p className="rp-ruling__side-line">
          <strong>Reason:</strong> {summary.escalation_reason}
        </p>
      )}
      {typeof summary.recommended_action === 'string' && summary.recommended_action && (
        <p className="rp-ruling__side-line">
          <strong>Recommended:</strong> {summary.recommended_action}
        </p>
      )}
    </section>
  )
}

/* ============================================================
 * Modals
 * ============================================================ */

function ProcessRefundModal({
  ruling,
  onCancel,
  onConfirm,
}: {
  ruling: Ruling
  onCancel: () => void
  onConfirm: () => void
}) {
  const refundText =
    ruling.outcome === 'no_refund'
      ? 'No refund will be issued — the charge stands.'
      : `${money(ruling.refund_amount)} will be refunded to the rider.`
  return (
    <Modal
      open
      title="Confirm refund"
      onClose={onCancel}
      size="sm"
      footer={
        <>
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="rp-btn rp-btn--primary" onClick={onConfirm}>
            Confirm refund
          </button>
        </>
      }
    >
      <p>{refundText}</p>
      <p className="rp-muted">This action will be recorded and a notification sent to the rider.</p>
    </Modal>
  )
}

function AppealModal({
  onCancel,
  onSubmit,
}: {
  onCancel: () => void
  onSubmit: (name: string, reason: string) => void
}) {
  const [name, setName] = useState('')
  const [reason, setReason] = useState('')
  const canSubmit = reason.trim().length > 0
  return (
    <Modal
      open
      title="Appeal this decision"
      onClose={onCancel}
      size="md"
      footer={
        <>
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onCancel}>
            Cancel
          </button>
          <button
            type="button"
            className="rp-btn rp-btn--primary"
            onClick={() => onSubmit(name, reason)}
            disabled={!canSubmit}
          >
            Submit appeal
          </button>
        </>
      }
    >
      <div className="rp-field">
        <span>Your name</span>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Rider or authorised representative"
        />
      </div>
      <div className="rp-field">
        <span>Reason for appeal</span>
        <textarea
          rows={5}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Briefly describe why this decision should be reviewed."
        />
      </div>
    </Modal>
  )
}

function ViewReportModal({
  ruling,
  dispute,
  flags,
  citedRuleIds,
  evidenceIds,
  riderMessage,
  driverMessage,
  onClose,
}: {
  ruling: Ruling
  dispute: Dispute | null
  flags: RulingFlag[]
  citedRuleIds: string[]
  evidenceIds: string[]
  riderMessage: string
  driverMessage: string
  onClose: () => void
}) {
  return (
    <Modal
      open
      title="Ruling report"
      onClose={onClose}
      size="lg"
      footer={
        <>
          <button type="button" className="rp-btn rp-btn--ghost" onClick={() => window.print()}>
            Print
          </button>
          <button type="button" className="rp-btn rp-btn--primary" onClick={onClose}>
            Close
          </button>
        </>
      }
    >
      <div className="rp-ruling__report">
        <header className="rp-ruling__report-head">
          <h2>Dispute #{ruling.dispute_id} — Final Ruling</h2>
          <p className="rp-muted">
            {dispute ? categoryLabel(dispute.category) : 'Dispute'} · Filed by user {dispute?.filed_by ?? '—'}
          </p>
        </header>

        <dl className="rp-ruling__report-grid">
          <dt>Outcome</dt>
          <dd>{outcomeLabel(ruling.outcome)}</dd>
          <dt>Refund</dt>
          <dd>{money(ruling.refund_amount)}</dd>
          <dt>Confidence</dt>
          <dd>{Math.round(ruling.confidence * 100)}%</dd>
          <dt>Escalated</dt>
          <dd>{ruling.escalated ? 'Yes' : 'No'}</dd>
          <dt>LLM degraded</dt>
          <dd>{ruling.llm_degraded ? 'Yes' : 'No'}</dd>
          <dt>Created</dt>
          <dd>{formatDate(ruling.created_at)}</dd>
        </dl>

        <h3>Reasoning</h3>
        <p>{ruling.reasoning || '—'}</p>

        {citedRuleIds.length > 0 && (
          <>
            <h3>Policies applied</h3>
            <ul className="rp-ruling__rule-list">
              {citedRuleIds.map((id) => {
                const meta = getRuleMeta(id)
                return (
                  <li key={id} className="rp-ruling__rule">
                    <span className="rp-ruling__rule-id">{id}</span>
                    <span className="rp-ruling__rule-title">{meta?.title ?? id}</span>
                  </li>
                )
              })}
            </ul>
          </>
        )}

        {evidenceIds.length > 0 && (
          <>
            <h3>Evidence used</h3>
            <ul className="rp-ruling__chip-list">
              {evidenceIds.map((id) => (
                <li key={id} className="rp-ruling__chip">
                  {id}
                </li>
              ))}
            </ul>
          </>
        )}

        {flags.length > 0 && (
          <>
            <h3>Flags</h3>
            <ul className="rp-ruling__flags">
              {flags.map((f) => (
                <li key={f.key} className={`rp-ruling__flag rp-ruling__flag--${f.tone}`}>
                  {f.label}
                </li>
              ))}
            </ul>
          </>
        )}

        {riderMessage && (
          <>
            <h3>Message to rider</h3>
            <p>{riderMessage}</p>
          </>
        )}
        {driverMessage && (
          <>
            <h3>Message to driver</h3>
            <p>{driverMessage}</p>
          </>
        )}
      </div>
    </Modal>
  )
}

function AssignReviewerModal({
  onCancel,
  onAssign,
}: {
  onCancel: () => void
  onAssign: (name: string) => void
}) {
  const [name, setName] = useState('')
  const presets = ['Maya Singh (L2 Support)', 'Carl Reed (L2 Support)', 'Sara Patel (Team Lead)']
  return (
    <Modal
      open
      title="Assign to a human reviewer"
      onClose={onCancel}
      size="sm"
      footer={
        <>
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="rp-btn rp-btn--primary" onClick={() => onAssign(name)}>
            Assign
          </button>
        </>
      }
    >
      <p className="rp-muted">Pick a reviewer to take ownership of this escalated dispute.</p>
      <ul className="rp-ruling__reviewer-list">
        {presets.map((p) => (
          <li key={p}>
            <button type="button" className="rp-ruling__reviewer-option" onClick={() => setName(p)}>
              {p}
            </button>
          </li>
        ))}
      </ul>
      <div className="rp-field">
        <span>Or enter a name</span>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Reviewer name"
        />
      </div>
    </Modal>
  )
}

function AddEvidenceModal({
  onCancel,
  onSubmit,
}: {
  onCancel: () => void
  onSubmit: () => void
}) {
  const [activeChip, setActiveChip] = useState<'photos_videos' | 'chat_logs' | 'receipts' | 'other'>(
    'photos_videos',
  )
  const [files, setFiles] = useState<{ name: string; size: number }[]>([])
  return (
    <Modal
      open
      title="Add evidence"
      onClose={onCancel}
      size="md"
      footer={
        <>
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onCancel}>
            Cancel
          </button>
          <button
            type="button"
            className="rp-btn rp-btn--primary"
            onClick={onSubmit}
            disabled={files.length === 0}
          >
            Submit evidence
          </button>
        </>
      }
    >
      <p className="rp-muted">Attach additional files to support the dispute. Evidence is listed, not analysed.</p>
      <div className="rp-evidence__chips" role="tablist" aria-label="Evidence type">
        {(['photos_videos', 'chat_logs', 'receipts', 'other'] as const).map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={activeChip === k}
            className={`rp-evidence__chip ${activeChip === k ? 'is-selected' : ''}`}
            onClick={() => setActiveChip(k)}
          >
            {labelForChip(k)}
          </button>
        ))}
      </div>
      <label className="rp-dropzone">
        <input
          type="file"
          multiple
          style={{ display: 'none' }}
          onChange={(e) => {
            const next: { name: string; size: number }[] = []
            for (const f of Array.from(e.target.files ?? [])) {
              next.push({ name: f.name, size: f.size })
            }
            setFiles((prev) => [...prev, ...next])
            // Reset the input so the same file can be re-added.
            e.target.value = ''
          }}
        />
        <div className="rp-dropzone__icon" aria-hidden>
          <UploadIcon size={28} />
        </div>
        <div className="rp-dropzone__text">
          <strong>Drag and drop files here</strong>
          <span>or click to browse</span>
        </div>
      </label>
      {files.length > 0 && (
        <ul className="rp-ruling__files">
          {files.map((f, i) => (
            <li key={i}>
              <span>{f.name}</span>
              <span className="rp-muted">{Math.round(f.size / 1024)} KB</span>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  )
}

function MessageModal({
  who,
  text,
  onClose,
}: {
  who: 'rider' | 'driver'
  text: string
  onClose: () => void
}) {
  return (
    <Modal
      open
      title={who === 'rider' ? 'Message to rider' : 'Message to driver'}
      onClose={onClose}
      size="md"
      footer={
        <button type="button" className="rp-btn rp-btn--primary" onClick={onClose}>
          Close
        </button>
      }
    >
      <p>{text || 'No message was recorded for this audience.'}</p>
    </Modal>
  )
}

/* ============================================================
 * Helpers
 * ============================================================ */

function money(n: number | null | undefined): string {
  const v = typeof n === 'number' && Number.isFinite(n) ? n : 0
  return `S$${v.toFixed(2)}`
}

function headlineFor(outcome: string): string {
  switch (outcome) {
    case 'full_refund':
      return 'FULL REFUND APPROVED'
    case 'partial_refund':
      return 'PARTIAL REFUND APPROVED'
    case 'no_refund':
      return 'CHARGE UPHELD'
    case 'no_action':
      return 'NO ACTION — FARE UNCHANGED'
    default:
      return outcome.toUpperCase()
  }
}

function summaryLineFor(ruling: Ruling): string {
  const refund = ruling.refund_amount
  if (ruling.outcome === 'full_refund') {
    return `${money(refund)} will be refunded to the rider.`
  }
  if (ruling.outcome === 'partial_refund') {
    return `${money(refund)} will be refunded to the rider.`
  }
  if (ruling.outcome === 'no_refund') {
    return 'The charge stands. No refund will be issued.'
  }
  if (ruling.outcome === 'no_action') {
    return 'The fare is unchanged. No action is required.'
  }
  return ''
}

function truncate(s: string, n: number): string {
  if (!s) return ''
  return s.length <= n ? s : `${s.slice(0, n).trim()}…`
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString()
  } catch {
    return iso
  }
}

function parseReasonBlob(blob: string, policySections: string[]): string[] {
  const items: string[] = []
  // Backend joins escalation reasons with a comma (e.g. "safety_incident,low_confidence").
  if (blob) {
    for (const part of blob.split(',')) {
      const t = part.trim()
      if (!t) continue
      items.push(humanizeReason(t))
    }
  }
  for (const s of policySections) {
    items.push(`Policy section ${s} was a deciding factor.`)
  }
  return items
}

function humanizeReason(code: string): string {
  switch (code) {
    case 'safety_incident':
      return 'The dispute is a safety incident and requires human review.'
    case 'rule_llm_disagreement':
      return 'The deterministic rule outcome and the LLM recommendation disagree.'
    case 'low_confidence':
      return 'The judge\'s confidence fell below the auto-resolve threshold.'
    default:
      return code.replace(/_/g, ' ')
  }
}

function labelForChip(k: 'photos_videos' | 'chat_logs' | 'receipts' | 'other'): string {
  switch (k) {
    case 'photos_videos':
      return 'Photos / Videos'
    case 'chat_logs':
      return 'Chat logs'
    case 'receipts':
      return 'Receipts'
    case 'other':
      return 'Other files'
  }
}
