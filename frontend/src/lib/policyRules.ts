/* ============================================================
 * Static rules used by the Policies page.
 * ============================================================
 * Source of truth: backend/policies/*.md. The rule ids, titles
 * and body text below are copied from those markdown files so
 * the UI never invents rule content. If a new policy file is
 * added, add a new entry below with the matching id.
 *
 * Note: backend/policies has files for general, no_show,
 * route_deviation, fare_surge_promo and safety. There is no
 * property_damage.md, so the property_damage group is rendered
 * as an empty state on the Policies page. The fare/surge rules
 * (RD-002A/B/C) live under the route_deviation group in the
 * page (they share that document lineage) but are not duplicated
 * here.
 * ============================================================ */

export type PolicyPart = 'general' | 'no_show' | 'route_deviation' | 'property_damage' | 'safety'

export interface PolicyRule {
  /** The exact rule id from the policy markdown (e.g. "RD-001A"). */
  id: string
  /** Short title shown in the card header. */
  title: string
  /** Verbatim rule body — one paragraph is usually enough. */
  text: string
  /** Which part of the policy this rule belongs to. */
  part: PolicyPart
}

export const POLICY_RULES: PolicyRule[] = [
  /* ---------- General principles (G-001..G-007) ---------- */
  {
    id: 'G-001',
    part: 'general',
    title: 'Missing required evidence (material impact)',
    text:
      'Triggers escalation when required evidence for the category is missing and the outcome would materially affect a party.',
  },
  {
    id: 'G-002',
    part: 'general',
    title: 'Contradicting evidence on a decisive fact',
    text:
      'Escalate when evidence sources contradict each other on a decisive fact that drives the outcome.',
  },
  {
    id: 'G-003',
    part: 'general',
    title: 'Safety allegation or immediate harm',
    text:
      'A safety allegation or potential immediate harm must be escalated and routed to the safety workflow.',
  },
  {
    id: 'G-004',
    part: 'general',
    title: 'Possible forged evidence, abuse or fraud',
    text:
      'Refer for review and do not label a person guilty when there is a possible forged evidence, abuse or fraud signal.',
  },
  {
    id: 'G-005',
    part: 'general',
    title: 'Policy applicability unclear',
    text:
      'Escalate when the applicable policy version or interpretation is unclear or in conflict.',
  },
  {
    id: 'G-006',
    part: 'general',
    title: 'Low or uncalibrated model confidence',
    text:
      'Low or uncalibrated model confidence triggers review. Confidence alone never establishes liability.',
  },
  {
    id: 'G-007',
    part: 'general',
    title: 'Historical behaviour profile used',
    text:
      'A historical behaviour profile (dispute history, ratings, account age) may raise a fraud or bad-faith flag for review but never establishes liability or overrides case evidence.',
  },

  /* ---------- No-show (NS-001A/B/C) ---------- */
  {
    id: 'NS-001A',
    part: 'no_show',
    title: 'Verified charge violates the published rule',
    text:
      'Verified charge violates the published cancellation or waiting rule (e.g. rider cancelled within the 3-minute grace period, the driver did not press "I\'m Here", or the driver waited 3 minutes or less). Outcome: REFUND_FULL or REFUND_PARTIAL, per the confirmed rule.',
  },
  {
    id: 'NS-001B',
    part: 'no_show',
    title: 'Charge meets the verified conditions',
    text:
      'The charge meets all verified conditions and no exception applies. Outcome: NO_ADJUSTMENT.',
  },
  {
    id: 'NS-001C',
    part: 'no_show',
    title: 'Arrival or timing disputed and not independently resolved',
    text:
      'Arrival or timing is disputed and not independently resolved. Outcome: REQUEST_EVIDENCE or HUMAN_REVIEW.',
  },

  /* ---------- Route deviation (RD-001A/B/C + fare/surge RD-002A/B/C) ---------- */
  {
    id: 'RD-001A',
    part: 'route_deviation',
    title: 'Verified unjustified detour with excess charge',
    text:
      'Verified unjustified detour AND verified attributable excess charge. Outcome: REFUND_PARTIAL. Calculation and evidence citations are required. A deviation over 2.0 km extra distance is labelled major in the ruling; the label does not change the refund rule.',
  },
  {
    id: 'RD-001B',
    part: 'route_deviation',
    title: 'Detour justified by reliable evidence',
    text:
      'Detour justified by reliable contemporaneous evidence (road closure, traffic, safety need, rider-requested detour, or legitimate route optimisation). Outcome: NO_ADJUSTMENT on route-deviation grounds.',
  },
  {
    id: 'RD-001C',
    part: 'route_deviation',
    title: 'Contradiction or insufficient evidence',
    text:
      'Material route or price contradiction, or insufficient evidence. Outcome: REQUEST_EVIDENCE or HUMAN_REVIEW.',
  },
  {
    id: 'RD-002A',
    part: 'route_deviation',
    title: 'Fare breakdown does not match pricing basis',
    text:
      'The verified fare breakdown does not match the pricing basis, surge multiplier or promo terms, and the difference is above the 5% tolerance. Outcome: REFUND_PARTIAL, or REFUND_FULL if the whole charge is unsupported. Calculation and evidence citations are required.',
  },
  {
    id: 'RD-002B',
    part: 'route_deviation',
    title: 'Fare matches the verified basis',
    text:
      'The fare matches the verified pricing basis, surge and promo terms, or is within tolerance. Outcome: NO_ADJUSTMENT.',
  },
  {
    id: 'RD-002C',
    part: 'route_deviation',
    title: 'Pricing basis unavailable or contradictory',
    text:
      'Pricing basis, surge or promo terms are unavailable or contradictory. Outcome: REQUEST_EVIDENCE or HUMAN_REVIEW.',
  },

  /* ---------- Property damage ---------- */
  // No policy markdown file is published for this part. The group
  // is rendered as an empty state on the Policies page so users
  // see the category exists but the framework is still draft.

  /* ---------- Safety (SI-001A/B/C) ---------- */
  {
    id: 'SI-001A',
    part: 'safety',
    title: 'Immediate or ongoing danger',
    text:
      'The allegation indicates immediate or ongoing danger. Outcome: urgent HUMAN_REVIEW and safety escalation, with emergency guidance where appropriate.',
  },
  {
    id: 'SI-001B',
    part: 'safety',
    title: 'Non-immediate serious misconduct',
    text:
      'Non-immediate serious misconduct allegation. Outcome: HUMAN_REVIEW with a neutral evidence summary.',
  },
  {
    id: 'SI-001C',
    part: 'safety',
    title: 'Insufficient evidence for a factual determination',
    text:
      'Insufficient evidence for a factual determination. Outcome: preserve the allegation and the uncertainty, and HUMAN_REVIEW.',
  },
]

const BY_PART: Record<PolicyPart, PolicyRule[]> = {
  general: [],
  no_show: [],
  route_deviation: [],
  property_damage: [],
  safety: [],
}

for (const r of POLICY_RULES) {
  BY_PART[r.part].push(r)
}

export const POLICY_PARTS: { key: PolicyPart; label: string; description: string }[] = [
  { key: 'general', label: 'General', description: 'Global principles, escalation triggers, and auto-resolution conditions.' },
  { key: 'no_show', label: 'No-show', description: 'Cancellation fee, waiting time fee, and arrival evidence.' },
  { key: 'route_deviation', label: 'Route deviation', description: 'Justified vs unjustified detours, fare discrepancies, and refund guidance.' },
  { key: 'property_damage', label: 'Property damage', description: 'No published policy file yet — the framework for this category is still draft.' },
  { key: 'safety', label: 'Safety', description: 'Safety allegations, conduct reference points, and prohibited automated outcomes.' },
]

export function rulesForPart(part: PolicyPart): PolicyRule[] {
  return BY_PART[part]
}

export function listAllRules(): PolicyRule[] {
  return POLICY_RULES
}
