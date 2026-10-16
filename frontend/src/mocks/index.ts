import type {
  AccountItem,
  AgentMessage,
  CategoryMeta,
  ChatMessage,
  Dispute,
  DisputeListItem,
  DisputeReview,
  EvidenceItem,
  Formula,
  ListDisputesParams,
  PolicySection,
  QueueItem,
  RuleItem,
  Ruling,
  Settings,
  Trip,
  TripGps,
} from '../api'
import { TRIPS, GPS_FIXTURES, CHAT_FIXTURES } from './fixtures'
import { EVIDENCE_BY_TRIP } from './evidence'
import { DISPUTES_1_6 } from './disputes1'
import { DISPUTES_7_12 } from './disputes2'
import type { DisputeSpec } from './types'

/* ============================================================
 * Mock API — sample-data mode
 * ============================================================
 * Every function mirrors a method on the real `api` object.
 * When VITE_USE_MOCK === 'true', api.ts swaps the real fetch-based
 * implementation for this object. All data is static and in-memory.
 */

export const ALL_SPECS: DisputeSpec[] = [...DISPUTES_1_6, ...DISPUTES_7_12]

/* -- Category metadata (mirrors GET /meta/categories) -- */
const CATEGORIES: CategoryMeta[] = [
  { value: 'route_deviation', label: 'Route Deviation', example_claim: 'Driver took a longer route than necessary.', supported: true },
  { value: 'no_show', label: 'No-show', example_claim: 'Driver never arrived at the pickup location.', supported: true },
  { value: 'fare_dispute', label: 'Fare Dispute', example_claim: 'I was charged more than the quoted fare.', supported: true },
  { value: 'property_damage', label: 'Property Damage', example_claim: 'My belongings were damaged during the trip.', supported: true },
  { value: 'safety_incident', label: 'Safety Incident', example_claim: 'I felt unsafe during the trip.', supported: true },
]

/* -- Deterministic formulas (mirrors GET /meta/formulas) -- */
const FORMULAS: Formula[] = [
  {
    id: 'confidence_score',
    name: 'Judge confidence score',
    category: 'Ruling',
    formula: 'confidence = 0.35·agreement + 0.30·evidence_strength + 0.20·citation_validity + 0.15·history_risk',
    description:
      'Documented confidence formula (not LLM self-reported). All components are in [0, 1]. The result is clamped to [0, 1] and a fraud penalty is then subtracted.',
    variables: [
      { name: 'agreement', definition: '1.0 when the LLM and the rules engine agree on the outcome, otherwise 0.3.' },
      { name: 'evidence_strength', definition: 'Mean strength of the cited deciding evidence items.' },
      { name: 'citation_validity', definition: "Fraction of the LLM's cited evidence ids that actually exist." },
      { name: 'history_risk', definition: 'Maximum abuse-risk score across the rider and driver.' },
    ],
    source: 'app/agents/judge.py:compute_confidence',
  },
  {
    id: 'rule_llm_reconcile',
    name: 'Rule / LLM refund reconciliation',
    category: 'Ruling',
    formula: 'final_amount = min(rule_amount, max(llm_amount, 0.0))',
    description:
      'The rules engine is the source of truth for the amount. The LLM may reduce the refund but never exceed the rule amount.',
    variables: [
      { name: 'rule_amount', definition: 'Refund amount from the deterministic rules engine.' },
      { name: 'llm_amount', definition: 'Refund amount proposed by the Judge LLM.' },
    ],
    source: 'app/agents/judge.py:reconcile',
  },
  {
    id: 'fraud_penalty',
    name: 'Fraud confidence penalty',
    category: 'Ruling',
    formula: 'fraud_penalty = fraud_penalty_weight · risk  (only when favored side\'s risk ≥ threshold)',
    description:
      'When the side being favored has fraud risk at or above the threshold, confidence is reduced. The signal is advisory: it never changes the outcome. Defaults: weight = 0.2, threshold = 0.5.',
    variables: [
      { name: 'fraud_penalty_weight', definition: '0.2 (configurable via settings).' },
      { name: 'fraud_penalty_threshold', definition: '0.5 (configurable via settings).' },
    ],
    source: 'app/agents/judge.py:_fraud_penalty',
  },
  {
    id: 'history_abuse_risk',
    name: 'Account abuse-risk profile',
    category: 'Evidence',
    formula: 'abuse_risk = 0.50·dispute_factor + 0.25·(1 - win_rate) + 0.25·rating_factor',
    description: 'Weighted combination of dispute frequency, loss rate and rating.',
    variables: [
      { name: 'dispute_factor', definition: 'min(1, dispute_count / 8).' },
      { name: 'win_rate', definition: 'won_count / resolved_count, or 0.5 when nothing is resolved.' },
      { name: 'rating_factor', definition: 'max(0, 1 - rating / 5).' },
    ],
    source: 'app/evidence/history.py:compute_history_profile',
  },
  {
    id: 'fare_recompute',
    name: 'Fare recomputation',
    category: 'Evidence',
    formula:
      'recomputed_base = base_fare + per_km_rate·distance + per_min_rate·duration\nrecomputed_expected = recomputed_base·surge_multiplier - promo_discount\narithmetic_discrepancy = actual_fare - recomputed_expected',
    description:
      'Pure arithmetic fare validation. A non-zero discrepancy beyond 0.011 flags a fare miscalculation; otherwise surge/promo are identified.',
    variables: [
      { name: 'surge_premium', definition: 'recomputed_base · (surge_multiplier - 1).' },
      { name: 'quote_discrepancy', definition: 'actual_fare - estimated_fare.' },
    ],
    source: 'app/evidence/fare.py:compute_fare',
  },
  {
    id: 'route_deviation',
    name: 'Route deviation detection',
    category: 'Evidence',
    formula:
      'fraction_outside = outside_buffer_points / total_points\nextra_distance = actual_distance - optimal_distance\nbad_faith = fraction_outside ≥ min_fraction AND extra_distance ≥ min_extra_km AND not traffic_signal',
    description:
      'GPS fixes are projected to EPSG:3414 (SVY21, metres) with pyproj and classified inside/outside a buffer around the optimal route.',
    variables: [
      { name: 'haversine_km', definition: 'Great-circle distance between two lat/lng points.' },
      { name: 'traffic_signal', definition: 'avg speed on-route before deviation < traffic_speed_kmh (15 km/h).' },
    ],
    source: 'app/evidence/route.py:compute_route_deviation',
  },
  {
    id: 'noshow_detection',
    name: 'No-show classification',
    category: 'Evidence',
    formula: 'driver_arrived = min_distance_to_pickup ≤ proximity_m\ncancellation_fee_valid = driver_arrived AND wait_duration ≥ min_wait_min',
    description:
      'A no-show is classified from GPS distance to the pickup point and the duration the driver stayed within the proximity threshold.',
    variables: [
      { name: 'proximity_m', definition: '100 m (configurable).' },
      { name: 'min_wait_min', definition: '5 min (configurable).' },
    ],
    source: 'app/evidence/noshow.py:compute_noshow',
  },
  {
    id: 'fraud_risk',
    name: 'Fraud risk scoring',
    category: 'Fraud',
    formula: 'risk = Σ fired_rule_weight, clamped to [0, 1]',
    description: 'Rule-based (no LLM) advisory scoring. Fired rules add their weight to the relevant side\'s risk.',
    variables: [
      { name: 'dispute_frequency', definition: 'weight 0.3 — ≥ threshold disputes within N days.' },
      { name: 'win_rate_anomaly', definition: 'weight 0.2 — win rate below threshold.' },
      { name: 'repeat_deviation', definition: 'weight 0.4 — driver in ≥ threshold route-deviation disputes.' },
      { name: 'young_account', definition: 'weight 0.2 — account age below N days.' },
      { name: 'claim_evidence_contradiction', definition: 'weight 0.3 — claim contradicted by deterministic evidence.' },
    ],
    source: 'app/agents/fraud.py:_WEIGHTS',
  },
  {
    id: 'queue_priority',
    name: 'Queue priority (SLA & routing)',
    category: 'Queue',
    formula: 'priority = safety·1e15 + amount·1e8 + age_seconds·1.0',
    description: 'Redis sorted-set score. Weights are chosen so safety > amount > age for realistic fares and ages.',
    variables: [
      { name: 'safety', definition: '1 if category is safety_incident, else 0.' },
      { name: 'amount', definition: "The trip's disputed amount (actual fare)." },
      { name: 'age_seconds', definition: 'Seconds since the dispute was filed.' },
    ],
    source: 'app/queue/queue.py:priority_score',
  },
  {
    id: 'chat_sentiment',
    name: 'Chat sentiment (VADER)',
    category: 'Evidence',
    formula: 'compound = mean(VADER compound score per message)',
    description:
      'Deterministic average of per-message VADER sentiment. Optional LLM extraction adds threats, admissions, agreements, disagreements and key claims with message-id citations.',
    variables: [],
    source: 'app/evidence/chat.py:vader_sentiment',
  },
]

/* -- Policy sections (mirrors GET /meta/policies) -- */
const POLICIES: PolicySection[] = [
  { id: '1.1', title: 'General Principle', source: 'route_deviation.md', tag: null, text: 'Drivers are permitted to reroute from the GPS-recommended path in response to real-time traffic conditions, road closures, or congestion. However, the rider must be informed of any deviation.' },
  { id: '2.2', title: 'Cancellation Fee', source: 'no_show_fee.md', tag: null, text: 'A no-show cancellation fee of $5.00 is charged to the rider when the driver cancels after the free wait period. The cancellation fee is transferred to the driver as compensation for time and fuel.' },
  { id: '3.3', title: 'Refund Eligibility', source: 'fare_surge_promo.md', tag: null, text: 'If the surge multiplier increases between quote and trip start and the rider is not notified, the rider is eligible for a full refund of the surge differential.' },
  { id: '7.1', title: 'Route Deviation Without Notification', source: 'precedent.md', tag: 'precedent', text: 'Case DISP-2026-0089: Driver rerouted without notifying the rider. Partial refund of excess distance fare.' },
  { id: '7.3', title: 'No-Show Cancellation Without Contact Attempt', source: 'precedent.md', tag: 'precedent', text: 'Case DISP-2026-0211: Driver cancelled as no-show without any contact attempt. Cancellation fee voided and refunded.' },
]

/* -- Deterministic rules (mirrors GET /meta/rules) -- */
const RULES: RuleItem[] = [
  { id: 'route_deviation_minor', category: 'route_deviation', citation: '1.3', conditions: '(deviation_km if deviation_km else extra_distance_km) <= 1', outcome: 'no_action', amount: '0' },
  { id: 'route_deviation_major', category: 'route_deviation', citation: '1.3', conditions: '(deviation_km if deviation_km else extra_distance_km) > 1 and not (traffic_justified if traffic_justified != None else traffic_signal)', outcome: 'full_refund', amount: 'excess_distance_fare if excess_distance_fare > 0 else fare * min(1, extra_distance_km / total_km)' },
  { id: 'no_show_driver_never_arrived', category: 'no_show', citation: '2.4', conditions: 'not driver_arrived', outcome: 'full_refund', amount: 'fee' },
  { id: 'no_show_contact_obligation_violated', category: 'no_show', citation: '2.3', conditions: 'driver_arrived and not contact_obligation_met', outcome: 'full_refund', amount: 'fee' },
  { id: 'surge_increase_not_notified', category: 'fare_dispute', citation: '3.3', conditions: 'surge_increased and not rider_notified and surge_differential > 0', outcome: 'full_refund', amount: 'surge_differential' },
]

/* -- Effective settings (mirrors GET /meta/settings) -- */
const SETTINGS: Settings = {
  models: [
    { agent: 'RiderAdvocate', model: 'ryde/llm-rider-advocate-v1', purpose: "Presents the rider's case" },
    { agent: 'DriverAdvocate', model: 'ryde/llm-driver-advocate-v1', purpose: "Presents the driver's defense" },
    { agent: 'Judge', model: 'ryde/llm-judge-v1', purpose: 'Evaluates evidence and applies policy' },
  ],
  llm_mock: false,
  policy_version: 'v2.1',
  policy_numbers: [
    { key: 'noshow_cancellation_fee', label: 'Cancellation fee', value: '$5.00', source: 'no_show_fee.md §2.2' },
    { key: 'noshow_min_wait_min', label: 'Free wait time', value: '5 minutes', source: 'no_show_fee.md §2.1' },
    { key: 'route_buffer_m', label: 'Off-route buffer', value: '100 m', source: 'route_deviation.md §1.3' },
    { key: 'route_escalate_km', label: 'Major detour threshold', value: '2 km extra', source: 'route_deviation.md §1.3' },
    { key: 'fare_tolerance_pct', label: 'Fare tolerance', value: '5%', source: 'fare_surge_promo.md §3.3' },
  ],
  thresholds: [
    { key: 'abuse_risk_threshold', label: 'Abuse-risk threshold', value: '0.6', source: 'app/config.py' },
    { key: 'fraud_dispute_frequency_threshold', label: 'Fraud dispute threshold', value: '3', source: 'app/config.py' },
    { key: 'fraud_penalty_threshold', label: 'Fraud penalty threshold', value: '0.5', source: 'app/config.py' },
    { key: 'fraud_penalty_weight', label: 'Fraud penalty weight', value: '0.2', source: 'app/config.py' },
  ],
  escalation: [
    { key: 'escalation_enabled', label: 'Escalation enabled', value: 'true', source: 'app/config.py' },
    { key: 'escalation_low_value', label: 'Low-value threshold', value: '$10.00', source: 'app/config.py' },
    { key: 'escalation_high_value', label: 'High-value threshold', value: '$50.00', source: 'app/config.py' },
    { key: 'escalation_threshold', label: 'Confidence threshold', value: '0.8', source: 'app/config.py' },
  ],
}

/* -- Build derived objects from specs -- */

function specToDisputeListItem(spec: DisputeSpec): DisputeListItem {
  return {
    id: spec.id,
    trip_id: spec.trip_id,
    category: spec.category,
    status: spec.status,
    priority: spec.priority,
    claim_text: spec.claim_text,
    created_at: spec.created_at,
    external_id: spec.external_id ?? null,
    outcome: spec.outcome,
    refund_amount: spec.refund_amount,
    llm_degraded: spec.llm_degraded,
    confidence: spec.ruling ? spec.ruling.confidence : null,
    ruling_created_at: spec.ruling ? spec.ruling.created_at : null,
  }
}

function specToDispute(spec: DisputeSpec): Dispute {
  return {
    id: spec.id,
    trip_id: spec.trip_id,
    filed_by: spec.filed_by,
    category: spec.category,
    claim_text: spec.claim_text,
    status: spec.status,
    priority: spec.priority,
    created_at: spec.created_at,
  }
}

function specToMessages(spec: DisputeSpec): AgentMessage[] {
  const msgs: AgentMessage[] = []
  let mid = spec.id * 100

  function push(msg: {
    sender: string
    recipient: string
    message_type: string
    content: unknown
  }, createdAt: string) {
    mid += 1
    msgs.push({
      id: mid,
      dispute_id: spec.id,
      sender: msg.sender,
      recipient: msg.recipient,
      message_type: msg.message_type,
      content: msg.content as Record<string, unknown>,
      created_at: createdAt,
    })
  }

  // Fraud signal (if present) comes first
  if (spec.fraud_signal) {
    push(spec.fraud_signal, spec.created_at)
  }

  // Rider opening
  push(spec.rider_opening, spec.created_at)

  // Driver opening
  const driverOpenTs = new Date(new Date(spec.created_at).getTime() + 30_000).toISOString()
  push(spec.driver_opening, driverOpenTs)

  // Rebuttals (if present)
  if (spec.rider_rebuttal) {
    const ts = new Date(new Date(driverOpenTs).getTime() + 30_000).toISOString()
    push(spec.rider_rebuttal, ts)
  }
  if (spec.driver_rebuttal) {
    const ts = new Date(new Date(spec.created_at).getTime() + 90_000).toISOString()
    push(spec.driver_rebuttal, ts)
  }

  // Escalation (if present) — comes after the judge would rule
  if (spec.escalation) {
    const ts = spec.ruling?.created_at ?? new Date(new Date(spec.created_at).getTime() + 120_000).toISOString()
    push(spec.escalation, ts)
  }

  return msgs
}

function specToRuling(spec: DisputeSpec): Ruling | null {
  if (!spec.ruling) return null
  const r = spec.ruling
  return {
    id: r.id,
    dispute_id: spec.id,
    outcome: r.outcome,
    refund_amount: r.refund_amount,
    confidence: r.confidence,
    reasoning: r.reasoning,
    rule_outcome: r.rule_outcome as unknown as Record<string, unknown>,
    evidence_ids: r.evidence_ids,
    escalated: r.escalated,
    human_review_summary: (r.human_review_summary as unknown as Ruling['human_review_summary']) ?? null,
    llm_degraded: r.llm_degraded,
    created_at: r.created_at,
  }
}

/* -- The mock API object -- */

function delay<T>(value: T, ms = 50): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms))
}

export const mockApi = {
  listTrips: () => delay<Trip[]>(TRIPS),

  listDisputes: (params?: ListDisputesParams) => {
    let specs = ALL_SPECS
    if (params?.account_id != null) {
      const id = params.account_id
      specs = specs.filter((s) => {
        const trip = TRIPS.find((t) => t.id === s.trip_id)
        return s.filed_by === id || trip?.rider_id === id || trip?.driver_id === id
      })
    }
    return delay<DisputeListItem[]>(specs.map(specToDisputeListItem))
  },

  fetchCategories: () => delay<CategoryMeta[]>(CATEGORIES),

  getDispute: (id: number) => {
    const spec = ALL_SPECS.find((s) => s.id === id)
    if (!spec) return Promise.reject(new Error(`HTTP 404: Dispute ${id} not found`))
    return delay<Dispute>(specToDispute(spec))
  },

  createDispute: (body: { trip_id: number; category: string; claim_text: string; filed_by_role?: 'rider' | 'driver' }) => {
    // In mock mode, creating a dispute persists a new DisputeSpec so
    // the debate page, ruling page, disputes list and dashboard all
    // see it. We generate sample agent messages and a ruling so the
    // full flow works end-to-end: file → debate (plays sample agent
    // output) → ruling.
    const trip = TRIPS.find((t) => t.id === body.trip_id)
    const filedBy =
      body.filed_by_role === 'driver' ? trip?.driver_id ?? 0 : trip?.rider_id ?? 0
    const newId = ALL_SPECS.length + 1
    const now = new Date()
    const created = now.toISOString()
    const rulingTs = new Date(now.getTime() + 5 * 60_000).toISOString()

    const spec: DisputeSpec = {
      id: newId,
      trip_id: body.trip_id,
      filed_by: filedBy,
      category: body.category,
      claim_text: body.claim_text,
      status: 'resolved',
      priority: 'normal',
      created_at: created,
      outcome: 'partial_refund',
      refund_amount: 5.00,
      llm_degraded: false,
      rider_opening: {
        sender: 'RiderAdvocate',
        recipient: 'Judge',
        message_type: 'case_brief',
        content: {
          brief: {
            position: 'The rider is disputing a charge they believe was unjustified.',
            argument_summary: `The rider filed this dispute: "${body.claim_text}". Based on the evidence available for trip #${body.trip_id}, the charge does not appear to be supported by the trip data. The rider requests a review and appropriate refund.`,
            claims: [
              {
                text: 'The charge is not supported by the trip evidence.',
                evidence_ids: [],
                policy_section_ids: [],
              },
            ],
            requested_outcome: 'Refund of the disputed amount.',
            weaknesses: ['This is a sample dispute generated in mock mode.'],
          },
          round: 'opening',
        },
      },
      driver_opening: {
        sender: 'DriverAdvocate',
        recipient: 'Judge',
        message_type: 'case_brief',
        content: {
          brief: {
            position: 'The driver followed platform procedure.',
            argument_summary: `The driver disputes the rider's claim. The charge was calculated by the platform meter and the driver followed the standard procedure for trip #${body.trip_id}. No deviation from policy is evident.`,
            claims: [
              {
                text: 'The charge was correctly calculated by the platform.',
                evidence_ids: [],
                policy_section_ids: [],
              },
            ],
            requested_outcome: 'No refund — the charge stands.',
            weaknesses: ['This is a sample dispute generated in mock mode.'],
          },
          round: 'opening',
        },
      },
      ruling: {
        id: newId,
        outcome: 'partial_refund',
        refund_amount: 5.00,
        confidence: 0.72,
        reasoning: `Based on the available evidence for trip #${body.trip_id}, the judge finds a partial refund is warranted. The rider's claim has been reviewed against the trip data. This is a sample ruling generated in mock mode to demonstrate the full dispute resolution flow.`,
        rule_outcome: {
          rule: {
            outcome: 'partial_refund',
            refund_amount: 5.00,
            matched_rule_ids: [],
          },
          llm: { outcome: 'partial_refund', refund_amount: 5.00 },
          disagreement: false,
          deciding_evidence_ids: [],
          deciding_policy_sections: [],
          rejected_claims: [],
          rider_explanation: 'Your dispute has been reviewed. A partial refund of $5.00 will be issued.',
          driver_explanation: 'The charge was partially upheld. A refund of $5.00 will be issued to the rider.',
          tone: 'neutral' as const,
          confidence_components: {
            agreement: 1.0,
            evidence_strength: 0.6,
            citation_validity: 0.8,
            history_risk: 0.2,
            fraud_penalty: 0.0,
          },
        },
        evidence_ids: [],
        escalated: false,
        human_review_summary: null,
        llm_degraded: false,
        created_at: rulingTs,
      },
    }

    ALL_SPECS.push(spec)

    const dispute: Dispute = specToDispute(spec)
    return delay<Dispute>(dispute)
  },

  resolveDispute: (id: number) => {
    return delay<{ dispute_id: number; status: string }>({ dispute_id: id, status: 'resolved' })
  },

  getMessages: (id: number) => {
    const spec = ALL_SPECS.find((s) => s.id === id)
    if (!spec) return Promise.reject(new Error(`HTTP 404: Dispute ${id} not found`))
    return delay<AgentMessage[]>(specToMessages(spec))
  },

  getRuling: (id: number) => {
    const spec = ALL_SPECS.find((s) => s.id === id)
    if (!spec || !spec.ruling) return Promise.reject(new Error(`HTTP 404: Ruling for dispute ${id} not found`))
    return delay<Ruling>(specToRuling(spec)!)
  },

  getEvidence: (tripId: number) => {
    const items = EVIDENCE_BY_TRIP[tripId]
    if (!items) return Promise.reject(new Error(`HTTP 404: Evidence for trip ${tripId} not found`))
    return delay<EvidenceItem[]>(items)
  },

  getGps: (tripId: number) => {
    const gps = GPS_FIXTURES[tripId]
    if (!gps) return Promise.reject(new Error(`HTTP 404: GPS for trip ${tripId} not found`))
    return delay<TripGps>(gps)
  },

  getTripChat: (tripId: number) => {
    const chat = CHAT_FIXTURES[tripId] ?? []
    return delay<ChatMessage[]>(chat)
  },

  getQueue: () => {
    const now = Date.now()
    const items: QueueItem[] = ALL_SPECS.map((s) => {
      const age = Math.max(0, (now - new Date(s.created_at).getTime()) / 1000)
      const safety = s.category === 'safety_incident'
      const amount = s.refund_amount ?? 0
      const sla = safety ? 3600 : 86400
      return {
        dispute_id: s.id,
        category: s.category,
        amount,
        priority: (safety ? 1e15 : 0) + amount * 1e8 + age,
        wait_time_seconds: Math.round(age),
        sla_seconds: sla,
        breached: age > sla,
      }
    })
    return delay<QueueItem[]>(items)
  },

  getFormulas: () => delay<Formula[]>(FORMULAS),

  getPolicies: () => delay<PolicySection[]>(POLICIES),

  getRules: () => delay<RuleItem[]>(RULES),

  getSettings: () => delay<Settings>(SETTINGS),

  listAccounts: () => {
    const accounts: AccountItem[] = []
    const seen = new Set<number>()
    for (const t of TRIPS) {
      if (!seen.has(t.rider_id)) {
        seen.add(t.rider_id)
        accounts.push({ id: t.rider_id, name: t.rider, role: 'rider' })
      }
      if (!seen.has(t.driver_id)) {
        seen.add(t.driver_id)
        accounts.push({ id: t.driver_id, name: t.driver, role: 'driver' })
      }
    }
    return delay<AccountItem[]>(accounts)
  },

  listReviews: () => delay<DisputeReview[]>([]),

  reviewDispute: (id: number, action: 'confirm' | 'appeal' | 'assign', note?: string) => {
    const spec = ALL_SPECS.find((s) => s.id === id)
    if (spec) {
      spec.status = action === 'confirm' ? 'resolved' : 'needs_human_review'
    }
    const review: DisputeReview = {
      id: Math.floor(Math.random() * 1_000_000),
      dispute_id: id,
      action,
      note: note ?? null,
      actor: 'ops',
      created_at: new Date().toISOString(),
    }
    return delay<DisputeReview>(review)
  },

  streamUrl: (id: number) => `/api/disputes/${id}/stream`,
}
