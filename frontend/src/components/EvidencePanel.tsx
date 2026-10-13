import { useState } from 'react'
import type { EvidenceItem } from '../api'
import EvidenceCard from './EvidenceCard'

const RELEVANT_TYPE: Record<string, string> = {
  route_deviation: 'route_deviation',
  no_show: 'noshow',
  fare_dispute: 'fare_validation',
}

interface Props {
  evidence: EvidenceItem[]
  highlightedId: string | null
  loading: boolean
  hasDispute: boolean
  category: string | null
}

export default function EvidencePanel({ evidence, highlightedId, loading, hasDispute, category }: Props) {
  const [showOther, setShowOther] = useState(false)

  const relevant = RELEVANT_TYPE[category ?? '']
  const primary = evidence.filter((e) => e.type === relevant)
  const other = evidence.filter((e) => e.type !== relevant)

  return (
    <div className="evidence-panel">
      <h2>Evidence</h2>
      {!hasDispute ? (
        <div className="empty-state">
          <p className="muted">Evidence will appear here once a dispute is open.</p>
        </div>
      ) : loading ? (
        <div className="muted">Loading evidence…</div>
      ) : evidence.length === 0 ? (
        <div className="muted">No evidence.</div>
      ) : (
        <>
          {primary.map((e) => (
            <EvidenceCard key={e.id} evidence={e} highlighted={e.id === highlightedId} />
          ))}
          {other.length > 0 && (
            <div className="other-evidence">
              <button className="json-toggle" onClick={() => setShowOther((v) => !v)}>
                {showOther ? 'Hide other evidence' : `Other evidence (${other.length})`}
              </button>
              {showOther &&
                other.map((e) => (
                  <EvidenceCard key={e.id} evidence={e} highlighted={e.id === highlightedId} />
                ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
