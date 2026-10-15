import { useMemo, useState } from 'react'
import type { DisputeListItem } from '../api'
import StatusBadge from '../components/StatusBadge'
import { categoryLabel, disputeStatusVariant, outcomeLabel } from '../lib/status'
import AnalyticsPane from './AnalyticsPane'

interface DisputesListProps {
  disputes: DisputeListItem[]
  loading: boolean
  error: string | null
  onSelect: (d: DisputeListItem) => void
  onCreate: () => void
  /** When true, the right-hand analytics pane is shown. */
  showAnalyticsPane?: boolean
  /** Forwarded to the analytics pane. */
  analyticsOnSelectCategory?: (category: string) => void
  /** Optional external category filter (e.g. when navigating from
   * the analytics pane). */
  initialCategoryFilter?: string
  /** Notifies the parent when the user changes the dropdown. */
  onCategoryFilterChange?: (category: string) => void
}

type StatusFilter = 'all' | 'resolved' | 'escalated' | 'in_progress'

type SortKey = 'id' | 'category' | 'status' | 'submitted' | 'outcome' | 'confidence'
type SortDir = 'asc' | 'desc'

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  return `${day} ${month} ${year}`
}

function confidencePct(d: DisputeListItem): number | null {
  // DisputeListItem.confidence is optional — it only exists in mock mode.
  // We tolerate `null` / `undefined` cleanly.
  const raw = (d as DisputeListItem & { confidence?: number | null }).confidence
  if (raw === null || raw === undefined) return null
  if (typeof raw !== 'number' || !Number.isFinite(raw)) return null
  return Math.round(raw * 100)
}

const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'resolved', label: 'Resolved' },
  { key: 'escalated', label: 'Escalated' },
  { key: 'in_progress', label: 'In progress' },
]

function matchesFilter(d: DisputeListItem, f: StatusFilter): boolean {
  if (f === 'all') return true
  const v = disputeStatusVariant(d)
  if (f === 'resolved') return v === 'resolved'
  if (f === 'escalated') return v === 'escalated'
  if (f === 'in_progress') return v === 'in-progress'
  return true
}

function compare(a: DisputeListItem, b: DisputeListItem, key: SortKey, dir: SortDir): number {
  const sign = dir === 'asc' ? 1 : -1
  switch (key) {
    case 'id':
      return (a.id - b.id) * sign
    case 'category':
      return categoryLabel(a.category).localeCompare(categoryLabel(b.category)) * sign
    case 'status':
      return a.status.localeCompare(b.status) * sign
    case 'outcome':
      return (a.outcome ?? '').localeCompare(b.outcome ?? '') * sign
    case 'confidence': {
      // Nulls always sort to the bottom, regardless of direction.
      const ca = confidencePct(a)
      const cb = confidencePct(b)
      if (ca === null && cb === null) return 0
      if (ca === null) return 1
      if (cb === null) return -1
      return (ca - cb) * sign
    }
    case 'submitted':
    default: {
      const ta = new Date(a.created_at).getTime()
      const tb = new Date(b.created_at).getTime()
      const na = Number.isNaN(ta) ? 0 : ta
      const nb = Number.isNaN(tb) ? 0 : tb
      return (na - nb) * sign
    }
  }
}

const ARROW: Record<SortDir, string> = { asc: '▲', desc: '▼' }

interface HeaderCellProps {
  label: string
  sortKey: SortKey
  currentKey: SortKey
  currentDir: SortDir
  onToggle: (k: SortKey) => void
  /** Right-align the cell content (used for the chevron column). */
  align?: 'right'
}

function SortableHeader({ label, sortKey, currentKey, currentDir, onToggle, align }: HeaderCellProps) {
  const active = currentKey === sortKey
  const nextDir: SortDir = active ? (currentDir === 'asc' ? 'desc' : 'asc') : 'desc'
  const ariaSort = active ? (currentDir === 'asc' ? 'ascending' : 'descending') : 'none'
  return (
    <th
      className="is-sortable"
      aria-sort={ariaSort}
      onClick={() => onToggle(sortKey)}
      style={align === 'right' ? { textAlign: 'right' } : undefined}
    >
      {label}
      {active && <span className="rp-table__sort-indicator">{ARROW[currentDir]}</span>}
      {!active && (
        <span className="rp-table__sort-indicator" style={{ color: 'var(--rp-text-subtle)' }}>
          ↕
        </span>
      )}
      <span style={{ display: 'none' }}>{nextDir}</span>
    </th>
  )
}

export default function DisputesList({
  disputes,
  loading,
  error,
  onSelect,
  onCreate,
  showAnalyticsPane = false,
  analyticsOnSelectCategory,
  initialCategoryFilter,
  onCategoryFilterChange,
}: DisputesListProps) {
  const [filter, setFilter] = useState<StatusFilter>('all')
  const [category, setCategory] = useState<string>(initialCategoryFilter ?? 'all')
  const [query, setQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('submitted')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  // Build the category dropdown from the data that's actually present.
  const availableCategories = useMemo<string[]>(() => {
    const seen = new Set<string>()
    for (const d of disputes) seen.add(d.category)
    return [...seen]
  }, [disputes])

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    return disputes
      .filter((d) => matchesFilter(d, filter))
      .filter((d) => category === 'all' || d.category === category)
      .filter(
        (d) =>
          q === '' ||
          `#${d.id}`.includes(q) ||
          categoryLabel(d.category).toLowerCase().includes(q) ||
          outcomeLabel(d.outcome).toLowerCase().includes(q),
      )
      .sort((a, b) => compare(a, b, sortKey, sortDir))
  }, [disputes, filter, category, query, sortKey, sortDir])

  function toggleSort(k: SortKey) {
    if (k === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(k)
      // Sensible defaults: date desc, confidence desc.
      setSortDir(k === 'submitted' || k === 'confidence' ? 'desc' : 'asc')
    }
  }

  function rowClick(d: DisputeListItem) {
    onSelect(d)
  }

  const tableBlock = (
    <div className="rp-page rp-disputes-list">
      <div className="rp-page-header">
        <div>
          <h1>Disputes</h1>
          <p>Every dispute filed through RumblePaws.</p>
        </div>
        <div className="rp-disputes-list__cta">
          <button className="rp-btn rp-btn--primary" onClick={onCreate} type="button">
            + New Dispute
          </button>
        </div>
      </div>

      <div className="rp-card">
        <div className="rp-disputes-list__toolbar">
          <div className="rp-tabs" role="tablist" aria-label="Status filter">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                role="tab"
                aria-selected={f.key === filter}
                className={f.key === filter ? 'active' : ''}
                onClick={() => setFilter(f.key)}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="rp-field rp-disputes-list__category">
            <span>Category</span>
            <select
              value={category}
              onChange={(e) => {
                const v = e.target.value
                setCategory(v)
                onCategoryFilterChange?.(v)
              }}
              aria-label="Filter by category"
            >
              <option value="all">All categories</option>
              {availableCategories.map((c) => (
                <option key={c} value={c}>
                  {categoryLabel(c)}
                </option>
              ))}
            </select>
          </div>
          <div className="rp-field rp-disputes-list__search">
            <span>Search</span>
            <input
              type="search"
              placeholder="ID, category, outcome…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search disputes"
            />
          </div>
        </div>

        {error ? (
          <div className="rp-recent__state rp-recent__state--error">
            <strong>Couldn't load disputes.</strong>
            <p>{error}</p>
          </div>
        ) : loading ? (
          <div className="rp-recent__state">Loading disputes…</div>
        ) : rows.length === 0 ? (
          <div className="rp-recent__state">
            <strong>No disputes match.</strong>
            <p>Try a different filter or file a new one.</p>
          </div>
        ) : (
          <table className="rp-table">
            <thead>
              <tr>
                <SortableHeader
                  label="ID"
                  sortKey="id"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onToggle={toggleSort}
                />
                <SortableHeader
                  label="Category"
                  sortKey="category"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onToggle={toggleSort}
                />
                <SortableHeader
                  label="Status"
                  sortKey="status"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onToggle={toggleSort}
                />
                <SortableHeader
                  label="Submitted"
                  sortKey="submitted"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onToggle={toggleSort}
                />
                <SortableHeader
                  label="Outcome"
                  sortKey="outcome"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onToggle={toggleSort}
                />
                <SortableHeader
                  label="Confidence"
                  sortKey="confidence"
                  currentKey={sortKey}
                  currentDir={sortDir}
                  onToggle={toggleSort}
                />
                <th aria-label="Open" />
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => {
                const conf = confidencePct(d)
                return (
                  <tr
                    key={d.id}
                    className="rp-recent__row"
                    onClick={() => rowClick(d)}
                    role="button"
                    tabIndex={0}
                    aria-label={`Open dispute #${d.id}`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        rowClick(d)
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
                    <td className={conf === null ? 'confidence is-empty' : 'confidence'}>
                      {conf === null ? '—' : `${conf}%`}
                    </td>
                    <td className="chev" aria-hidden>›</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )

  if (!showAnalyticsPane) return tableBlock

  return (
    <div className="rp-disputes-with-analytics">
      {tableBlock}
      <div className="rp-analytics-pane" aria-label="Analytics overview">
        <AnalyticsPane
          disputes={disputes}
          onSelectCategory={analyticsOnSelectCategory}
        />
      </div>
    </div>
  )
}
