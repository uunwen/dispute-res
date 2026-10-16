import { useMemo, useState } from 'react'
import type { DisputeListItem } from '../api'
import { categoryLabel, outcomeLabel } from '../lib/status'
import { getCategoryMeta } from '../lib/categoryMeta'

/* ============================================================
 * AnalyticsPane — the analytics summary used on the standalone
 * /analytics page AND on the right rail of /disputes. It is
 * intentionally data-only: it takes a list of disputes and
 * computes every number from them.
 * ============================================================ */

interface Props {
  disputes: DisputeListItem[]
  /** When provided, clicking a category bar calls this. */
  onSelectCategory?: (category: string) => void
  /** When true, renders a slightly larger header (standalone page). */
  standalone?: boolean
  /** Show the time-window selector. */
  showRangeSelector?: boolean
  /** Loading / error state (standalone page fetches its own data). */
  loading?: boolean
  error?: string | null
  /** Whether synthetic data is included in `disputes`. */
  includeSynthetic?: boolean
  /** Count of synthetic variants (VAR-*) in `disputes`, for the note. */
  syntheticCount?: number
  /** Called to toggle synthetic data (only on the standalone page). */
  onIncludeSyntheticChange?: (include: boolean) => void
}

type RangeKey = 'all' | 7 | 30 | 90

const RANGES: { key: RangeKey; label: string }[] = [
  { key: 'all', label: 'All time' },
  { key: 7, label: '7d' },
  { key: 30, label: '30d' },
  { key: 90, label: '90d' },
]

function rangeLabel(key: RangeKey): string {
  if (key === 'all') return 'All time'
  if (key === 7) return 'Last 7 days'
  if (key === 30) return 'Last 30 days'
  return 'Last 90 days'
}

interface CategoryStat {
  category: string
  label: string
  count: number
  percent: number
  color: string
}

interface OutcomeStat {
  key: string
  label: string
  count: number
  percent: number
  color: string
}

function inRange(iso: string, days: number): boolean {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return false
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000
  return t >= cutoff
}

function resolutionMinutes(d: DisputeListItem): number | null {
  const raw = d.ruling_created_at
  if (typeof raw !== 'string' || raw === '') return null
  const filed = new Date(d.created_at).getTime()
  const resolved = new Date(raw).getTime()
  if (Number.isNaN(filed) || Number.isNaN(resolved) || resolved < filed) return null
  return Math.round((resolved - filed) / 60000)
}

function confidenceValue(d: DisputeListItem): number | null {
  const c = d.confidence
  return typeof c === 'number' && Number.isFinite(c) ? c : null
}

export default function AnalyticsPane({
  disputes,
  onSelectCategory,
  standalone = false,
  showRangeSelector = true,
  loading = false,
  error = null,
  includeSynthetic = false,
  syntheticCount,
  onIncludeSyntheticChange,
}: Props) {
  const [range, setRange] = useState<RangeKey>('all')

  // ---- Filter to the selected window ----
  const windowDisputes = useMemo(() => {
    if (range === 'all') return disputes
    return disputes.filter((d) => inRange(d.created_at, range))
  }, [disputes, range])

  // ---- Top-line stats ----
  const stats = useMemo(() => {
    const total = windowDisputes.length
    const resolved = windowDisputes.filter((d) => d.outcome != null)
    const autoResolved = windowDisputes.filter((d) => d.status === 'resolved')
    const escalated = windowDisputes.filter((d) => d.status === 'needs_human_review')

    const resolutionMins = resolved
      .map((d) => resolutionMinutes(d))
      .filter((n): n is number => n !== null)
    const avgResolutionMin =
      resolutionMins.length === 0
        ? null
        : Math.round(resolutionMins.reduce((a, b) => a + b, 0) / resolutionMins.length)

    const confidences = resolved
      .map((d) => confidenceValue(d))
      .filter((n): n is number => n !== null)
    const avgConfidence =
      confidences.length === 0
        ? null
        : Math.round((confidences.reduce((a, b) => a + b, 0) / confidences.length) * 100)

    return {
      total,
      resolvedCount: resolved.length,
      autoResolvedCount: autoResolved.length,
      autoResolvedPct: total === 0 ? null : Math.round((autoResolved.length / total) * 100),
      avgResolutionMin,
      avgConfidence,
      escalatedCount: escalated.length,
      escalatedPct: total === 0 ? null : Math.round((escalated.length / total) * 100),
    }
  }, [windowDisputes])

  // ---- By category ----
  const byCategory = useMemo<CategoryStat[]>(() => {
    if (windowDisputes.length === 0) return []
    const counts = new Map<string, number>()
    for (const d of windowDisputes) counts.set(d.category, (counts.get(d.category) ?? 0) + 1)
    const total = windowDisputes.length
    const stats: CategoryStat[] = []
    for (const [cat, count] of counts) {
      const meta = getCategoryMeta(cat)
      stats.push({
        category: cat,
        label: categoryLabel(cat),
        count,
        percent: Math.round((count / total) * 100),
        color: meta.color,
      })
    }
    return stats.sort((a, b) => b.count - a.count)
  }, [windowDisputes])

  // ---- Outcomes ----
  const byOutcome = useMemo<OutcomeStat[]>(() => {
    if (windowDisputes.length === 0) return []
    const counts = new Map<string, number>()
    for (const d of windowDisputes) {
      const key = d.outcome ?? 'pending'
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    const total = windowDisputes.length
    const stats: OutcomeStat[] = []
    for (const [key, count] of counts) {
      stats.push({
        key,
        label: outcomeLabel(key === 'pending' ? null : key),
        count,
        percent: Math.round((count / total) * 100),
        color: outcomeColor(key),
      })
    }
    return stats.sort((a, b) => b.count - a.count)
  }, [windowDisputes])

  const empty = !loading && !error && windowDisputes.length === 0

  return (
    <div className={standalone ? 'rp-analytics' : 'rp-analytics rp-analytics--pane'}>
      {/* Header */}
      <div className="rp-analytics__header">
        <div>
          <h2>{standalone ? 'Case History & Analytics' : 'Analytics'}</h2>
          {standalone && <p className="rp-muted">Track performance and impact</p>}
        </div>
        <div className="rp-analytics__controls">
          {onIncludeSyntheticChange && (
            <label className="rp-analytics__synthetic-toggle">
              <input
                type="checkbox"
                checked={includeSynthetic}
                onChange={(e) => onIncludeSyntheticChange(e.target.checked)}
              />
              <span>Include synthetic data</span>
            </label>
          )}
          {showRangeSelector && (
            <div className="rp-analytics__range" role="tablist" aria-label="Time window">
              {RANGES.map((r) => (
                <button
                  key={r.key}
                  type="button"
                  role="tab"
                  aria-selected={r.key === range}
                  className={r.key === range ? 'active' : ''}
                  onClick={() => setRange(r.key)}
                >
                  {rangeLabel(r.key)}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {includeSynthetic && (syntheticCount ?? 0) > 0 && (
        <div className="rp-analytics__synthetic-note" role="status">
          Includes {syntheticCount} synthetic variants of organizer samples
        </div>
      )}

      {loading ? (
        <div className="rp-card rp-card--padded">Loading analytics…</div>
      ) : error ? (
        <div className="rp-card rp-card--padded">
          <strong>Couldn't load disputes.</strong>
          <p className="rp-muted">{error}</p>
        </div>
      ) : empty ? (
        <div className="rp-analytics__empty">
          <p>No disputes in this range</p>
          <div className="rp-analytics__empty-actions">
            {range !== 'all' && (
              <button type="button" className="rp-btn rp-btn--primary" onClick={() => setRange('all')}>
                Show all time
              </button>
            )}
            {onIncludeSyntheticChange && !includeSynthetic && (
              <button
                type="button"
                className="rp-btn rp-btn--ghost"
                onClick={() => onIncludeSyntheticChange(true)}
              >
                Include synthetic data
              </button>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* Stat tiles */}
          <div className="rp-stat-grid rp-analytics__tiles">
            <Tile
              label="Total Disputes"
              value={stats.total === 0 ? '—' : String(stats.total)}
              accent="#F0246E"
            />
            <Tile
              label="Auto-Resolved"
              value={stats.autoResolvedPct === null ? '—' : `${stats.autoResolvedPct}%`}
              accent="#178F4B"
              sub={stats.autoResolvedPct === null ? null : `${stats.autoResolvedCount} of ${stats.total}`}
            />
            <Tile
              label="Avg. Resolution"
              value={stats.avgResolutionMin === null ? '—' : `${stats.avgResolutionMin} min`}
              accent="#1F64CC"
              sub={stats.resolvedCount === 0 ? null : `${stats.resolvedCount} resolved`}
            />
            <Tile
              label="Avg. Confidence"
              value={stats.avgConfidence === null ? '—' : `${stats.avgConfidence}%`}
              accent="#A855F7"
              sub={stats.resolvedCount === 0 ? null : `${stats.resolvedCount} resolved`}
            />
            <Tile
              label="Escalated"
              value={stats.escalatedPct === null ? '—' : `${stats.escalatedPct}%`}
              accent="#C2510A"
              sub={stats.escalatedPct === null ? null : `${stats.escalatedCount} of ${stats.total}`}
            />
          </div>

          <div className="rp-analytics__grid">
            {/* By category */}
            <section className="rp-card rp-card--padded">
              <header className="rp-analytics__card-head">
                <h3>Disputes by Category</h3>
                <span className="rp-muted rp-small">{windowDisputes.length} in range</span>
              </header>
              <ul className="rp-analytics__bars" aria-label="Disputes by category">
                {byCategory.map((c) => (
                  <li key={c.category}>
                    <button
                      type="button"
                      className="rp-analytics__bar"
                      onClick={() => onSelectCategory?.(c.category)}
                      disabled={!onSelectCategory}
                      title={
                        onSelectCategory
                          ? `View ${c.label} disputes`
                          : `${c.count} ${c.label} (${c.percent}%)`
                      }
                    >
                      <div className="rp-analytics__bar-label">
                        <span>{c.label}</span>
                        <span className="rp-analytics__bar-value">
                          {c.count} · {c.percent}%
                        </span>
                      </div>
                      <div
                        className="rp-analytics__bar-track"
                        role="progressbar"
                        aria-valuenow={c.percent}
                        aria-valuemin={0}
                        aria-valuemax={100}
                      >
                        <div
                          className="rp-analytics__bar-fill"
                          style={{ width: `${c.percent}%`, background: c.color }}
                        />
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </section>

            {/* Outcomes */}
            <section className="rp-card rp-card--padded">
              <header className="rp-analytics__card-head">
                <h3>Outcomes</h3>
                <span className="rp-muted rp-small">{windowDisputes.length} in range</span>
              </header>
              <ul className="rp-analytics__outcomes">
                {byOutcome.map((o) => (
                  <li key={o.key} className="rp-analytics__outcome">
                    <span className="rp-analytics__outcome-dot" style={{ background: o.color }} />
                    <span className="rp-analytics__outcome-label">{o.label}</span>
                    <span className="rp-analytics__outcome-count">{o.count}</span>
                    <span className="rp-analytics__outcome-pct">{o.percent}%</span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </>
      )}
    </div>
  )
}

interface TileProps {
  label: string
  value: string
  accent: string
  sub?: string | null
}

function Tile({ label, value, accent, sub }: TileProps) {
  return (
    <div className="rp-stat-card">
      <div className="rp-stat-card__label">{label}</div>
      <div className="rp-stat-card__value">{value}</div>
      <div
        className="rp-analytics__tile-bar"
        style={{ background: accent, height: 4, width: '40%', borderRadius: 2, marginTop: 4 }}
        aria-hidden
      />
      {sub ? (
        <div className="rp-stat-card__delta is-up" style={{ visibility: 'visible' }}>
          {sub}
        </div>
      ) : (
        <div className="rp-stat-card__delta is-empty" aria-hidden />
      )}
    </div>
  )
}

function outcomeColor(key: string): string {
  switch (key) {
    case 'full_refund':
      return '#178F4B'
    case 'partial_refund':
      return '#1F64CC'
    case 'no_refund':
      return '#9398A3'
    case 'no_action':
      return '#9398A3'
    case 'favor_rider':
      return '#178F4B'
    case 'favor_driver':
      return '#1F64CC'
    case 'escalate_to_human':
      return '#C2510A'
    default:
      return 'var(--rp-text-subtle)'
  }
}
