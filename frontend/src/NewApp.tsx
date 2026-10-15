import { useEffect, useState } from 'react'
import { api, isMockMode, type DisputeListItem } from './api'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import Dashboard from './pages/Dashboard'
import DisputesList from './pages/DisputesList'
import DisputeDetail from './pages/DisputeDetail'
import FileDispute from './pages/FileDispute'
import Debate from './pages/Debate'
import RulingScreen from './pages/Ruling'
import EvidencePage from './pages/Evidence'
import Arguments from './pages/Arguments'
import Analytics from './pages/Analytics'
import Policies from './pages/Policies'
import AgentLogs from './pages/AgentLogs'
import Settings from './pages/Settings'

type Screen =
  | 'dashboard'
  | 'file-dispute'
  | 'disputes'
  | 'dispute-detail'
  | 'debate'
  | 'ruling'
  | 'evidence'
  | 'arguments'
  | 'analytics'
  | 'policies'
  | 'agent-logs'
  | 'settings'

const NAV_ITEMS: { key: Screen; label: string; icon: string }[] = [
  { key: 'dashboard', label: 'Dashboard', icon: '🏠' },
  { key: 'file-dispute', label: 'New Dispute', icon: '＋' },
  { key: 'disputes', label: 'Disputes', icon: '⏱' },
  { key: 'analytics', label: 'Analytics', icon: '📈' },
  { key: 'policies', label: 'Policies', icon: '📋' },
  { key: 'agent-logs', label: 'Agent Logs', icon: '🧠' },
  { key: 'settings', label: 'Settings', icon: '⚙' },
]

export default function NewApp() {
  const [screen, setScreen] = useState<Screen>('dashboard')
  const [disputes, setDisputes] = useState<DisputeListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeDisputeId, setActiveDisputeId] = useState<number | null>(null)
  const [debateId, setDebateId] = useState<number | null>(null)
  const [rulingId, setRulingId] = useState<number | null>(null)
  const [evidenceId, setEvidenceId] = useState<number | null>(null)
  const [argumentsId, setArgumentsId] = useState<number | null>(null)

  // Category filter shared between the analytics "Disputes by Category"
  // click and the DisputesList page. When the user clicks a category
  // bar, we set this and switch to the disputes screen.
  const [categoryFilter, setCategoryFilter] = useState<string>('all')

  useEffect(() => {
    let cancelled = false
    api
      .listDisputes()
      .then((items) => {
        if (cancelled) return
        setDisputes(items)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load disputes.')
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  /** Row click — go to the ruling for resolved/escalated disputes,
   * otherwise the debate screen. Mirrors the design's "click to
   * inspect" behaviour. */
  function openDispute(d: DisputeListItem) {
    setActiveDisputeId(d.id)
    setDebateId(d.id)
    if (d.status === 'resolved' || d.status === 'needs_human_review') {
      setRulingId(d.id)
      setScreen('ruling')
    } else {
      setScreen('debate')
    }
  }

  function createNew() {
    setScreen('file-dispute')
  }

  function viewAll() {
    setScreen('disputes')
  }

  /** Called by the wizard once the backend has accepted the dispute. */
  function onSubmitted(disputeId: number) {
    setDebateId(disputeId)
    setActiveDisputeId(disputeId)
    setScreen('debate')
    // Refresh the disputes list so the new one shows up everywhere else.
    api
      .listDisputes()
      .then(setDisputes)
      .catch(() => undefined)
  }

  function seeRuling(id: number) {
    setRulingId(id)
    setScreen('ruling')
  }

  function seeEvidence(id: number) {
    setEvidenceId(id)
    setScreen('evidence')
  }

  function seeArguments(id: number) {
    setArgumentsId(id)
    setScreen('arguments')
  }

  function pickCategory(category: string) {
    setCategoryFilter(category)
    setScreen('disputes')
  }

  const activeDispute = activeDisputeId
    ? disputes.find((d) => d.id === activeDisputeId) ?? null
    : null

  return (
    <div className="rp-app">
      <Sidebar
        activeKey={screen}
        onSelect={(k) => setScreen(k as Screen)}
        items={NAV_ITEMS}
        profile={{ name: 'Alex Tan', role: 'Support Agent' }}
      />
      <div className="rp-main">
        <TopBar />
        {isMockMode && (
          <div className="rp-mock-banner" role="status" aria-label="Sample data mode">
            Sample data mode — showing representative disputes and evidence. No backend connection required.
          </div>
        )}
        {screen === 'dashboard' && (
          <Dashboard
            disputes={disputes}
            loading={loading}
            error={error}
            onCreate={createNew}
            onSelect={openDispute}
            onViewAll={viewAll}
          />
        )}
        {screen === 'file-dispute' && (
          <FileDispute
            onCancel={() => setScreen('dashboard')}
            onSubmitted={onSubmitted}
          />
        )}
        {screen === 'disputes' && (
          <DisputesList
            disputes={disputes}
            loading={loading}
            error={error}
            onSelect={openDispute}
            onCreate={createNew}
            showAnalyticsPane
            analyticsOnSelectCategory={pickCategory}
            initialCategoryFilter={categoryFilter}
            onCategoryFilterChange={setCategoryFilter}
          />
        )}
        {screen === 'dispute-detail' && activeDispute && (
          <DisputeDetail
            dispute={activeDispute}
            onOpenDebate={(id) => {
              setDebateId(id)
              setActiveDisputeId(id)
              setScreen('debate')
            }}
            onOpenRuling={(id) => {
              setRulingId(id)
              setActiveDisputeId(id)
              setScreen('ruling')
            }}
          />
        )}
        {screen === 'dispute-detail' && !activeDispute && (
          <div className="rp-page">
            <div className="rp-card rp-card--padded">
              <h3 style={{ marginTop: 0 }}>No dispute selected</h3>
              <p className="rp-muted">
                Pick one from the dashboard, or file a new dispute to start the investigation.
              </p>
              <button className="rp-btn rp-btn--primary" onClick={createNew} type="button">
                + New Dispute
              </button>
            </div>
          </div>
        )}
        {screen === 'debate' && debateId !== null && (
          <Debate
            disputeId={debateId}
            onBack={() => {
              setScreen('disputes')
            }}
            onSeeRuling={seeRuling}
            onSeeEvidence={seeEvidence}
            onSeeArguments={seeArguments}
          />
        )}
        {screen === 'ruling' && rulingId !== null && (
          <RulingScreen
            disputeId={rulingId}
            onBack={() => {
              setScreen(debateId !== null ? 'debate' : 'disputes')
            }}
            onSeeEvidence={seeEvidence}
          />
        )}
        {screen === 'evidence' && evidenceId !== null && (
          <EvidencePage
            disputeId={evidenceId}
            onBack={() => {
              setScreen(rulingId !== null ? 'ruling' : debateId !== null ? 'debate' : 'disputes')
            }}
            onSeeRuling={seeRuling}
          />
        )}
        {screen === 'arguments' && argumentsId !== null && (
          <Arguments
            disputeId={argumentsId}
            onBack={() => {
              setScreen(debateId !== null ? 'debate' : 'disputes')
            }}
          />
        )}
        {screen === 'analytics' && (
          <Analytics
            disputes={disputes}
            onSelectCategory={pickCategory}
          />
        )}
        {screen === 'policies' && <Policies />}
        {screen === 'agent-logs' && (
          <AgentLogs
            disputes={disputes}
            loading={loading}
            error={error}
          />
        )}
        {screen === 'settings' && <Settings />}
      </div>
    </div>
  )
}
