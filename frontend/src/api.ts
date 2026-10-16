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
  /** Stable external reference (e.g. "DISP-002" or "VAR-R01"). Null for
   * locally filed disputes. */
  external_id?: string | null
  outcome: string | null
  refund_amount: number | null
  llm_degraded: boolean | null
  /** Latest ruling confidence in [0, 1]. */
  confidence?: number | null
  /** ISO timestamp of the latest ruling, if one exists. */
  ruling_created_at?: string | null
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

export interface DisputeReview {
  id: number
  dispute_id: number
  action: string
  note: string | null
  actor: string
  created_at: string
}

export interface AccountItem {
  id: number
  name: string
  role: string
}

export interface ListDisputesParams {
  account_id?: number | null
  include_synthetic?: boolean
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

export interface QueueItem {
  dispute_id: number
  category: string
  amount: number
  priority: number
  wait_time_seconds: number
  sla_seconds: number
  breached: boolean
}

export interface FormulaVariable {
  name: string
  definition: string
}

export interface Formula {
  id: string
  name: string
  category: string
  formula: string
  description: string
  variables: FormulaVariable[]
  source: string
}

export interface PolicySection {
  id: string
  title: string
  text: string
  source: string
  tag: string | null
}

export interface RuleItem {
  id: string
  category: string
  citation: string
  conditions: string
  outcome: string
  amount: string
}

export interface ModelAssignment {
  agent: string
  model: string
  purpose: string
}

export interface ConfigEntry {
  key: string
  label: string
  value: string
  source: string
}

export interface Settings {
  models: ModelAssignment[]
  llm_mock: boolean
  policy_version: string
  policy_numbers: ConfigEntry[]
  thresholds: ConfigEntry[]
  escalation: ConfigEntry[]
}

const BASE = '/api'

/* When VITE_USE_MOCK is 'true', every API call returns sample data
 * from the mocks module instead of hitting the backend. */
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

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

/* Lazily import the mock layer so the real build doesn't pull
 * sample data into the bundle when mock mode is off. */
type MockApi = {
  listTrips: () => Promise<Trip[]>
  listDisputes: (params?: ListDisputesParams) => Promise<DisputeListItem[]>
  fetchCategories: () => Promise<CategoryMeta[]>
  getDispute: (id: number) => Promise<Dispute>
  createDispute: (body: { trip_id: number; category: string; claim_text: string; filed_by_role?: 'rider' | 'driver' }) => Promise<Dispute>
  resolveDispute: (id: number, force?: boolean) => Promise<{ dispute_id: number; status: string }>
  getMessages: (id: number) => Promise<AgentMessage[]>
  getRuling: (id: number) => Promise<Ruling>
  getEvidence: (tripId: number) => Promise<EvidenceItem[]>
  getGps: (tripId: number) => Promise<TripGps>
  getTripChat: (tripId: number) => Promise<ChatMessage[]>
  getQueue: () => Promise<QueueItem[]>
  getFormulas: () => Promise<Formula[]>
  getPolicies: () => Promise<PolicySection[]>
  getRules: () => Promise<RuleItem[]>
  getSettings: () => Promise<Settings>
  listAccounts: () => Promise<AccountItem[]>
  listReviews: (id: number) => Promise<DisputeReview[]>
  reviewDispute: (id: number, action: 'confirm' | 'appeal' | 'assign', note?: string) => Promise<DisputeReview>
  streamUrl: (id: number) => string
}

async function getMock(): Promise<MockApi> {
  const mod = await import('./mocks/index')
  return mod.mockApi
}

export const api = {
  listTrips: () => (USE_MOCK ? getMock().then((m) => m.listTrips()) : request<Trip[]>('/trips')),
  listDisputes: (params?: ListDisputesParams) => {
    if (USE_MOCK) return getMock().then((m) => m.listDisputes(params))
    const qs = new URLSearchParams()
    if (params?.account_id != null) qs.set('account_id', String(params.account_id))
    if (params?.include_synthetic != null) qs.set('include_synthetic', String(params.include_synthetic))
    const q = qs.toString()
    return request<DisputeListItem[]>(`/disputes${q ? `?${q}` : ''}`)
  },
  fetchCategories: () => (USE_MOCK ? getMock().then((m) => m.fetchCategories()) : request<CategoryMeta[]>('/meta/categories')),
  getDispute: (id: number) => (USE_MOCK ? getMock().then((m) => m.getDispute(id)) : request<Dispute>(`/disputes/${id}`)),
  createDispute: (body: { trip_id: number; category: string; claim_text: string; filed_by_role?: 'rider' | 'driver' }) =>
    USE_MOCK
      ? getMock().then((m) => m.createDispute(body))
      : request<Dispute>('/disputes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }),
  resolveDispute: (id: number, force = false) =>
    USE_MOCK
      ? getMock().then((m) => m.resolveDispute(id, force))
      : request<{ dispute_id: number; status: string }>(`/disputes/${id}/resolve${force ? '?force=true' : ''}`, {
          method: 'POST',
        }),
  getMessages: (id: number) => (USE_MOCK ? getMock().then((m) => m.getMessages(id)) : request<AgentMessage[]>(`/disputes/${id}/messages`)),
  getRuling: (id: number) => (USE_MOCK ? getMock().then((m) => m.getRuling(id)) : request<Ruling>(`/disputes/${id}/ruling`)),
  getEvidence: (tripId: number) => (USE_MOCK ? getMock().then((m) => m.getEvidence(tripId)) : request<EvidenceItem[]>(`/trips/${tripId}/evidence`)),
  getGps: (tripId: number) => (USE_MOCK ? getMock().then((m) => m.getGps(tripId)) : request<TripGps>(`/trips/${tripId}/gps`)),
  getTripChat: (tripId: number) => (USE_MOCK ? getMock().then((m) => m.getTripChat(tripId)) : request<ChatMessage[]>(`/trips/${tripId}/chat`)),
  getQueue: () => (USE_MOCK ? getMock().then((m) => m.getQueue()) : request<QueueItem[]>('/queue')),
  getFormulas: () => (USE_MOCK ? getMock().then((m) => m.getFormulas()) : request<Formula[]>('/meta/formulas')),
  getPolicies: () => (USE_MOCK ? getMock().then((m) => m.getPolicies()) : request<PolicySection[]>('/meta/policies')),
  getRules: () => (USE_MOCK ? getMock().then((m) => m.getRules()) : request<RuleItem[]>('/meta/rules')),
  getSettings: () => (USE_MOCK ? getMock().then((m) => m.getSettings()) : request<Settings>('/meta/settings')),
  listAccounts: () => (USE_MOCK ? getMock().then((m) => m.listAccounts()) : request<AccountItem[]>('/accounts')),
  listReviews: (id: number) =>
    USE_MOCK ? getMock().then((m) => m.listReviews(id)) : request<DisputeReview[]>(`/disputes/${id}/reviews`),
  reviewDispute: (id: number, action: 'confirm' | 'appeal' | 'assign', note?: string) =>
    USE_MOCK
      ? getMock().then((m) => m.reviewDispute(id, action, note))
      : request<DisputeReview>(`/disputes/${id}/review`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action, note: note ?? null }),
        }),
  streamUrl: (id: number) => `${BASE}/disputes/${id}/stream`,
}

/* Exported so the UI can show the grey banner. */
export const isMockMode = USE_MOCK
