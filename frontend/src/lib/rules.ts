/* Maps the deterministic rule IDs from backend/rules/rules.yaml to
 * human-readable titles + one-line descriptions, for the Policy Rules
 * tab on the Evidence screen.
 *
 * The backend only stores the rule id (e.g. "route_deviation_major");
 * the title and description live in the policy markdown files under
 * backend/policies/ and are surfaced to the UI through this static map.
 * The map is keyed by rule id so unknown ids fall through gracefully.
 */

export interface RuleMeta {
  id: string
  title: string
  blurb: string
  category: string
}

const RULES: RuleMeta[] = [
  {
    id: 'route_deviation_major',
    title: 'Major route deviation',
    blurb:
      'Driver exceeded the optimal route by more than 2 km without a slow-traffic justification. Partial refund scaled to the extra distance.',
    category: 'route_deviation',
  },
  {
    id: 'route_deviation_minor',
    title: 'Minor route deviation',
    blurb:
      'The extra distance is within tolerance. The fare stands and no refund is issued.',
    category: 'route_deviation',
  },
  {
    id: 'no_show_driver_never_arrived',
    title: 'Driver did not arrive',
    blurb:
      'GPS never came within 100 m of the pickup point. The cancellation fee is fully refunded.',
    category: 'no_show',
  },
  {
    id: 'no_show_rider_waited',
    title: 'Driver arrived and waited',
    blurb:
      'The driver reached the pickup point and waited at least 5 minutes. The cancellation fee is upheld.',
    category: 'no_show',
  },
  {
    id: 'fare_discrepancy_5pct',
    title: 'Fare discrepancy over 5 %',
    blurb:
      'Recomputed fare differs from the charged fare by more than 5 % of the expected amount. The rider is refunded the difference.',
    category: 'fare_dispute',
  },
]

const BY_ID = new Map(RULES.map((r) => [r.id, r] as const))

export function getRuleMeta(id: string): RuleMeta | undefined {
  return BY_ID.get(id)
}

export function listRules(): RuleMeta[] {
  return RULES
}
