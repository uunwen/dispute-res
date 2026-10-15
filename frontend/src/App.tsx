import { useEffect, useRef, useState } from 'react'
import './App.css'
import { api, type AgentMessage, type CategoryMeta, type DisputeListItem, type EvidenceItem, type Ruling, type Trip, type TripGps } from './api'
import AgentFeed from './components/AgentFeed'
import DisputeForm from './components/DisputeForm'
import DisputeList from './components/DisputeList'
import EvidencePanel from './components/EvidencePanel'
import RouteMap from './components/RouteMap'
import RulingCard from './components/RulingCard'
import Toast from './components/Toast'

interface ActiveDispute {
  id: number
  tripId: number
  category: string
  status: string
}

/**
 * Legacy live-debate view, kept so the multi-agent investigation flow still
 * works end-to-end. The new shell (NewApp) is the default entry point;
 * this component is retained for reference.
 */
export default function LegacyLiveDebate() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [disputes, setDisputes] = useState<DisputeListItem[]>([])
  const [categories, setCategories] = useState<CategoryMeta[]>([])
  const [selectedTripId, setSelectedTripId] = useState<number | null>(null)
  const [category, setCategory] = useState<string>('')
  const [claimText, setClaimText] = useState<string>('')
  const [filing, setFiling] = useState(false)

  const [activeDispute, setActiveDispute] = useState<ActiveDispute | null>(null)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [ruling, setRuling] = useState<Ruling | null>(null)
  const [evidence, setEvidence] = useState<EvidenceItem[]>([])
  const [gps, setGps] = useState<TripGps | null>(null)
  const [thinking, setThinking] = useState(false)
  const [loadingEvidence, setLoadingEvidence] = useState(false)
  const [highlightedId, setHighlightedId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    api.listTrips().then(setTrips).catch((e) => setError(String(e)))
    api.listDisputes().then(setDisputes).catch((e) => setError(String(e)))
    api.fetchCategories()
      .then((cats) => {
        setCategories(cats)
        const first = cats.find((c) => c.supported) ?? cats[0]
        if (first) {
          setCategory(first.value)
          setClaimText(first.example_claim)
        }
      })
      .catch((e) => setError(String(e)))
    return () => esRef.current?.close()
  }, [])

  function closeStream() {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
  }

  function openStream(disputeId: number): Promise<void> {
    return new Promise((resolve) => {
      closeStream()
      const es = new EventSource(api.streamUrl(disputeId))
      es.onopen = () => resolve()
      es.onmessage = (e) => {
        let data: any
        try {
          data = JSON.parse(e.data)
        } catch {
          return
        }
        if (data.type === 'agent_message') {
          setMessages((prev) => [...prev, data as AgentMessage])
        } else if (data.type === 'resolving') {
          setThinking(true)
        } else if (data.type === 'ruling_ready') {
          setThinking(false)
          refreshAfterRuling(disputeId)
        }
      }
      esRef.current = es
    })
  }

  async function refreshAfterRuling(disputeId: number) {
    try {
      setRuling(await api.getRuling(disputeId))
      setMessages(await api.getMessages(disputeId))
      setDisputes(await api.listDisputes())
    } catch (e) {
      setError(String(e))
    }
  }

  async function loadEvidence(tripId: number) {
    setLoadingEvidence(true)
    try {
      setEvidence(await api.getEvidence(tripId))
    } catch (e) {
      setError(String(e))
      setEvidence([])
    } finally {
      setLoadingEvidence(false)
    }
  }

  async function loadGps(tripId: number) {
    try {
      setGps(await api.getGps(tripId))
    } catch {
      setGps(null)
    }
  }

  async function handleFileResolve() {
    if (selectedTripId === null) return
    setFiling(true)
    setError(null)
    try {
      const trip = trips.find((t) => t.id === selectedTripId)
      if (!trip) throw new Error('trip not found')
      const dispute = await api.createDispute({
        trip_id: selectedTripId,
        category,
        claim_text: claimText,
        filed_by: trip.rider_id,
      })

      setMessages([])
      setRuling(null)
      setThinking(true)
      setHighlightedId(null)
      setActiveDispute({ id: dispute.id, tripId: selectedTripId, category, status: 'open' })
      loadEvidence(selectedTripId)
      loadGps(selectedTripId)

      await openStream(dispute.id)
      await api.resolveDispute(dispute.id)

      setDisputes(await api.listDisputes())
    } catch (e) {
      setError(String(e))
    } finally {
      setFiling(false)
    }
  }

  async function handleResolveExisting() {
    if (!activeDispute) return
    const id = activeDispute.id
    setError(null)
    setMessages([])
    setRuling(null)
    setThinking(true)
    try {
      await openStream(id)
      await api.resolveDispute(id)
    } catch (e) {
      setError(String(e))
    }
  }

  async function handleReRun() {
    if (!activeDispute) return
    const id = activeDispute.id
    setError(null)
    setMessages([])
    setRuling(null)
    setThinking(true)
    try {
      await openStream(id)
      await api.resolveDispute(id, true)
    } catch (e) {
      setError(String(e))
    }
  }

  async function handleSelectDispute(d: DisputeListItem) {
    setError(null)
    closeStream()
    setThinking(false)
    setMessages([])
    setRuling(null)
    setHighlightedId(null)
    setActiveDispute({ id: d.id, tripId: d.trip_id, category: d.category, status: d.status })

    try {
      setMessages(await api.getMessages(d.id))
    } catch (e) {
      setError(String(e))
    }
    try {
      setRuling(await api.getRuling(d.id))
    } catch {
      setRuling(null)
    }
    loadEvidence(d.trip_id)
    loadGps(d.trip_id)
  }

  function handleCategoryChange(c: string) {
    setCategory(c)
    const meta = categories.find((m) => m.value === c)
    setClaimText(meta?.example_claim ?? '')
  }

  const showMap = activeDispute !== null && activeDispute.category !== 'fare_dispute'
  const degraded = ruling?.llm_degraded ?? false

  return (
    <div className="app">
      <aside className="col left">
        <DisputeForm
          trips={trips}
          categories={categories}
          selectedTripId={selectedTripId}
          category={category}
          claimText={claimText}
          filing={filing}
          onTripChange={setSelectedTripId}
          onCategoryChange={handleCategoryChange}
          onClaimTextChange={setClaimText}
          onSubmit={handleFileResolve}
        />
        <DisputeList disputes={disputes} activeId={activeDispute?.id ?? null} onSelect={handleSelectDispute} />
      </aside>

      <main className="col middle">
        <AgentFeed
          messages={messages}
          thinking={thinking}
          hasDispute={activeDispute !== null}
          disputeStatus={activeDispute?.status ?? null}
          degraded={degraded}
          onResolve={handleResolveExisting}
          onEvidenceClick={setHighlightedId}
        />
      </main>

      <aside className="col right">
        <h2>Evidence & Ruling</h2>
        <RulingCard ruling={ruling} loading={thinking} onReRun={handleReRun} />
        {showMap && <RouteMap gps={gps} />}
        <EvidencePanel
          evidence={evidence}
          highlightedId={highlightedId}
          loading={loadingEvidence}
          hasDispute={activeDispute !== null}
          category={activeDispute?.category ?? null}
        />
      </aside>

      <Toast error={error} onClose={() => setError(null)} />
    </div>
  )
}

/* The new shell is exported as a named export so it can replace App() without
 * touching this file again. */
export { default as NewApp } from './NewApp'
