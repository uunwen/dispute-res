import { useEffect, useRef, useState } from 'react'
import type { EvidenceItem } from '../api'

interface Props {
  evidence: EvidenceItem
  highlighted: boolean
}

export default function EvidenceCard({ evidence, highlighted }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (highlighted && ref.current) {
      ref.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [highlighted])

  return (
    <div ref={ref} className={`card evidence ${highlighted ? 'highlighted' : ''}`}>
      <div className="evidence-head">
        <span className="mono">{evidence.type}</span>
        <span className={`badge supports-${evidence.supports}`}>{evidence.supports}</span>
      </div>
      <p className="small">{evidence.summary}</p>
      <div className="strength">
        <div className="strength-bar" style={{ width: `${Math.round(evidence.strength * 100)}%` }} />
      </div>
      <div className="muted small">strength {evidence.strength.toFixed(2)}</div>
      <button className="json-toggle" onClick={() => setExpanded((v) => !v)}>
        {expanded ? 'Hide data' : 'Show data'}
      </button>
      {expanded && <pre className="json">{JSON.stringify(evidence.data, null, 2)}</pre>}
    </div>
  )
}
