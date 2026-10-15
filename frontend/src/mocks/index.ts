import type {
  AgentMessage,
  CategoryMeta,
  ChatMessage,
  Dispute,
  DisputeListItem,
  EvidenceItem,
  Ruling,
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
    outcome: spec.outcome,
    refund_amount: spec.refund_amount,
    llm_degraded: spec.llm_degraded,
    // In real mode these are not returned by GET /disputes. The mock
    // layer fills them so the disputes list and analytics pane can
    // show confidence and avg-resolution without extra round-trips.
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

  listDisputes: () => delay<DisputeListItem[]>(ALL_SPECS.map(specToDisputeListItem)),

  fetchCategories: () => delay<CategoryMeta[]>(CATEGORIES),

  getDispute: (id: number) => {
    const spec = ALL_SPECS.find((s) => s.id === id)
    if (!spec) return Promise.reject(new Error(`HTTP 404: Dispute ${id} not found`))
    return delay<Dispute>(specToDispute(spec))
  },

  createDispute: (body: { trip_id: number; category: string; claim_text: string; filed_by: number }) => {
    // In mock mode, creating a dispute persists a new DisputeSpec so
    // the debate page, ruling page, disputes list and dashboard all
    // see it. We generate sample agent messages and a ruling so the
    // full flow works end-to-end: file → debate (plays sample agent
    // output) → ruling.
    const newId = ALL_SPECS.length + 1
    const now = new Date()
    const created = now.toISOString()
    const rulingTs = new Date(now.getTime() + 5 * 60_000).toISOString()

    const spec: DisputeSpec = {
      id: newId,
      trip_id: body.trip_id,
      filed_by: body.filed_by,
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

  streamUrl: (id: number) => `/api/disputes/${id}/stream`,
}
