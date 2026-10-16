import { useEffect, useMemo, useState } from 'react'
import { api, type Attachment, type ChatMessage, type Dispute, type EvidenceItem, type Ruling, type TripGps } from '../api'
import StatusBadge from '../components/StatusBadge'
import RouteMap from '../components/RouteMap'
import { ChatIcon, FileIcon, PhotoIcon, ReceiptIcon } from '../components/icons'
import { categoryLabel, disputeStatusVariant } from '../lib/status'
import { listRules, type RuleMeta } from '../lib/rules'

interface EvidenceProps {
  disputeId: number
  onBack: () => void
  onSeeRuling?: (id: number) => void
}

type Tab = 'trip' | 'policy' | 'analysis'

const TABS: { key: Tab; label: string }[] = [
  { key: 'trip', label: 'Trip Evidence' },
  { key: 'policy', label: 'Policy Rules' },
  { key: 'analysis', label: 'Analysis' },
]

/**
 * Screen 6 — Evidence & Policy Analysis.
 *
 * Three tabs:
 *   1. Trip Evidence  — route map (route_deviation), or a no-show
 *      timeline, or a chat log (property_damage / safety_incident).
 *      Always also shows the deterministic evidence tiles and the fare
 *      details.
 *   2. Policy Rules   — every rule in the system, with the ones the
 *      judge actually cited highlighted in pink.
 *   3. Analysis       — the Judge's reasoning text + the confidence
 *      score and its components.
 *
 * All numbers come straight from the backend; no fake values.
 */
export default function EvidencePage({ disputeId, onBack, onSeeRuling }: EvidenceProps) {
  const [tab, setTab] = useState<Tab>('trip')

  const [dispute, setDispute] = useState<Dispute | null>(null)
  const [ruling, setRuling] = useState<Ruling | null>(null)
  const [evidence, setEvidence] = useState<EvidenceItem[] | null>(null)
  const [gps, setGps] = useState<TripGps | null>(null)
  const [chat, setChat] = useState<ChatMessage[] | null>(null)
  const [attachments, setAttachments] = useState<Attachment[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    api
      .getDispute(disputeId)
      .then(async (d) => {
        if (cancelled) return
        setDispute(d)
        // Fetch the rest in parallel. Ruling may 404 if the dispute is
        // still resolving; we swallow that and only show a "ruling
        // pending" hint on the Analysis tab.
        const [ev, gp, ch, ru] = await Promise.allSettled([
          api.getEvidence(d.trip_id),
          api.getGps(d.trip_id),
          api.getTripChat(d.trip_id),
          api.getRuling(d.id),
        ])
        if (cancelled) return
        if (ev.status === 'fulfilled') setEvidence(ev.value)
        if (gp.status === 'fulfilled') setGps(gp.value)
        if (ch.status === 'fulfilled') setChat(ch.value)
        if (ru.status === 'fulfilled') setRuling(ru.value)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load dispute.')
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })

    api
      .listAttachments(disputeId)
      .then((items) => {
        if (!cancelled) setAttachments(items)
      })
      .catch(() => undefined)

    return () => {
      cancelled = true
    }
  }, [disputeId])

  // Pre-extract the route and no-show evidence items so the card
  // doesn't re-scan the list on every render.
  const routeEvidence = useMemo(
    () => evidence?.find((e) => e.type === 'route_deviation') ?? null,
    [evidence],
  )
  const fareEvidence = useMemo(
    () => evidence?.find((e) => e.type === 'fare_validation') ?? null,
    [evidence],
  )
  const noshowEvidence = useMemo(
    () => evidence?.find((e) => e.type === 'noshow') ?? null,
    [evidence],
  )
  const chatEvidence = useMemo(
    () => evidence?.find((e) => e.type === 'chat_analysis') ?? null,
    [evidence],
  )

  // Cited rule ids from the ruling (fallback to [] if not yet decided)
  const citedRuleIds = useMemo<string[]>(() => {
    const r = ruling?.rule_outcome as Record<string, unknown> | undefined
    if (!r) return []
    const rule = (r.rule ?? {}) as Record<string, unknown>
    const matched = rule.matched_rule_ids
    if (Array.isArray(matched)) return matched.filter((x): x is string => typeof x === 'string')
    return []
  }, [ruling])

  const confidence = ruling?.confidence ?? null
  const confidencePct = confidence !== null ? Math.round(confidence * 100) : null

  // The components sub-object is documented in backend/app/agents/judge.py
  const confidenceComponents = useMemo<Record<string, number>>(() => {
    const r = ruling?.rule_outcome as Record<string, unknown> | undefined
    if (!r) return {}
    const cc = (r.confidence_components ?? {}) as Record<string, number>
    return cc && typeof cc === 'object' ? cc : {}
  }, [ruling])

  // Whether the rule is currently in degraded mode (LLM unavailable)
  const llmDegraded = !!ruling?.llm_degraded

  // Decide which evidence block to show under "Trip Evidence"
  const category = dispute?.category ?? ''
  const showRoute = category === 'route_deviation' || category === 'fare_dispute'
  const showNoShow = category === 'no_show'
  const showChat = category === 'property_damage' || category === 'safety_incident'

  return (
    <div className="rp-page rp-evidence">
      <div className="rp-evidence__header">
        <div className="rp-evidence__title">
          <span className="rp-evidence__brandmark" aria-label="ryde">
            ryde
          </span>
          <div>
            <h1>
              Dispute #{disputeId}
              {dispute && (
                <StatusBadge
                  variant={disputeStatusVariant({
                    id: dispute.id,
                    trip_id: dispute.trip_id,
                    category: dispute.category,
                    status: dispute.status,
                    priority: dispute.priority,
                    claim_text: dispute.claim_text,
                    created_at: String(dispute.created_at),
                    outcome: null,
                    refund_amount: null,
                    llm_degraded: null,
                  })}
                />
              )}
            </h1>
            {dispute && <p>{categoryLabel(dispute.category)} · {dispute.claim_text}</p>}
          </div>
        </div>
        <div className="rp-evidence__header-actions">
          {ruling && onSeeRuling && (
            <button
              type="button"
              className="rp-btn rp-btn--ghost"
              onClick={() => onSeeRuling(disputeId)}
            >
              See ruling →
            </button>
          )}
          <button type="button" className="rp-btn rp-btn--ghost" onClick={onBack}>
            ← Back
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="rp-evidence__tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={`rp-evidence__tab ${tab === t.key ? 'is-active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error ? (
        <div className="rp-card rp-card--padded">
          <strong>Couldn't load this dispute.</strong>
          <p className="rp-muted">{error}</p>
        </div>
      ) : loading ? (
        <div className="rp-card rp-card--padded">Loading…</div>
      ) : (
        tab === 'trip' && (
          <TripEvidenceTab
            gps={gps}
            evidence={evidence ?? []}
            routeEvidence={routeEvidence}
            fareEvidence={fareEvidence}
            noshowEvidence={noshowEvidence}
            chatEvidence={chatEvidence}
            chat={chat ?? []}
            attachments={attachments}
            showRoute={showRoute}
            showNoShow={showNoShow}
            showChat={showChat}
          />
        )
      )}

      {!loading && tab === 'policy' && (
        <PolicyRulesTab citedRuleIds={citedRuleIds} rules={listRules()} />
      )}

      {!loading && tab === 'analysis' && (
        <AnalysisTab
          ruling={ruling}
          reasoning={ruling?.reasoning ?? null}
          confidencePct={confidencePct}
          confidenceComponents={confidenceComponents}
          llmDegraded={llmDegraded}
        />
      )}
    </div>
  )
}

/* ============================================================
 * Trip Evidence tab
 * ============================================================ */
interface TripEvidenceTabProps {
  gps: TripGps | null
  evidence: EvidenceItem[]
  routeEvidence: EvidenceItem | null
  fareEvidence: EvidenceItem | null
  noshowEvidence: EvidenceItem | null
  chatEvidence: EvidenceItem | null
  chat: ChatMessage[]
  attachments: Attachment[]
  showRoute: boolean
  showNoShow: boolean
  showChat: boolean
}

function TripEvidenceTab({
  gps,
  evidence,
  routeEvidence,
  fareEvidence,
  noshowEvidence,
  chatEvidence,
  chat,
  attachments,
  showRoute,
  showNoShow,
  showChat,
}: TripEvidenceTabProps) {
  return (
    <div className="rp-evidence__grid">
      {/* Route Comparison card — always present, content varies by case */}
      <section className="rp-evidence__card rp-evidence__card--wide">
        <h2>Route Comparison</h2>
        {showRoute && (
          <p className="rp-evidence__lede">
            GPS trace (red) vs. optimal route (blue, dashed). Pickup and drop-off are marked.
          </p>
        )}
        {showNoShow && (
          <p className="rp-evidence__lede">
            The driver did not complete a route on this trip. The timeline below shows the
            app events around the cancellation.
          </p>
        )}
        {showChat && (
          <p className="rp-evidence__lede">
            Route is not relevant for this category. The trip chat log and attached evidence
            are shown below.
          </p>
        )}

        {showRoute && <RouteMap gps={gps} />}

        {showRoute && (
          <div className="rp-evidence__legend" aria-label="Map legend">
            <span><i className="rp-evidence__swatch is-actual" /> Actual route</span>
            <span><i className="rp-evidence__swatch is-optimal" /> Optimal route</span>
            <span><i className="rp-evidence__swatch is-pickup" /> Pickup</span>
            <span><i className="rp-evidence__swatch is-dropoff" /> Dropoff</span>
          </div>
        )}

        {showNoShow && <NoShowTimeline gps={gps} evidence={noshowEvidence} />}

        {showChat && <ChatLog chat={chat} />}

        {/* Metric tiles under the route (route_deviation + fare_dispute) */}
        {showRoute && <RouteMetrics routeEvidence={routeEvidence} />}

        {/* Distance from pickup (no_show) */}
        {showNoShow && noshowEvidence && <NoShowProximity evidence={noshowEvidence} />}
      </section>

      {/* Fare Details card */}
      {fareEvidence && (
        <FareDetailsCard evidence={fareEvidence} />
      )}

      {/* Evidence Files card */}
      <EvidenceFilesCard
        evidence={evidence}
        chatEvidence={chatEvidence}
        showChat={showChat}
      />

      {/* User-supplied evidence (advisory, unverified) */}
      {attachments.length > 0 && <AttachmentsCard attachments={attachments} />}
    </div>
  )
}

/* ---------- Route metric tiles ---------- */
function RouteMetrics({ routeEvidence }: { routeEvidence: EvidenceItem | null }) {
  const d = (routeEvidence?.data ?? {}) as Record<string, unknown>
  const actualKm = num(d.actual_distance_km)
  const optimalKm = num(d.optimal_distance_km)
  const actualMin = num(d.actual_duration_min)
  const estimatedMin = num(d.estimated_duration_min)
  const extraPct =
    optimalKm !== null && optimalKm > 0 && actualKm !== null
      ? ((actualKm - optimalKm) / optimalKm) * 100
      : null
  const durPct =
    estimatedMin !== null && estimatedMin > 0 && actualMin !== null
      ? ((actualMin - estimatedMin) / estimatedMin) * 100
      : null

  const tiles: Array<{
    label: string
    value: string | null
    highlight?: boolean
    warn?: boolean
  }> = [
    { label: 'Actual distance', value: actualKm !== null ? `${actualKm.toFixed(1)} km` : null },
    { label: 'Optimal distance', value: optimalKm !== null ? `${optimalKm.toFixed(1)} km` : null },
    {
      label: 'Distance',
      value: extraPct !== null ? `${extraPct >= 0 ? '+' : ''}${extraPct.toFixed(0)}%` : null,
      highlight: true,
    },
    { label: 'Actual duration', value: actualMin !== null ? `${actualMin.toFixed(0)} min` : null },
    {
      label: 'Estimated duration',
      value: estimatedMin !== null ? `${estimatedMin.toFixed(0)} min` : null,
    },
    {
      label: 'Duration',
      value: durPct !== null ? `${durPct >= 0 ? '+' : ''}${durPct.toFixed(0)}%` : null,
      highlight: true,
    },
  ]

  return (
    <div className="rp-evidence__tiles">
      {tiles
        .filter((t) => t.value !== null)
        .map((t) => (
          <div
            key={t.label}
            className={`rp-evidence__tile ${t.highlight ? 'is-highlight' : ''} ${t.warn ? 'is-warn' : ''}`}
          >
            <span className="rp-evidence__tile-label">{t.label}</span>
            <span className="rp-evidence__tile-value">{t.value}</span>
          </div>
        ))}
    </div>
  )
}

/* ---------- No-show timeline ---------- */
function NoShowTimeline({
  gps,
  evidence,
}: {
  gps: TripGps | null
  evidence: EvidenceItem | null
}) {
  // The deterministic evidence analyzer returns:
  //   driver_arrived: bool
  //   driver_arrival_time: ISO string | null
  //   wait_duration_min: number
  //   min_distance_to_pickup_m: number
  //   fee: number
  // We use the GPS points to build a small event timeline
  // (driver movement, app events from speed changes, etc).
  const d = (evidence?.data ?? {}) as Record<string, unknown>
  const driverArrived = d.driver_arrived === true
  const arrivalTs = typeof d.driver_arrival_time === 'string' ? d.driver_arrival_time : null
  const waitMin = num(d.wait_duration_min) ?? 0
  const minDistM = num(d.min_distance_to_pickup_m)

  // Pull a handful of meaningful events from the GPS trace:
  //   - first GPS point (driver accepted)
  //   - closest point to pickup (driver arrived area)
  //   - last GPS point (driver stopped/cancelled)
  const events = useMemo(() => {
    if (!gps || gps.points.length === 0) return []
    const items: Array<{ ts: string; what: string; isDriver: boolean }> = []
    items.push({
      ts: gps.points[0].ts,
      what: 'Driver accepted and started moving toward pickup',
      isDriver: true,
    })
    if (driverArrived && arrivalTs) {
      items.push({
        ts: arrivalTs,
        what: 'Driver arrived at pickup area',
        isDriver: true,
      })
      if (waitMin > 0) {
        const end = new Date(new Date(arrivalTs).getTime() + waitMin * 60_000).toISOString()
        items.push({
          ts: end,
          what: `Driver waited ${waitMin.toFixed(1)} min and cancelled`,
          isDriver: true,
        })
      }
    } else {
      items.push({
        ts: gps.points[gps.points.length - 1].ts,
        what: 'Driver did not reach the pickup point and cancelled',
        isDriver: true,
      })
    }
    return items
  }, [gps, driverArrived, arrivalTs, waitMin])

  if (events.length === 0) {
    return (
      <p className="rp-muted">No GPS events recorded for this trip.</p>
    )
  }

  return (
    <>
      <ol className="rp-evidence__timeline" aria-label="Trip timeline">
        {events.map((e, i) => (
          <li key={i} className={e.isDriver ? 'is-driver' : ''}>
            <span className="dot" />
            <div className="body">
              <div className="when">{formatTs(e.ts)}</div>
              <div className="what">{e.what}</div>
            </div>
          </li>
        ))}
      </ol>
      {minDistM !== null && (
        <p className="rp-evidence__proximity">
          Closest the driver came to the rider:{' '}
          <strong>{minDistM >= 1000 ? `${(minDistM / 1000).toFixed(2)} km` : `${minDistM.toFixed(0)} m`}</strong>
        </p>
      )}
    </>
  )
}

function NoShowProximity({ evidence }: { evidence: EvidenceItem }) {
  const d = evidence.data as Record<string, unknown>
  const minM = num(d.min_distance_to_pickup_m)
  const fee = num(d.fee)
  return (
    <div className="rp-evidence__tiles">
      {minM !== null && (
        <div className="rp-evidence__tile">
          <span className="rp-evidence__tile-label">Closest distance</span>
          <span className="rp-evidence__tile-value">
            {minM >= 1000 ? `${(minM / 1000).toFixed(2)} km` : `${minM.toFixed(0)} m`}
          </span>
        </div>
      )}
      {fee !== null && (
        <div className="rp-evidence__tile is-warn">
          <span className="rp-evidence__tile-label">Cancellation fee</span>
          <span className="rp-evidence__tile-value">${fee.toFixed(2)}</span>
        </div>
      )}
    </div>
  )
}

/* ---------- Chat log ---------- */
function ChatLog({ chat }: { chat: ChatMessage[] }) {
  if (chat.length === 0) {
    return <p className="rp-evidence__chat-empty">No chat messages were logged for this trip.</p>
  }
  // We don't know which side is the rider vs the driver from the
  // frontend; the design renders them as two columns. We can label
  // messages by the sender's name: if the sender name contains
  // "Driver" we treat it as the driver side, otherwise as the rider.
  return (
    <ul className="rp-evidence__chat" aria-label="Trip chat log">
      {chat.map((m) => {
        const isDriver = /driver/i.test(m.sender)
        return (
          <li key={m.id} className={isDriver ? 'is-driver' : 'is-rider'}>
            <div className="head">
              <span>{m.sender}</span>
              <span>{formatTs(m.ts)}</span>
            </div>
            <div className="text">{m.text}</div>
          </li>
        )
      })}
    </ul>
  )
}

/* ---------- Fare Details card ---------- */
function FareDetailsCard({ evidence }: { evidence: EvidenceItem }) {
  // The fare analyzer returns:
  //   recomputed_base_fare, recomputed_expected_fare
  //   arithmetic_discrepancy, surge_multiplier, surge_premium
  //   promo_discount, quote_discrepancy
  // It does NOT split the fare into base/distance/time directly. The
  // base / distance / time lines are the *recomputed* components (per
  // backend/app/evidence/fare.py compute_fare). The trip model itself
  // exposes base_fare, per_km_rate, per_min_rate but we don't fetch
  // the trip here — so we show what's in the evidence and label the
  // surcharge as a separate row.
  const d = evidence.data as Record<string, unknown>
  const base = num(d.recomputed_base_fare)
  const expected = num(d.recomputed_expected_fare)
  const surge = num(d.surge_multiplier)
  const surgePremium = num(d.surge_premium)
  const discrepancy = num(d.arithmetic_discrepancy)
  const promo = num(d.promo_discount)
  const total = expected !== null && discrepancy !== null ? expected + discrepancy : expected
  const excess = discrepancy !== null && discrepancy > 0 ? discrepancy : null

  // Distance/time fare split isn't available in the evidence, so we
  // fold them into a single "Distance + time" line under the base fare
  // when the recomputed base is present. If it's missing, hide the row.
  const lines: Array<{ label: string; value: string; cls?: string }> = []
  if (base !== null) lines.push({ label: 'Base fare', value: `$${base.toFixed(2)}` })
  if (base !== null) lines.push({ label: 'Distance + time fare', value: `—` }) // not split by analyzer
  if (surge !== null && surge > 1.0001) {
    lines.push({ label: `Surge (${surge.toFixed(2)}x)`, value: surgePremium !== null ? `+$${surgePremium.toFixed(2)}` : '—' })
  }
  if (promo !== null && promo > 0) {
    lines.push({ label: 'Promo discount', value: `-$${promo.toFixed(2)}` })
  }
  if (total !== null) {
    lines.push({ label: 'Total charged', value: `$${total.toFixed(2)}`, cls: 'is-total' })
  }
  if (excess !== null) {
    lines.push({
      label: 'Potential excess',
      value: `+$${excess.toFixed(2)}`,
      cls: 'is-excess',
    })
  }

  if (lines.length === 0) {
    return null
  }

  return (
    <section className="rp-evidence__card">
      <h2>Fare Details</h2>
      <ul className="rp-evidence__fare">
        {lines.map((l, i) => (
          <li key={i} className={l.cls}>
            <span className="label">{l.label}</span>
            <span className="value">{l.value}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

/* ---------- Evidence Files card ---------- */
function EvidenceFilesCard({
  evidence,
  chatEvidence,
  showChat,
}: {
  evidence: EvidenceItem[]
  chatEvidence: EvidenceItem | null
  showChat: boolean
}) {
  // Map the deterministic evidence list to user-friendly file rows.
  // For property_damage / safety_incident the user attached no files,
  // so we show the chat_analysis row as the only evidence file. For
  // other categories we show every deterministic evidence item as a
  // named file row.
  const items: Array<{ icon: 'photo' | 'chat' | 'receipt' | 'file'; name: string; sub: string }> = []

  if (showChat) {
    // property_damage / safety_incident: chat log is the primary evidence
    items.push({
      icon: 'chat',
      name: 'Trip chat log',
      sub: chatEvidence ? chatEvidence.summary : 'Extracted from the trip chat history.',
    })
    items.push({
      icon: 'photo',
      name: 'Photo evidence',
      sub: 'No images were attached to this dispute.',
    })
  } else {
    for (const e of evidence) {
      items.push({
        icon: iconForType(e.type),
        name: labelForEvidence(e),
        sub: e.summary,
      })
    }
  }

  return (
    <section className="rp-evidence__card">
      <h2>Evidence Files</h2>
      {items.length === 0 ? (
        <p className="rp-muted">No evidence collected yet.</p>
      ) : (
        <ul className="rp-evidence__files">
          {items.map((it, i) => (
            <li key={i} className="rp-evidence__file">
              <span className="file-icon" aria-hidden>
                {iconRender(it.icon)}
              </span>
              <span className="file-text">
                <span className="file-name">{it.name}</span>
                <span className="file-sub">{it.sub}</span>
              </span>
              <span className="file-chevron" aria-hidden>
                ›
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function iconForType(t: string): 'photo' | 'chat' | 'receipt' | 'file' {
  if (t === 'route_deviation') return 'photo'
  if (t === 'noshow') return 'chat'
  if (t === 'fare_validation') return 'receipt'
  return 'file'
}

function labelForEvidence(e: EvidenceItem): string {
  switch (e.type) {
    case 'route_deviation':
      return 'Route deviation report'
    case 'noshow':
      return 'No-show analysis'
    case 'fare_validation':
      return 'Fare validation report'
    case 'chat_analysis':
      return 'Chat analysis'
    case 'history':
      return 'Account history profile'
    default:
      return e.type
  }
}

function iconRender(name: 'photo' | 'chat' | 'receipt' | 'file') {
  if (name === 'photo') return <PhotoIcon size={16} />
  if (name === 'chat') return <ChatIcon size={16} />
  if (name === 'receipt') return <ReceiptIcon size={16} />
  return <FileIcon size={16} />
}

/* ---------- User-supplied attachments card ---------- */
function AttachmentsCard({ attachments }: { attachments: Attachment[] }) {
  return (
    <section className="rp-evidence__card rp-evidence__card--wide">
      <h2>User Evidence</h2>
      <p className="rp-evidence__lede">
        Files supplied by the user. These are advisory only — they are described by the
        analysis agent but are never treated as verified.
      </p>
      <ul className="rp-evidence__files">
        {attachments.map((a) => {
          const analysis = (a.analysis ?? {}) as Record<string, unknown>
          const description = typeof analysis.description === 'string' ? analysis.description : null
          return (
            <li key={a.id} className="rp-evidence__file">
              <span className="file-icon" aria-hidden>
                {a.kind === 'receipt' ? <ReceiptIcon size={16} /> : a.kind === 'chat_log' ? <ChatIcon size={16} /> : <PhotoIcon size={16} />}
              </span>
              <span className="file-text">
                <span className="file-name">
                  {a.filename}
                  <span className="rp-evidence__unverified">unverified</span>
                </span>
                <span className="file-sub">
                  {description ?? 'Analysis unavailable — this file was not interpreted.'}
                </span>
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

/* ============================================================
 * Policy Rules tab
 * ============================================================ */
function PolicyRulesTab({
  citedRuleIds,
  rules,
}: {
  citedRuleIds: string[]
  rules: RuleMeta[]
}) {
  const cited = new Set(citedRuleIds)
  return (
    <div className="rp-evidence__card rp-evidence__card--wide">
      <h2>Policy Rules</h2>
      <p className="rp-evidence__lede">
        Every deterministic rule the system can apply. Rules highlighted in pink are the
        ones the Judge cited in the ruling for this dispute.
      </p>
      {rules.length === 0 ? (
        <p className="rp-evidence__rules-empty">No rules configured.</p>
      ) : (
        <ul className="rp-evidence__rules">
          {rules.map((r) => {
            const isCited = cited.has(r.id)
            return (
              <li key={r.id} className={`rp-evidence__rule ${isCited ? 'is-cited' : ''}`}>
                <span className="rule-id">{r.id}</span>
                <div className="rule-body">
                  <span className="rule-title">
                    {r.title}
                    {isCited && <span className="rule-cited-badge">· Cited in ruling</span>}
                  </span>
                  <span className="rule-blurb">{r.blurb}</span>
                </div>
              </li>
            )
          })}
          {/* If the judge cited a rule we don't have a static entry for, surface it
              so we never silently drop something. */}
          {citedRuleIds
            .filter((id) => !rules.find((r) => r.id === id))
            .map((id) => (
              <li key={id} className="rp-evidence__rule is-cited">
                <span className="rule-id">{id}</span>
                <div className="rule-body">
                  <span className="rule-title">
                    {id}
                    <span className="rule-cited-badge">· Cited in ruling</span>
                  </span>
                  <span className="rule-blurb">
                    Rule id from the backend's deterministic policy. The full description
                    lives in <code>backend/rules/rules.yaml</code>.
                  </span>
                </div>
              </li>
            ))}
        </ul>
      )}
    </div>
  )
}

/* ============================================================
 * Analysis tab
 * ============================================================ */
function AnalysisTab({
  ruling,
  reasoning,
  confidencePct,
  confidenceComponents,
  llmDegraded,
}: {
  ruling: Ruling | null
  reasoning: string | null
  confidencePct: number | null
  confidenceComponents: Record<string, number>
  llmDegraded: boolean
}) {
  return (
    <div className="rp-evidence__card rp-evidence__card--wide rp-evidence__analysis">
      <h2>Analysis</h2>
      {ruling === null ? (
        <p className="rp-muted">
          The Judge's reasoning will appear here once the dispute is resolved. If this
          dispute is still in progress, please check back in a moment.
        </p>
      ) : (
        <>
          {llmDegraded && (
            <div className="rp-evidence__llm-warning">
              The LLM was unavailable when this dispute was decided. The Judge fell back
              to the deterministic rule outcome. Numbers are accurate; tone may be less
              natural.
            </div>
          )}

          <p className="rp-evidence__reasoning">
            {reasoning ?? 'No reasoning was produced.'}
          </p>

          {confidencePct !== null && (
            <div className="rp-evidence__confidence" aria-label="Judge confidence">
              <span>Judge confidence</span>
              <span className="rp-evidence__confidence-bar" aria-hidden>
                <span
                  className="rp-evidence__confidence-bar-fill"
                  style={{ width: `${Math.max(0, Math.min(100, confidencePct))}%` }}
                />
              </span>
              <span className="rp-evidence__confidence-value">{confidencePct}%</span>
            </div>
          )}

          {Object.keys(confidenceComponents).length > 0 && (
            <div className="rp-evidence__components" aria-label="Confidence components">
              {Object.entries(confidenceComponents).map(([k, v]) => (
                <div key={k} className="rp-evidence__component">
                  <span className="rp-evidence__component-label">
                    {labelForComponent(k)}
                  </span>
                  <span className="rp-evidence__component-value">
                    {typeof v === 'number' ? v.toFixed(2) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="rp-evidence__analysis-meta">
            <span>
              <strong>Outcome:</strong>{' '}
              {ruling ? outcomePretty(ruling.outcome) : '—'}
            </span>
            <span>
              <strong>Refund:</strong> $
              {ruling ? ruling.refund_amount.toFixed(2) : '0.00'}
            </span>
            <span>
              <strong>Evidence used:</strong> {ruling.evidence_ids.length}
            </span>
          </div>
        </>
      )}
    </div>
  )
}

function labelForComponent(key: string): string {
  switch (key) {
    case 'agreement':
      return 'Agreement'
    case 'evidence_strength':
      return 'Evidence strength'
    case 'citation_validity':
      return 'Citation validity'
    case 'history_risk':
      return 'History risk'
    case 'fraud_penalty':
      return 'Fraud penalty'
    default:
      return key.replace(/_/g, ' ')
  }
}

function outcomePretty(o: string): string {
  if (o === 'full_refund') return 'Full refund'
  if (o === 'partial_refund') return 'Partial refund'
  if (o === 'no_refund') return 'No refund'
  return o
}

/* ============================================================
 * Helpers
 * ============================================================ */
function num(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string' && v !== '') {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }
  return null
}

function formatTs(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}
