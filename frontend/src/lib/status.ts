import type { StatusVariant } from '../components/StatusBadge'
import type { DisputeListItem } from '../api'

export function disputeStatusVariant(d: DisputeListItem): StatusVariant {
  if (d.status === 'needs_human_review') return 'escalated'
  if (d.status === 'resolved' || d.outcome) {
    return 'resolved'
  }
  if (d.status === 'open') return 'in-progress'
  return 'pending'
}

export function categoryLabel(value: string): string {
  switch (value) {
    case 'route_deviation':
      return 'Route deviation'
    case 'no_show':
      return 'No-show'
    case 'fare_dispute':
      return 'Fare dispute'
    case 'property_damage':
      return 'Property damage'
    case 'safety_incident':
      return 'Safety incident'
    default:
      return value
  }
}

export function outcomeLabel(outcome: string | null | undefined): string {
  if (!outcome) return '—'
  switch (outcome) {
    case 'full_refund':
      return 'Partial refund'
    case 'partial_refund':
      return 'Partial refund'
    case 'no_refund':
      return 'No refund'
    default:
      return outcome
  }
}
