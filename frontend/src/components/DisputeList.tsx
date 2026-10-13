import type { DisputeListItem } from '../api'

interface Props {
  disputes: DisputeListItem[]
  activeId: number | null
  onSelect: (d: DisputeListItem) => void
}

export default function DisputeList(props: Props) {
  const { disputes, activeId, onSelect } = props

  return (
    <div className="card">
      <h2>Past disputes</h2>
      {disputes.length === 0 ? (
        <p className="muted">No disputes yet.</p>
      ) : (
        <ul className="dispute-list">
          {disputes.map((d) => {
            const escalated = d.status === 'needs_human_review'
            const badgeClass = escalated ? 'escalated' : (d.outcome ?? 'pending')
            const badgeText = escalated ? 'needs_human_review' : (d.outcome ?? d.status)
            return (
              <li key={d.id}>
                <button
                  className={`dispute-item ${d.id === activeId ? 'active' : ''}`}
                  onClick={() => onSelect(d)}
                >
                  <div className="dispute-item-top">
                    <span className="mono">#{d.id}</span>
                    <span className={`badge ${badgeClass}`}>{badgeText}</span>
                  </div>
                  <div className="muted small">{d.category} · trip {d.trip_id}</div>
                  <div className="muted small">
                    {d.refund_amount != null ? `$${d.refund_amount.toFixed(2)}` : '—'}
                    {d.llm_degraded ? ' · LLM fallback' : ''}
                  </div>
                  {d.llm_degraded && <div className="badge degraded">LLM unavailable</div>}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
