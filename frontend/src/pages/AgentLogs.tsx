import { useEffect, useMemo, useState } from 'react'
import { api, isMockMode, type AgentMessage, type DisputeListItem } from '../api'
import { buildRounds, type Speaker } from '../lib/rounds'
import { categoryLabel, disputeStatusVariant, outcomeLabel } from '../lib/status'
import StatusBadge from '../components/StatusBadge'

interface Props {
  /** Pre-fetched list of disputes (the parent app already loads this). */
  disputes: DisputeListItem[]
  loading: boolean
  error: string | null
}

interface Row {
  dispute: DisputeListItem
  /** AgentMessages keyed by sender; missing senders are simply absent. */
  riderBrief: string | null
  driverBrief: string | null
  judgeBrief: string | null
  /** Total round count (Rider + Driver + Judge). */
  rounds: number
  /** Ruling confidence in [0, 1], if a ruling exists. */
  confidence: number | null
  /** Resolution time in minutes, if a ruling timestamp is known. */
  durationMin: number | null
  /** Backend rule outcome object, used by the drawer if it exists. */
  ruleOutcome: Record<string, unknown> | null
}

const SPEAKER_ORDER: Speaker[] = ['rider', 'driver', 'judge']
const SPEAKER_META: Record<Speaker, { name: string; role: string; color: string }> = {
  rider: { name: 'Rider Advocate', role: "Presents the rider's case", color: '#F0246E' },
  driver: { name: 'Driver Advocate', role: "Presents the driver's defense", color: '#1F64CC' },
  judge: { name: 'Judge Agent', role: 'Evaluates evidence and policy', color: '#7C3AED' },
}

function formatDateTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${day} ${month} ${year} · ${hh}:${mm}`
}

function readBrief(content: Record<string, unknown>): string | null {
  if (content && typeof content === 'object') {
    const brief = (content as { brief?: { argument_summary?: string } }).brief
    const summary = brief?.argument_summary
    if (typeof summary === 'string' && summary.length > 0) return summary
  }
  return null
}

function readEscalation(content: Record<string, unknown>): string {
  const ruling = (content as { ruling?: string }).ruling ?? ''
  const reason = (content as { escalation_reason?: string }).escalation_reason ?? ''
  const recommended = (content as { recommended_action?: string }).recommended_action ?? ''
  return [ruling, reason ? `Reason: ${reason}` : '', recommended].filter(Boolean).join(' · ')
}

async function buildRow(d: DisputeListItem): Promise<Row> {
  const [ruling, messages] = await Promise.all([
    d.status === 'resolved' || d.status === 'needs_human_review'
      ? api.getRuling(d.id).catch(() => null)
      : Promise.resolve(null),
    api.getMessages(d.id).catch(() => [] as AgentMessage[]),
  ])

  const riderBrief = messages.find((m) => m.sender === 'RiderAdvocate' && m.message_type === 'case_brief')
    ? readBrief(messages.find((m) => m.sender === 'RiderAdvocate' && m.message_type === 'case_brief')!.content)
    : null
  const driverBrief = messages.find((m) => m.sender === 'DriverAdvocate' && m.message_type === 'case_brief')
    ? readBrief(messages.find((m) => m.sender === 'DriverAdvocate' && m.message_type === 'case_brief')!.content)
    : null
  // Judge brief: prefer case_brief, fall back to escalation summary.
  let judgeBrief: string | null = null
  const judgeCaseBrief = messages.find((m) => m.sender === 'Judge' && m.message_type === 'case_brief')
  if (judgeCaseBrief) {
    judgeBrief = readBrief(judgeCaseBrief.content)
  } else {
    const esc = messages.find((m) => m.message_type === 'escalation')
    if (esc) judgeBrief = readEscalation(esc.content) || null
  }

  const rounds = buildRounds(messages)

  let confidence: number | null = null
  let ruleOutcome: Record<string, unknown> | null = null
  let durationMin: number | null = null
  if (ruling) {
    confidence = typeof ruling.confidence === 'number' ? ruling.confidence : null
    ruleOutcome = ruling.rule_outcome ?? null
    if (ruling.created_at && d.created_at) {
      const a = new Date(d.created_at).getTime()
      const b = new Date(ruling.created_at).getTime()
      if (!Number.isNaN(a) && !Number.isNaN(b) && b > a) {
        durationMin = Math.max(1, Math.round((b - a) / 60000))
      }
    }
  }

  return { dispute: d, riderBrief, driverBrief, judgeBrief, rounds: rounds.length, confidence, durationMin, ruleOutcome }
}

export default function AgentLogs({ disputes, loading, error }: Props) {
  const [rows, setRows] = useState<Row[]>([])
  const [openDisputeId, setOpenDisputeId] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<string>('all')

  // Build the table rows. For every dispute we fetch its messages
  // and (if resolved) its ruling in parallel. The list is small
  // (mock = 12 rows, real = whatever the dispute list is), so a
  // simple fan-out is fine.
  useEffect(() => {
    let cancelled = false
    Promise.all(disputes.map((d) => buildRow(d)))
      .then((items) => {
        if (cancelled) return
        setRows(items)
      })
      .catch(() => {
        if (cancelled) return
        // On failure we just leave rows empty; the page-level error
        // banner handles the user-facing message.
      })
    return () => {
      cancelled = true
    }
  }, [disputes])

  // Loading state is derived: we're "loading" when the parent is
  // still fetching the disputes, or when we haven't built any
  // rows for the current list yet.
  const rowsLoading = loading || rows.length === 0

  // Available categories come from the data so we don't render a
  // dropdown with empty options.
  const availableCategories = useMemo<string[]>(() => {
    const seen = new Set<string>()
    for (const r of rows) seen.add(r.dispute.category)
    return [...seen]
  }, [rows])

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase()
    return rows
      .filter((r) => category === 'all' || r.dispute.category === category)
      .filter(
        (r) =>
          q === '' ||
          `#${r.dispute.id}`.includes(q) ||
          categoryLabel(r.dispute.category).toLowerCase().includes(q) ||
          outcomeLabel(r.dispute.outcome).toLowerCase().includes(q),
      )
  }, [rows, query, category])

  const openRow = filteredRows.find((r) => r.dispute.id === openDisputeId) ?? null

  return (
    <div className="rp-page rp-agent-logs">
      <div className="rp-page-header">
        <div>
          <h1>Agent Logs</h1>
          <p>
            Every dispute run, the agents that worked on it, and what they said. Click a row to open the
            full trace.
          </p>
        </div>
      </div>

      <div className="rp-card">
        <div className="rp-agent-logs__toolbar">
          <div className="rp-field rp-agent-logs__category">
            <span>Category</span>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
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
          <div className="rp-field rp-agent-logs__search">
            <span>Search</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="ID, category, outcome…"
              aria-label="Search agent runs"
            />
          </div>
          <span className="rp-agent-logs__count">
            {filteredRows.length} of {rows.length} runs
          </span>
        </div>

        {error ? (
          <div className="rp-recent__state rp-recent__state--error">
            <strong>Couldn't load disputes.</strong>
            <p>{error}</p>
          </div>
        ) : loading || rowsLoading ? (
          <div className="rp-recent__state">Loading agent traces…</div>
        ) : filteredRows.length === 0 ? (
          <div className="rp-recent__state">
            <strong>No runs match.</strong>
            <p>Try a different filter.</p>
          </div>
        ) : (
          <table className="rp-table">
            <thead>
              <tr>
                <th>Dispute</th>
                <th>Started</th>
                <th>Category</th>
                <th>Status</th>
                <th>Outcome</th>
                <th>Confidence</th>
                <th>Duration</th>
                <th>Rounds</th>
                <th aria-label="Open" />
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((r) => (
                <tr
                  key={r.dispute.id}
                  className="rp-recent__row"
                  onClick={() => setOpenDisputeId(r.dispute.id)}
                  role="button"
                  tabIndex={0}
                  aria-label={`Open trace for dispute #${r.dispute.id}`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      setOpenDisputeId(r.dispute.id)
                    }
                  }}
                >
                  <td className="id">#{r.dispute.id}</td>
                  <td>{formatDateTime(r.dispute.created_at)}</td>
                  <td>{categoryLabel(r.dispute.category)}</td>
                  <td>
                    <StatusBadge variant={disputeStatusVariant(r.dispute)} />
                  </td>
                  <td>{outcomeLabel(r.dispute.outcome)}</td>
                  <td className={r.confidence === null ? 'confidence is-empty' : 'confidence'}>
                    {r.confidence === null ? '—' : `${Math.round(r.confidence * 100)}%`}
                  </td>
                  <td>{r.durationMin === null ? '—' : `${r.durationMin} min`}</td>
                  <td>{r.rounds}</td>
                  <td className="chev" aria-hidden>›</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {openRow && (
        <TraceDrawer
          row={openRow}
          onClose={() => setOpenDisputeId(null)}
        />
      )}
    </div>
  )
}

function TraceDrawer({ row, onClose }: { row: Row; onClose: () => void }) {
  return (
    <div className="rp-drawer-backdrop" onClick={onClose} role="presentation">
      <aside
        className="rp-drawer rp-drawer--wide"
        role="dialog"
        aria-modal="true"
        aria-label="Agent trace"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="rp-drawer__head">
          <div>
            <span className="rp-drawer__eyebrow">Dispute #{row.dispute.id}</span>
            <h2>
              {categoryLabel(row.dispute.category)} ·{' '}
              <span className="rp-drawer__muted">{outcomeLabel(row.dispute.outcome)}</span>
            </h2>
            <p className="rp-drawer__meta">
              Filed {formatDateTime(row.dispute.created_at)}
              {row.durationMin !== null ? ` · resolved in ${row.durationMin} min` : ''}
              {row.confidence !== null ? ` · confidence ${Math.round(row.confidence * 100)}%` : ''}
            </p>
          </div>
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onClose} aria-label="Close">
            Close
          </button>
        </header>

        <div className="rp-drawer__body">
          {SPEAKER_ORDER.map((s) => {
            const meta = SPEAKER_META[s]
            const text =
              s === 'rider' ? row.riderBrief : s === 'driver' ? row.driverBrief : row.judgeBrief
            return (
              <section className="rp-trace" key={s}>
                <header className="rp-trace__head" style={{ borderLeftColor: meta.color }}>
                  <div>
                    <h3>{meta.name}</h3>
                    <p className="rp-muted rp-small">{meta.role}</p>
                  </div>
                  <CopyButton text={text ?? ''} disabled={text === null} />
                </header>
                <div className="rp-trace__body">
                  {text === null ? (
                    <p className="rp-muted rp-small">No output recorded for this agent on this dispute.</p>
                  ) : (
                    <p>{text}</p>
                  )}
                </div>
              </section>
            )
          })}

          {row.ruleOutcome && (
            <section className="rp-trace">
              <header className="rp-trace__head" style={{ borderLeftColor: '#9398A3' }}>
                <div>
                  <h3>Rule outcome</h3>
                  <p className="rp-muted rp-small">Deterministic rule verdict returned by the Judge</p>
                </div>
                <CopyButton text={JSON.stringify(row.ruleOutcome, null, 2)} />
              </header>
              <div className="rp-trace__body">
                <pre>{JSON.stringify(row.ruleOutcome, null, 2)}</pre>
              </div>
            </section>
          )}

          {isMockMode && (
            <p className="rp-muted rp-small">
              Showing {row.rounds} round{row.rounds === 1 ? '' : 's'} from the persisted message log.
            </p>
          )}
        </div>
      </aside>
    </div>
  )
}

function CopyButton({ text, disabled = false }: { text: string; disabled?: boolean }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      className="rp-btn rp-btn--ghost rp-btn--sm"
      onClick={async () => {
        try {
          if (navigator?.clipboard?.writeText) {
            await navigator.clipboard.writeText(text)
          } else {
            const ta = document.createElement('textarea')
            ta.value = text
            document.body.appendChild(ta)
            ta.select()
            document.execCommand('copy')
            document.body.removeChild(ta)
          }
          setCopied(true)
          setTimeout(() => setCopied(false), 1200)
        } catch {
          setCopied(false)
        }
      }}
      disabled={disabled}
      aria-label="Copy to clipboard"
    >
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}
