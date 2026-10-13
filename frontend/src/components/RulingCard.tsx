import { useState } from 'react'
import type { Ruling } from '../api'

interface Props {
  ruling: Ruling | null
  loading: boolean
  onReRun?: () => void
}

export default function RulingCard({ ruling, loading, onReRun }: Props) {
  const [tab, setTab] = useState<'rider' | 'driver'>('rider')
  const [showSummary, setShowSummary] = useState(false)

  if (loading) return <div className="card muted">Resolving dispute…</div>
  if (!ruling) return null

  const ro = (ruling.rule_outcome ?? {}) as Record<string, any>
  const disagreement = Boolean(ro.disagreement)
  const riderMsg = typeof ro.rider_explanation === 'string' ? ro.rider_explanation : ''
  const driverMsg = typeof ro.driver_explanation === 'string' ? ro.driver_explanation : ''
  const confidencePct = Math.round(ruling.confidence * 100)
  const summary = ruling.human_review_summary

  return (
    <div className="card ruling">
      <div className="ruling-top">
        <span className={`badge outcome-${ruling.outcome}`}>{ruling.outcome}</span>
        <span className="refund">${ruling.refund_amount.toFixed(2)}</span>
      </div>

      {ruling.escalated && <div className="banner warn">Escalated: needs human review</div>}

      {ruling.escalated && summary && (
        <div className="review-summary">
          <button className="json-toggle" onClick={() => setShowSummary((v) => !v)}>
            {showSummary ? 'Hide review summary' : 'Show review summary'}
          </button>
          {showSummary && (
            <div className="summary-body small">
              {summary.escalation_reason && (
                <p>
                  <strong>Reason:</strong> {summary.escalation_reason}
                </p>
              )}
              <p>
                <strong>Ruling:</strong> {summary.ruling}
              </p>
              {summary.rider_brief && (
                <p>
                  <strong>Rider:</strong> {summary.rider_brief}
                </p>
              )}
              {summary.driver_brief && (
                <p>
                  <strong>Driver:</strong> {summary.driver_brief}
                </p>
              )}
              {(summary.key_evidence_ids ?? []).length > 0 && (
                <p>
                  <strong>Evidence:</strong> {summary.key_evidence_ids.join(', ')}
                </p>
              )}
              {summary.recommended_action && (
                <p>
                  <strong>Recommended:</strong> {summary.recommended_action}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {disagreement && <div className="banner warn-soft">Rule vs LLM disagreement flagged</div>}

      {ruling.llm_degraded && (
        <div className="banner warn-soft">LLM unavailable, deterministic fallback</div>
      )}

      <div className="confidence">
        <div className="confidence-bar" style={{ width: `${confidencePct}%` }} />
      </div>
      <div className="muted small">confidence {ruling.confidence.toFixed(2)}</div>

      <p className="small">{ruling.reasoning}</p>

      <div className="tabs">
        <button className={tab === 'rider' ? 'tab active' : 'tab'} onClick={() => setTab('rider')}>
          Message to rider
        </button>
        <button className={tab === 'driver' ? 'tab active' : 'tab'} onClick={() => setTab('driver')}>
          Message to driver
        </button>
      </div>
      <p className="small">{tab === 'rider' ? riderMsg : driverMsg}</p>

      {onReRun && (
        <button className="json-toggle" onClick={onReRun} title="Delete previous messages/ruling and run again">
          Re-run (dev)
        </button>
      )}
    </div>
  )
}
