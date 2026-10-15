import type { DisputeListItem } from '../api'
import StatusBadge, { type StatusVariant } from '../components/StatusBadge'
import { categoryLabel, disputeStatusVariant } from '../lib/status'

interface DisputeDetailProps {
  dispute: DisputeListItem
  onOpenDebate: (id: number) => void
  onOpenRuling: (id: number) => void
}

/* ============================================================
 * Dispute detail redirect — when a user lands on /disputes/:id
 * directly, we send them to the debate page (if the dispute is
 * still open) or the ruling page (if it has been resolved or
 * escalated). This page is never the final destination; it's a
 * routing shim so deep links work.
 * ============================================================ */

export default function DisputeDetail({ dispute, onOpenDebate, onOpenRuling }: DisputeDetailProps) {
  const isFinished = dispute.status === 'resolved' || dispute.status === 'needs_human_review'

  return (
    <div className="rp-page rp-detail">
      <div className="rp-detail__header">
        <div>
          <h1>Dispute #{dispute.id}</h1>
          <div className="meta">
            <span>{categoryLabel(dispute.category)}</span>
            <span>·</span>
            <span>Submitted {new Date(dispute.created_at).toLocaleDateString()}</span>
          </div>
        </div>
        <StatusBadge variant={disputeStatusVariant(dispute) satisfies StatusVariant} />
      </div>
      <div className="rp-card rp-card--padded">
        <p className="rp-muted" style={{ marginTop: 0 }}>
          {isFinished
            ? 'This dispute has been resolved. View the final ruling for the full breakdown.'
            : 'This dispute is in progress. View the live debate to see the agents deliberating.'}
        </p>
        <button
          type="button"
          className="rp-btn rp-btn--primary"
          onClick={() => (isFinished ? onOpenRuling(dispute.id) : onOpenDebate(dispute.id))}
        >
          {isFinished ? 'View Ruling →' : 'View Debate →'}
        </button>
      </div>
    </div>
  )
}
