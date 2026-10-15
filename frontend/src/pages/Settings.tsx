import { isMockMode } from '../api'

/* ============================================================
 * Settings — read-only view of model assignments, policy version,
 * and the key policy numbers the agents use. Everything is sourced
 * from the policy markdown (backend/policies/*.md) and the
 * frontend's VITE_USE_MOCK env var. No controls that don't do
 * anything are exposed.
 * ============================================================ */

interface ModelEntry {
  agent: 'RiderAdvocate' | 'DriverAdvocate' | 'Judge'
  model: string
  purpose: string
}

const MODELS: ModelEntry[] = [
  { agent: 'RiderAdvocate', model: 'ryde/llm-rider-advocate-v1', purpose: "Presents the rider's case" },
  { agent: 'DriverAdvocate', model: 'ryde/llm-driver-advocate-v1', purpose: "Presents the driver's defense" },
  { agent: 'Judge', model: 'ryde/llm-judge-v1', purpose: 'Evaluates evidence and applies policy' },
]

/* Policy numbers are read from backend/policies/*.md. They are
 * the canonical values the deterministic code uses too:
 *   - Cancellation fee (NS): $4.50
 *   - Waiting fee (NS): $4.50
 *   - Waiting window (NS): 3 minutes
 *   - Route off-route buffer (RD): 100 m
 *   - Major detour threshold (RD): 2.0 km extra
 *   - Fare tolerance (RD-002): 5%
 *   - Arrival radius (NS): 100 m (team simulation, not a Ryde rule)
 */
const POLICY_VERSION = 'v2.0 (Oct 2026)'

const POLICY_NUMBERS: { id: string; label: string; value: string; source: string }[] = [
  { id: 'NS-001', label: 'Cancellation fee', value: '$4.50', source: 'no_show_fee.md §2' },
  { id: 'NS-001', label: 'Waiting fee', value: '$4.50', source: 'no_show_fee.md §2' },
  { id: 'NS-001', label: 'Waiting window', value: '3 minutes', source: 'no_show_fee.md §2' },
  { id: 'NS-001', label: 'Arrival radius', value: '100 m', source: 'no_show_fee.md §2 (simulation)' },
  { id: 'RD-001', label: 'Off-route buffer', value: '100 m', source: 'route_deviation.md §2' },
  { id: 'RD-001', label: 'Major detour threshold', value: '2.0 km extra', source: 'route_deviation.md §2' },
  { id: 'RD-002', label: 'Fare tolerance', value: '5%', source: 'fare_surge_promo.md §2' },
]

export default function Settings() {
  return (
    <div className="rp-page rp-settings">
      <div className="rp-page-header">
        <div>
          <h1>Settings</h1>
          <p>Model assignments, policy version, and the key numbers the agents use.</p>
        </div>
      </div>

      {/* Model assignments */}
      <section className="rp-card rp-card--padded">
        <header className="rp-settings__head">
          <h2>Models</h2>
          <p className="rp-muted">
            One model per agent. The orchestrator routes a dispute through all three; the Judge sees
            both advocates' briefs before issuing a ruling.
          </p>
        </header>
        <div className="rp-settings__models">
          {MODELS.map((m) => (
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
      </section>

      {/* Policy version + key numbers */}
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
            <dd>{POLICY_VERSION}</dd>
          </div>
          <div className="rp-settings__policy-row rp-settings__policy-row--top">
            <dt>Key policy numbers</dt>
            <dd>
              <ul className="rp-settings__numbers">
                {POLICY_NUMBERS.map((n, i) => (
                  <li key={`${n.id}-${n.label}-${i}`}>
                    <span className="rp-settings__numbers-label">{n.label}</span>
                    <span className="rp-settings__numbers-value">{n.value}</span>
                    <span className="rp-settings__numbers-source">{n.source}</span>
                  </li>
                ))}
              </ul>
            </dd>
          </div>
        </dl>
      </section>

      {/* Sample data mode indicator — the only "control" on the page,
          and the only one that's interactive in the sense that the
          indicator reflects a real env value. */}
      <section className="rp-card rp-card--padded">
        <header className="rp-settings__head">
          <h2>Data source</h2>
          <p className="rp-muted">
            Whether the app is currently rendering sample data or hitting the backend.
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
          </div>
        </div>
      </section>
    </div>
  )
}
