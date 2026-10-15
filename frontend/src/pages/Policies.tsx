import { useMemo, useState } from 'react'
import {
  POLICY_PARTS,
  rulesForPart,
  type PolicyPart,
  type PolicyRule,
} from '../lib/policyRules'

type PartFilter = PolicyPart | 'all'

const PART_FILTERS: { key: PartFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  ...POLICY_PARTS.map((p) => ({ key: p.key as PartFilter, label: p.label })),
]

/* Two lines of body text are visible when the rule is collapsed.
 * We approximate that with a character budget so the layout works
 * for any rule length without measuring. */
const COLLAPSED_CHAR_BUDGET = 220

function RuleCard({ rule }: { rule: PolicyRule }) {
  const [open, setOpen] = useState(false)
  const isLong = rule.text.length > COLLAPSED_CHAR_BUDGET
  const visible = open || !isLong ? rule.text : `${rule.text.slice(0, COLLAPSED_CHAR_BUDGET).trimEnd()}…`

  return (
    <article className="rp-policy-card" data-part={rule.part}>
      <header className="rp-policy-card__head">
        <code className="rp-policy-card__id">{rule.id}</code>
        <h3 className="rp-policy-card__title">{rule.title}</h3>
      </header>
      <p className="rp-policy-card__body">{visible}</p>
      {isLong && (
        <button
          type="button"
          className="rp-policy-card__toggle"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {open ? 'Show less' : 'Show more'}
        </button>
      )}
    </article>
  )
}

export default function Policies() {
  const [part, setPart] = useState<PartFilter>('all')
  const [query, setQuery] = useState('')

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase()
    const partsToShow = part === 'all' ? POLICY_PARTS : POLICY_PARTS.filter((p) => p.key === part)
    return partsToShow
      .map((p) => {
        const rules = rulesForPart(p.key)
        const filtered = q === ''
          ? rules
          : rules.filter(
              (r) =>
                r.id.toLowerCase().includes(q) ||
                r.title.toLowerCase().includes(q) ||
                r.text.toLowerCase().includes(q),
            )
        return { part: p, rules: filtered }
      })
      .filter((g) => g.rules.length > 0)
  }, [part, query])

  const totalShown = groups.reduce((acc, g) => acc + g.rules.length, 0)
  const totalRules = useMemo(() => POLICY_PARTS.reduce((acc, p) => acc + rulesForPart(p.key).length, 0), [])

  return (
    <div className="rp-page rp-policies">
      <div className="rp-page-header">
        <div>
          <h1>Dispute Policy Rules</h1>
          <p>
            The framework applied by the Rider Advocate, Driver Advocate and Judge agents. Rule ids match{' '}
            <code>backend/policies/*.md</code> exactly.
          </p>
        </div>
      </div>

      <div className="rp-card rp-policies__toolbar">
        <div className="rp-tabs" role="tablist" aria-label="Policy part filter">
          {PART_FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              role="tab"
              aria-selected={f.key === part}
              className={f.key === part ? 'active' : ''}
              onClick={() => setPart(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="rp-field rp-policies__search">
          <span>Search</span>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rule id, title or text…"
            aria-label="Search rules"
          />
        </div>
        <span className="rp-policies__count">
          {totalShown} of {totalRules} rules
        </span>
      </div>

      {groups.length === 0 ? (
        <div className="rp-card rp-card--padded">
          <h3 style={{ marginTop: 0 }}>No matching rules.</h3>
          <p className="rp-muted">Try a different search term or part filter.</p>
        </div>
      ) : (
        groups.map((g) => (
          <section className="rp-policies__group" key={g.part.key}>
            <header className="rp-policies__group-head">
              <h2>{g.part.label}</h2>
              <p className="rp-muted rp-small">{g.part.description}</p>
            </header>
            {g.rules.length === 0 ? (
              <p className="rp-policies__empty">
                No published rules for this part yet. The framework is still draft.
              </p>
            ) : (
              <div className="rp-policies__grid">
                {g.rules.map((r) => (
                  <RuleCard key={r.id} rule={r} />
                ))}
              </div>
            )}
          </section>
        ))
      )}
    </div>
  )
}
