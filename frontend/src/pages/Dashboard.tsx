import { useMemo } from 'react'
import type { DisputeListItem } from '../api'
import StatusBadge from '../components/StatusBadge'
import Mascot from '../components/Mascot'
import Sparkline from '../components/Sparkline'
import { disputeStatusVariant, categoryLabel, outcomeLabel } from '../lib/status'
import { buildDashboardSummary } from '../mocks'

interface DashboardProps {
  disputes: DisputeListItem[]
  loading: boolean
  error: string | null
  onCreate: () => void
  onSelect: (d: DisputeListItem) => void
  onViewAll: () => void
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  return `${day} ${month} ${year}`
}

function trendChip(deltaPct: number | null): { text: string; positive: boolean } | null {
  // MOCK: backend has no historical-snapshot endpoint, so the dashboard
  // derives `null` and we hide the trend entirely (no fake numbers).
  if (deltaPct === null || deltaPct === undefined) return null
  const positive = deltaPct >= 0
  const arrow = positive ? '▲' : '▼'
  return { text: `${arrow} ${Math.abs(deltaPct)}%`, positive }
}

export default function Dashboard({
  disputes,
  loading,
  error,
  onCreate,
  onSelect,
  onViewAll,
}: DashboardProps) {
  const summary = useMemo(() => buildDashboardSummary(disputes), [disputes])

  // Sort by created_at desc, then take the 5 most recent.
  const recent = useMemo(() => {
    return [...disputes]
      .sort((a, b) => {
        const ta = new Date(a.created_at).getTime()
        const tb = new Date(b.created_at).getTime()
        if (Number.isNaN(ta) || Number.isNaN(tb)) return b.id - a.id
        return tb - ta
      })
      .slice(0, 5)
  }, [disputes])

  // MOCK: no historical-snapshot endpoint, so we don't have a real
  // series to plot. Each stat card gets `series: []` and the UI hides
  // the sparkline and the trend chip rather than fake a number. Remove
  // the empty arrays and feed real series once /analytics returns
  // time-series.
  const noSeries: number[] = []
  // Avg-resolution card: hidden entirely when avgResolutionMin is null.

  return (
    <div className="rp-page rp-dashboard">
      <div className="rp-page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Overview and quick actions</p>
        </div>
      </div>

      {/* Welcome card */}
      <div className="rp-welcome">
        <div className="rp-welcome__copy">
          <h2>
            Welcome to RumblePaws <span aria-hidden>✨</span>
          </h2>
          <p>AI-powered dispute resolution for a fairer Ryde.</p>
          <div className="rp-welcome__cta">
            <button className="rp-btn rp-btn--primary" onClick={onCreate} type="button">
              + New Dispute
            </button>
            <button
              className="rp-btn rp-btn--on-pink"
              onClick={onViewAll}
              type="button"
              disabled={disputes.length === 0 && !loading}
              title={disputes.length === 0 ? 'No disputes yet' : 'View past disputes'}
            >
              View Past Disputes
            </button>
          </div>
        </div>
        <div className="rp-welcome__art" aria-hidden>
          <Mascot size={150} />
        </div>
      </div>

      {/* Stat cards */}
      <div className="rp-stat-grid">
        <StatCard
          label="Total Disputes"
          value={String(summary.totalDisputes)}
          series={noSeries}
          color="#F0246E"
          delta={trendChip(summary.deltas.totalPct)}
        />
        <StatCard
          label="Auto Resolved"
          value={summary.totalDisputes === 0 ? '—' : `${summary.autoResolvedPct}%`}
          series={noSeries}
          color="#178F4B"
          delta={trendChip(summary.deltas.autoResolvedPct)}
        />
        <AvgResolutionCard
          avgMin={summary.avgResolutionMin}
          deltaPct={summary.deltas.avgMinPct}
        />
        <StatCard
          label="Escalated to Human"
          value={String(summary.escalatedToHuman)}
          series={noSeries}
          color="#C2510A"
          delta={trendChip(summary.deltas.escalatedPct)}
        />
      </div>

      {/* Recent Disputes table */}
      <div className="rp-card rp-recent">
        <div className="rp-recent__head">
          <h3>Recent Disputes</h3>
          <button
            className="rp-btn rp-btn--text"
            onClick={onViewAll}
            type="button"
            disabled={disputes.length === 0}
          >
            View all →
          </button>
        </div>
        {error ? (
          <div className="rp-recent__state rp-recent__state--error">
            <strong>Couldn't load disputes.</strong>
            <p>{error}</p>
          </div>
        ) : loading ? (
          <div className="rp-recent__state">Loading recent disputes…</div>
        ) : recent.length === 0 ? (
          <div className="rp-recent__state">
            <strong>No disputes yet.</strong>
            <p>Click <em>+ New Dispute</em> to start your first one.</p>
          </div>
        ) : (
          <table className="rp-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Category</th>
                <th>Status</th>
                <th>Submitted</th>
                <th>Outcome</th>
                <th aria-label="Open" />
              </tr>
            </thead>
            <tbody>
              {recent.map((d) => (
                <tr
                  key={d.id}
                  className="rp-recent__row"
                  onClick={() => onSelect(d)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSelect(d)
                    }
                  }}
                >
                  <td className="id">#{d.id}</td>
                  <td>{categoryLabel(d.category)}</td>
                  <td>
                    <StatusBadge variant={disputeStatusVariant(d)} />
                  </td>
                  <td>{formatDate(d.created_at)}</td>
                  <td>{outcomeLabel(d.outcome)}</td>
                  <td className="chev" aria-hidden>›</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

interface StatCardProps {
  label: string
  value: string
  series: number[]
  color: string
  delta: { text: string; positive: boolean } | null
}

function StatCard({ label, value, series, color, delta }: StatCardProps) {
  return (
    <div className="rp-stat-card">
      <div className="rp-stat-card__label">{label}</div>
      <div className="rp-stat-card__value">{value}</div>
      <div className="rp-stat-card__chart">
        {series.length >= 2 ? <Sparkline values={series} color={color} /> : <span className="rp-stat-card__chart-spacer" aria-hidden />}
      </div>
      {delta ? (
        <div className={`rp-stat-card__delta ${delta.positive ? 'is-up' : 'is-down'}`}>
          {delta.text} <span className="rp-stat-card__delta-period">vs last week</span>
        </div>
      ) : (
        // No trend data — leave the slot empty rather than invent a number.
        <div className="rp-stat-card__delta is-empty" aria-hidden />
      )}
    </div>
  )
}

function AvgResolutionCard({
  avgMin,
  deltaPct,
}: {
  avgMin: number | null
  deltaPct: number | null
}) {
  // Hide the entire trend line (sparkline + delta chip) when timing data
  // is not available, per the design's intent.
  const hasData = avgMin !== null
  const delta = trendChip(deltaPct)
  return (
    <div className="rp-stat-card">
      <div className="rp-stat-card__label">Avg. Resolution Time</div>
      <div className="rp-stat-card__value">
        {hasData ? `${avgMin} min` : '—'}
      </div>
      <div className="rp-stat-card__chart">
        {hasData ? (
          <Sparkline values={[]} color="#1F64CC" />
        ) : (
          <span className="rp-stat-card__chart-spacer" aria-hidden />
        )}
      </div>
      {hasData && delta ? (
        <div className={`rp-stat-card__delta ${delta.positive ? 'is-up' : 'is-down'}`}>
          {delta.text} <span className="rp-stat-card__delta-period">vs last week</span>
        </div>
      ) : (
        <div className="rp-stat-card__delta is-empty" aria-hidden />
      )}
    </div>
  )
}
