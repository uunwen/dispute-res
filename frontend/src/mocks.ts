// MOCK: no backend endpoint yet — analytics aggregations (Screen 1 KPI strip,
// Screen 10 case-history aggregations). All values are derived locally from
// the real /disputes list. The backend does not yet expose per-dispute
// resolution duration, so `avgResolutionMin` is null and the UI must hide the
// trend line for that card. Remove once /analytics or /metrics exists.
import type { DisputeListItem } from './api'

export interface DashboardSummary {
  totalDisputes: number
  autoResolvedPct: number
  avgResolutionMin: number | null
  escalatedToHuman: number

  /** Trend deltas (period-over-period). Null when no time-series data. */
  deltas: {
    totalPct: number | null
    autoResolvedPct: number | null
    avgMinPct: number | null
    escalatedPct: number | null
  }
}

const RESOLVED_OUTCOMES = new Set(['full_refund', 'partial_refund', 'no_refund'])

export function buildDashboardSummary(disputes: DisputeListItem[]): DashboardSummary {
  const total = disputes.length
  const resolved = disputes.filter(
    (d) => d.outcome !== null && d.outcome !== undefined && RESOLVED_OUTCOMES.has(d.outcome),
  ).length
  const escalated = disputes.filter((d) => d.status === 'needs_human_review').length
  const autoResolvedPct = total === 0 ? 0 : Math.round((resolved / total) * 100)

  // MOCK: no backend timing endpoint exists yet.
  const avgResolutionMin: number | null = null

  // MOCK: no historical-snapshot endpoint, so we cannot compute a real period
  // delta. Surface `null` and let the UI hide trend chips rather than fake it.
  const deltas: DashboardSummary['deltas'] = {
    totalPct: null,
    autoResolvedPct: null,
    avgMinPct: null,
    escalatedPct: null,
  }

  return {
    totalDisputes: total,
    autoResolvedPct,
    avgResolutionMin,
    escalatedToHuman: escalated,
    deltas,
  }
}

export interface CategoryBucket {
  category: string
  count: number
}

export function bucketByCategory(disputes: DisputeListItem[]): CategoryBucket[] {
  const map = new Map<string, number>()
  for (const d of disputes) {
    map.set(d.category, (map.get(d.category) ?? 0) + 1)
  }
  return Array.from(map.entries()).map(([category, count]) => ({ category, count }))
}
