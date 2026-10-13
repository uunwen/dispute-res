export type Supports = 'rider' | 'driver' | 'neutral'

export interface CategoryMeta {
  value: string
  label: string
  example_claim: string
  supported: boolean
}

export interface Trip {
  id: number
  rider_id: number
  driver_id: number
  rider: string
  driver: string
  fare: number
  scenario: string
}

export interface DisputeListItem {
  id: number
  trip_id: number
  category: string
  status: string
  priority: string
  claim_text: string
  created_at: string
  outcome: string | null
  refund_amount: number | null
  llm_degraded: boolean | null
}

export interface Dispute {
  id: number
  trip_id: number
  filed_by: number
  category: string
  claim_text: string
  status: string
  priority: string
  created_at: string
}

export interface AgentMessage {
  id: number
  dispute_id: number
  sender: string
  recipient: string
  message_type: string
  content: Record<string, unknown>
  created_at: string
}

export interface EvidenceItem {
  id: string
  type: string
  trip_id: number | null
  summary: string
  data: Record<string, unknown>
  supports: Supports
  strength: number
}

export interface HumanReviewSummary {
  dispute: string
  rider_brief: string
  driver_brief: string
  key_evidence_ids: string[]
  ruling: string
  escalation_reason: string
  recommended_action: string
}

export interface Ruling {
  id: number
  dispute_id: number
  outcome: string
  refund_amount: number
  confidence: number
  reasoning: string
  rule_outcome: Record<string, unknown>
  evidence_ids: string[]
  escalated: boolean
  human_review_summary: HumanReviewSummary | null
  llm_degraded: boolean
  created_at: string
}

export interface ChatMessage {
  id: number
  trip_id: number
  sender_id: number
  sender: string
  text: string
  ts: string
}

export interface GpsPoint {
  lat: number
  lng: number
  ts: string
  speed_kmh: number | null
}

export interface TripGps {
  optimal_route: [number, number][]
  points: GpsPoint[]
}

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, init)
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const body = await resp.json()
      detail = (body as { detail?: string }).detail ?? detail
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail)
  }
  return (await resp.json()) as T
}

export const api = {
  listTrips: () => request<Trip[]>('/trips'),
  listDisputes: () => request<DisputeListItem[]>('/disputes'),
  fetchCategories: () => request<CategoryMeta[]>('/meta/categories'),
  getDispute: (id: number) => request<Dispute>(`/disputes/${id}`),
  createDispute: (body: { trip_id: number; category: string; claim_text: string; filed_by: number }) =>
    request<Dispute>('/disputes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  resolveDispute: (id: number, force = false) =>
    request<{ dispute_id: number; status: string }>(`/disputes/${id}/resolve${force ? '?force=true' : ''}`, {
      method: 'POST',
    }),
  getMessages: (id: number) => request<AgentMessage[]>(`/disputes/${id}/messages`),
  getRuling: (id: number) => request<Ruling>(`/disputes/${id}/ruling`),
  getEvidence: (tripId: number) => request<EvidenceItem[]>(`/trips/${tripId}/evidence`),
  getGps: (tripId: number) => request<TripGps>(`/trips/${tripId}/gps`),
  streamUrl: (id: number) => `${BASE}/disputes/${id}/stream`,
}
