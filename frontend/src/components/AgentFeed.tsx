import type { AgentMessage } from '../api'
import MessageBubble from './MessageBubble'

interface Props {
  messages: AgentMessage[]
  thinking: boolean
  hasDispute: boolean
  disputeStatus: string | null
  degraded: boolean
  onResolve: () => void
  onEvidenceClick: (id: string) => void
}

export default function AgentFeed({
  messages,
  thinking,
  hasDispute,
  disputeStatus,
  degraded,
  onResolve,
  onEvidenceClick,
}: Props) {
  const openUnresolved = hasDispute && disputeStatus === 'open' && messages.length === 0 && !thinking

  return (
    <div className="feed">
      <h2>Agent conversation</h2>

      {degraded && <div className="banner warn-soft">LLM unavailable, deterministic fallback</div>}

      {!hasDispute ? (
        <div className="empty-state">
          <p>No active dispute.</p>
          <p className="muted">File a dispute on the left, or pick a past one.</p>
        </div>
      ) : openUnresolved ? (
        <div className="empty-state">
          <p>Not resolved yet</p>
          <button className="primary" onClick={onResolve}>
            Resolve this dispute
          </button>
        </div>
      ) : messages.length === 0 && thinking ? (
        <div className="empty-state">
          <p>Waiting for agents…</p>
        </div>
      ) : (
        <div className="feed-scroll">
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} onEvidenceClick={onEvidenceClick} />
          ))}
          {thinking && (
            <div className="thinking">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
              <span className="thinking-label">Agents are deliberating…</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
