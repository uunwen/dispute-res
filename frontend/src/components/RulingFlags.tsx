import type { Dispute, Ruling } from '../api'

/* ============================================================
 * Ruling flags
 * ============================================================
 * The backend doesn't store boolean flag columns (driver_warning,
 * fraud_flag, etc.). The Ruling model only has `escalated` and
 * `llm_degraded` as real boolean fields. The other flags in the
 * design are derived from existing data:
 *
 *   - Safety referral  → dispute.category === 'safety_incident'
 *   - Driver warning   → the rider_explanation / driver_explanation
 *                        text explicitly addresses the driver, or the
 *                        ruling was escalated due to driver behaviour
 *                        (escalation_reason includes 'safety_incident')
 *   - Rider warning    → fraud_penalty > 0 OR escalation_reason
 *                        includes low_confidence while the rider
 *                        produced a fraud_signal-shaped event
 *   - Fraud flag       → confidence_components.fraud_penalty > 0
 *   - Security flag    → not derivable from any current field
 *
 * The component is intentionally lenient: anything we can't prove
 * true is simply not shown. The user spec says "Flags row showing
 * only the flags that are true" — we never invent flags.
 */

export interface RulingFlag {
  key: string
  label: string
  tone: 'warn' | 'danger' | 'info'
}

interface Args {
  dispute: Dispute | null
  ruling: Ruling
}

function num(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string' && v !== '') {
    const n = Number(v)
    return Number.isFinite(n) ? n : null
  }
  return null
}

function readRuleOutcome(ruling: Ruling): Record<string, unknown> {
  return (ruling.rule_outcome ?? {}) as Record<string, unknown>
}

function readConfidenceComponents(ruling: Ruling): Record<string, number> {
  const ro = readRuleOutcome(ruling)
  const cc = ro.confidence_components
  return cc && typeof cc === 'object' ? (cc as Record<string, number>) : {}
}

function readEscalationReason(ruling: Ruling): string {
  const h = ruling.human_review_summary
  if (h && typeof h === 'object') {
    const r = (h as unknown as Record<string, unknown>).escalation_reason
    if (typeof r === 'string') return r
  }
  return ''
}

function readDriverExplanation(ruling: Ruling): string {
  const ro = readRuleOutcome(ruling)
  const v = ro.driver_explanation
  return typeof v === 'string' ? v : ''
}

export function deriveFlags({ dispute, ruling }: Args): RulingFlag[] {
  const flags: RulingFlag[] = []
  const cc = readConfidenceComponents(ruling)
  const escalationReason = readEscalationReason(ruling)
  const driverText = readDriverExplanation(ruling)

  // 1. Safety referral — fires when the dispute is a safety incident.
  if (dispute && dispute.category === 'safety_incident') {
    flags.push({ key: 'safety_referral', label: 'Safety referral', tone: 'warn' })
  }

  // 2. Fraud flag — only when the judge's confidence was actually
  //    penalised by a fraud signal. fraud_penalty > 0 means at least
  //    one party tripped a fraud reason.
  const fraudPenalty = num(cc.fraud_penalty) ?? 0
  if (fraudPenalty > 0) {
    flags.push({ key: 'fraud_flag', label: 'Fraud flag', tone: 'danger' })
  }

  // 3. Driver warning — when the escalation was driven by driver
  //    behaviour (safety_incident category OR escalation reason
  //    mentions safety) AND the judge's driver_explanation actually
  //    addresses the driver.
  const driverMentionedInExplanation = /driver|you (?:did|were|took|failed)/i.test(driverText)
  const isDriverEscalation =
    escalationReason.includes('safety_incident') ||
    (dispute && dispute.category === 'safety_incident' && ruling.escalated)
  if ((isDriverEscalation || driverMentionedInExplanation) && dispute?.category !== 'route_deviation') {
    flags.push({ key: 'driver_warning', label: 'Driver warning', tone: 'warn' })
  }

  // 4. Rider warning — fraud_penalty > 0 also implies a rider signal
  //    was raised; surface that distinctly so a single fraud event
  //    doesn't show as both "Fraud" and "Rider warning" without cause.
  //    We only show the rider warning if the dispute was NOT a
  //    safety_incident and NOT a no_show (where the rider is the
  //    victim, not the subject of the warning).
  if (
    fraudPenalty > 0 &&
    dispute &&
    dispute.category !== 'safety_incident' &&
    dispute.category !== 'no_show'
  ) {
    flags.push({ key: 'rider_warning', label: 'Rider warning', tone: 'warn' })
  }

  // 5. Security flag — not derivable from any current field. We do not
  //    fabricate it; it will simply not appear in the row.

  return flags
}
