import type {
  AgentMessage,
  ChatMessage,
  Dispute,
  DisputeListItem,
  EvidenceItem,
  GpsPoint,
  Ruling,
  Trip,
  TripGps,
  CategoryMeta,
} from '../api'

/* ============================================================
 * Sample-data mode — internal types
 * ============================================================
 * These types are only used to build the mock dataset. The export
 * functions return the same types the real api.ts uses, so no
 * consumer needs to know about these.
 */

export interface BriefClaim {
  text: string
  evidence_ids: string[]
  policy_section_ids: string[]
}

export interface CaseBriefContent {
  position: string
  argument_summary: string
  claims: BriefClaim[]
  requested_outcome: string
  weaknesses: string[]
}

export interface CaseBriefMessage {
  sender: 'RiderAdvocate' | 'DriverAdvocate'
  recipient: 'Judge'
  message_type: 'case_brief'
  content: {
    brief: CaseBriefContent
    round: 'opening' | 'rebuttal'
  }
}

export interface FraudSignalContent {
  reasons: { code: string; description: string; evidence_id: string }[]
  rider_risk: number
  driver_risk: number
}

export interface HumanReviewSummaryContent {
  dispute: string
  rider_brief: string
  driver_brief: string
  key_evidence_ids: string[]
  ruling: string
  escalation_reason: string
  recommended_action: string
}

export interface RuleOutcome {
  rule: {
    outcome: string
    refund_amount: number
    matched_rule_ids: string[]
  }
  llm: {
    outcome: string
    refund_amount: number
  }
  disagreement: boolean
  deciding_evidence_ids: string[]
  deciding_policy_sections: string[]
  rejected_claims: { advocate: string; claim_text: string; reason: string }[]
  rider_explanation: string
  driver_explanation: string
  tone: 'empathetic' | 'neutral'
  confidence_components: {
    agreement: number
    evidence_strength: number
    citation_validity: number
    history_risk: number
    fraud_penalty: number
  }
}

export interface DisputeSpec {
  id: number
  trip_id: number
  filed_by: number
  category: string
  claim_text: string
  status: string
  priority: string
  created_at: string
  outcome: string | null
  refund_amount: number | null
  llm_degraded: boolean | null
  rider_opening: CaseBriefMessage
  driver_opening: CaseBriefMessage
  rider_rebuttal?: CaseBriefMessage
  driver_rebuttal?: CaseBriefMessage
  fraud_signal?: {
    sender: 'Fraud'
    recipient: 'Judge'
    message_type: 'fraud_signal'
    content: FraudSignalContent
  }
  escalation?: {
    sender: 'Judge'
    recipient: 'HumanReviewer'
    message_type: 'escalation'
    content: HumanReviewSummaryContent
  }
  ruling?: {
    id: number
    outcome: string
    refund_amount: number
    confidence: number
    reasoning: string
    rule_outcome: RuleOutcome
    evidence_ids: string[]
    escalated: boolean
    human_review_summary: HumanReviewSummaryContent | null
    llm_degraded: boolean
    created_at: string
  }
}

export type {
  AgentMessage,
  ChatMessage,
  Dispute,
  DisputeListItem,
  EvidenceItem,
  GpsPoint,
  Ruling,
  Trip,
  TripGps,
  CategoryMeta,
}
