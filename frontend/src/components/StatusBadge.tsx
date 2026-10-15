import type { ReactNode } from 'react'

export type StatusVariant = 'resolved' | 'escalated' | 'in-progress' | 'live' | 'pending'

interface StatusBadgeProps {
  variant: StatusVariant
  label?: ReactNode
  showDot?: boolean
}

const DEFAULT_LABEL: Record<StatusVariant, string> = {
  resolved: 'Resolved',
  escalated: 'Escalated',
  'in-progress': 'In progress',
  live: 'Live',
  pending: 'Pending',
}

export default function StatusBadge({ variant, label, showDot = true }: StatusBadgeProps) {
  return (
    <span className={`rp-badge rp-badge--${variant}`}>
      {showDot && <span className="rp-badge__dot" aria-hidden />}
      {label ?? DEFAULT_LABEL[variant]}
    </span>
  )
}
