import { useEffect, useState } from 'react'
import { api, isMockMode, type ConfigEntry, type Settings as SettingsData } from '../api'

/* ============================================================
 * Settings — read-only view sourced from GET /meta/settings.
 * Models, policy version, policy numbers, thresholds and
 * escalation values all come from the backend config (never
 * hardcoded here).
 * ============================================================ */

function NumberList({ entries }: { entries: ConfigEntry[] }) {
  return (
    <ul className="rp-settings__numbers">
      {entries.map((n) => (
        <li key={n.key}>
          <span className="rp-settings__numbers-label">{n.label}</span>
          <span className="rp-settings__numbers-value">{n.value}</span>
          <span className="rp-settings__numbers-source">{n.source}</span>
        </li>
      ))}
    </ul>
  )
}

export default function Settings() {
  const [data, setData] = useState<SettingsData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .getSettings()
      .then((s) => {
        if (!cancelled) setData(s)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load settings.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const models = data?.models ?? []
  const llmMock = data?.llm_mock ?? false

  return (
    <div className="rp-page rp-settings">
      <div className="rp-page-header">
        <div>
          <h1>Settings</h1>
          <p>Model assignments, policy version, and the key numbers the agents use.</p>
        </div>
      </div>

      {error && (
        <div className="rp-recent__state rp-recent__state--error">
          <strong>Couldn't load settings.</strong>
          <p>{error}</p>
        </div>
      )}

      {/* Model assignments */}
      <section className="rp-card rp-card--padded">
        <header className="rp-settings__head">
          <h2>Models</h2>
          <p className="rp-muted">
            One model per agent. The orchestrator routes a dispute through all three; the Judge sees
            both advocates' briefs before issuing a ruling.
          </p>
        </header>
        {models.length === 0 ? (
          <p className="rp-muted">Loading models…</p>
        ) : (
          <div className="rp-settings__models">
            {models.map((m) => (
              <div key={m.agent} className="rp-settings__model">
                <div className="rp-settings__model-name">
                  <code className="rp-settings__chip">{m.agent}</code>
                  <span>{m.purpose}</span>
                </div>
                <div className="rp-settings__model-value">
                  <code>{m.model}</code>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Policy version + key numbers + escalation + thresholds */}
      <section className="rp-card rp-card--padded">
        <header className="rp-settings__head">
          <h2>Policy</h2>
          <p className="rp-muted">
            All agents reason against the same policy document. Numbers below are the values the
            deterministic code uses — change the policy file, not this page.
          </p>
        </header>
        <dl className="rp-settings__policy">
          <div className="rp-settings__policy-row">
            <dt>Policy version</dt>
            <dd>{data?.policy_version ?? '—'}</dd>
          </div>
          <div className="rp-settings__policy-row rp-settings__policy-row--top">
            <dt>Key policy numbers</dt>
            <dd>
              <NumberList entries={data?.policy_numbers ?? []} />
            </dd>
          </div>
          <div className="rp-settings__policy-row rp-settings__policy-row--top">
            <dt>Escalation</dt>
            <dd>
              <NumberList entries={data?.escalation ?? []} />
            </dd>
          </div>
          <div className="rp-settings__policy-row rp-settings__policy-row--top">
            <dt>Fraud &amp; abuse thresholds</dt>
            <dd>
              <NumberList entries={data?.thresholds ?? []} />
            </dd>
          </div>
        </dl>
      </section>

      {/* Data source indicator */}
      <section className="rp-card rp-card--padded">
        <header className="rp-settings__head">
          <h2>Data source</h2>
          <p className="rp-muted">
            Whether the app is currently rendering sample data or hitting the backend, plus the
            backend LLM mock flag.
          </p>
        </header>
        <div
          className={`rp-settings__mode ${isMockMode ? 'is-on' : 'is-off'}`}
          role="status"
          aria-label={isMockMode ? 'Sample data mode is on' : 'Sample data mode is off'}
        >
          <span className="rp-settings__mode-dot" aria-hidden />
          <div>
            <strong>Sample data mode</strong>
            <p className="rp-muted rp-small">
              {isMockMode
                ? 'On — the app is reading from the in-memory mock layer. No backend is required.'
                : 'Off — the app is reading from the live FastAPI backend.'}
            </p>
            <code className="rp-settings__env">VITE_USE_MOCK = {String(isMockMode)}</code>
            <code className="rp-settings__env" style={{ marginLeft: 8 }}>
              llm_mock = {String(llmMock)}
            </code>
          </div>
        </div>
      </section>
    </div>
  )
}
