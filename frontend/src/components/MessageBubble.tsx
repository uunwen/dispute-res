import { useState } from 'react'
import type { AgentMessage } from '../api'

const SENDER_COLORS: Record<string, string> = {
  RiderAdvocate: '#2f80ed',
  DriverAdvocate: '#eb5757',
  Judge: '#9b51e0',
  Fraud: '#f2994a',
  System: '#828282',
}

function senderColor(sender: string): string {
  return SENDER_COLORS[sender] ?? '#828282'
}

function alignment(sender: string): 'left' | 'right' | 'center' {
  if (sender === 'RiderAdvocate') return 'left'
  if (sender === 'DriverAdvocate') return 'right'
  return 'center'
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function roundLabel(round: string | undefined): string {
  return round === 'rebuttal' ? 'Rebuttal' : 'Opening argument'
}

interface Props {
  message: AgentMessage
  onEvidenceClick: (id: string) => void
}

function CaseBriefBody({ content, onEvidenceClick }: { content: Record<string, any>; onEvidenceClick: (id: string) => void }) {
  const brief = (content.brief ?? {}) as Record<string, any>
  const claims = Array.isArray(brief.claims) ? brief.claims : []
  const weaknesses = Array.isArray(brief.weaknesses) ? brief.weaknesses : []

  return (
    <>
      <div className="round-label">{roundLabel(typeof content.round === 'string' ? content.round : undefined)}</div>
      {typeof brief.argument_summary === 'string' && brief.argument_summary && (
        <p className="bubble-text">{brief.argument_summary}</p>
      )}

      {claims.length > 0 && (
        <ul className="claims">
          {claims.map((c, i) => {
            const evIds: string[] = Array.isArray(c.evidence_ids) ? c.evidence_ids : []
            const polIds: string[] = Array.isArray(c.policy_section_ids) ? c.policy_section_ids : []
            return (
              <li key={i}>
                <span className="claim-text">{c.text}</span>
                {evIds.length > 0 && (
                  <div className="chips">
                    {evIds.map((id) => (
                      <button key={id} className="chip" onClick={() => onEvidenceClick(id)} title="Scroll to evidence">
                        {id}
                      </button>
                    ))}
                  </div>
                )}
                {polIds.length > 0 && (
                  <div className="chips">
                    {polIds.map((id) => (
                      <span key={id} className="chip policy-chip">
                        {id}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {typeof brief.requested_outcome === 'string' && brief.requested_outcome && (
        <div className="muted small">
          Requests: <strong>{brief.requested_outcome}</strong>
        </div>
      )}

      {weaknesses.length > 0 && (
        <div className="weaknesses small muted">
          <strong>Acknowledged weaknesses:</strong>
          <ul>
            {weaknesses.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}

function FraudBody({ content }: { content: Record<string, any> }) {
  const reasons = Array.isArray(content.reasons) ? content.reasons : []
  return (
    <div className="fraud-panel">
      <div className="risk-row">
        <span>
          Rider risk: <strong>{Number(content.rider_risk ?? 0).toFixed(2)}</strong>
        </span>
        <span>
          Driver risk: <strong>{Number(content.driver_risk ?? 0).toFixed(2)}</strong>
        </span>
      </div>
      {reasons.length > 0 && (
        <ul className="fraud-reasons">
          {reasons.map((r, i) => (
            <li key={i}>
              <span className="mono">{r.code}</span> — {r.description}
              {r.evidence_id ? <span className="muted"> [{r.evidence_id}]</span> : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function EscalationBody({ content }: { content: Record<string, any> }) {
  return (
    <div className="escalation-panel">
      {content.escalation_reason && (
        <div className="muted small">
          <strong>Reason:</strong> {content.escalation_reason}
        </div>
      )}
      {content.ruling && <p className="small">{content.ruling}</p>}
      {content.rider_brief && (
        <p className="small">
          <strong>Rider:</strong> {content.rider_brief}
        </p>
      )}
      {content.driver_brief && (
        <p className="small">
          <strong>Driver:</strong> {content.driver_brief}
        </p>
      )}
      {Array.isArray(content.key_evidence_ids) && content.key_evidence_ids.length > 0 && (
        <p className="small">
          <strong>Evidence:</strong> {content.key_evidence_ids.join(', ')}
        </p>
      )}
      {content.recommended_action && (
        <p className="small">
          <strong>Recommended:</strong> {content.recommended_action}
        </p>
      )}
    </div>
  )
}

export default function MessageBubble({ message, onEvidenceClick }: Props) {
  const [expanded, setExpanded] = useState(false)
  const content = (message.content ?? {}) as Record<string, any>

  return (
    <div className={`bubble align-${alignment(message.sender)}`} style={{ borderLeftColor: senderColor(message.sender) }}>
      <div className="bubble-head">
        <span className="sender" style={{ color: senderColor(message.sender) }}>
          {message.sender}
        </span>
        <span className="badge msg-type">{message.message_type}</span>
        <span className="muted small">{formatTime(message.created_at)}</span>
      </div>

      {message.message_type === 'case_brief' && <CaseBriefBody content={content} onEvidenceClick={onEvidenceClick} />}
      {message.message_type === 'fraud_signal' && <FraudBody content={content} />}
      {message.message_type === 'escalation' && <EscalationBody content={content} />}

      <button className="json-toggle" onClick={() => setExpanded((v) => !v)}>
        {expanded ? 'Hide JSON' : 'Show JSON'}
      </button>
      {expanded && <pre className="json">{JSON.stringify(message.content, null, 2)}</pre>}
    </div>
  )
}
