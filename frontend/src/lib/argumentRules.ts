/* ============================================================
 * Rule ID extraction for the Arguments screen
 * ============================================================
 *
 * The agent briefs the LLM produces use `policy_section_ids` in
 * `source#section` format (e.g. "route_deviation#1") — see
 * backend/app/agents/prompts/{rider,driver}_advocate.txt and
 * backend/app/schemas/case_brief.py.
 *
 * The rule IDs the design wants us to surface (the "small chips
 * for the rule IDs it cites") are the same strings the advocates
 * use. The placeholder IDs in the design image (RD-001, GPS-001,
 * FARE-001) are NOT real — we ignore those and surface the real
 * project IDs from the briefs.
 *
 * Extraction strategy (defensive, never invents IDs):
 *   1. Collect every policy_section_id from every claim in the
 *      brief. This is the canonical place the LLM is told to put
 *      them.
 *   2. Also scan the argument_summary text for any rule-shaped
 *      string we may have missed (e.g. an advocate that mentions
 *      a rule by name in prose), using a regex that matches:
 *        - snake_case identifiers (e.g. "route_deviation_major")
 *        - "source#section" form (e.g. "no_show#2")
 *   3. De-duplicate, preserve first-seen order.
 *
 * If a string is not one of the canonical rule IDs in
 * `KNOWN_RULE_IDS`, we still surface it as a chip — the rules can
 * grow over time and the LLM is allowed to cite policy sections
 * that don't have a registered rule yet. We just don't pretend
 * we have a title for it.
 */

import type { AgentMessage } from '../api'
import { getRuleMeta } from './rules'

/* The real, snake_case rule IDs declared in backend/rules/rules.yaml
 * and mirrored in lib/rules.ts. We list them here so we can detect
 * bare-name mentions like "route_deviation_major" inside prose. */
const KNOWN_RULE_IDS: ReadonlyArray<string> = [
  'route_deviation_major',
  'route_deviation_minor',
  'no_show_driver_never_arrived',
  'no_show_rider_waited',
  'fare_discrepancy_5pct',
]

/* Matches a policy-section citation of the form `source#section`,
 * e.g. "route_deviation#1" or "no_show#2.3". The source part is
 * snake_case or kebab-case letters/digits/underscore. The section
 * is digits plus optional dots. Word boundaries so we don't catch
 * URLs. */
const POLICY_SECTION_RE = /\b([a-z][a-z0-9_-]*)#(\d+(?:\.\d+)*)\b/g

/* Matches a bare rule id (snake_case, lowercase). We restrict the
 * tail to common rule-id shapes to avoid catching ordinary words. */
const BARE_RULE_RE = /\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b/g

interface ClaimLike {
  text?: string
  policy_section_ids?: string[]
}

function isClaimLike(value: unknown): value is ClaimLike {
  return !!value && typeof value === 'object'
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === 'string')
}

/**
 * Extract every rule ID cited by an advocate's brief. Returns a
 * de-duplicated list, in the order they first appeared.
 */
export function extractRuleIds(brief: Record<string, unknown> | null | undefined): string[] {
  if (!brief || typeof brief !== 'object') return []

  const seen = new Set<string>()
  const out: string[] = []

  function push(id: string) {
    const trimmed = id.trim()
    if (!trimmed) return
    if (seen.has(trimmed)) return
    seen.add(trimmed)
    out.push(trimmed)
  }

  /* 1. claims[].policy_section_ids — canonical */
  const claimsRaw = brief.claims
  if (Array.isArray(claimsRaw)) {
    for (const c of claimsRaw) {
      if (!isClaimLike(c)) continue
      if (isStringArray(c.policy_section_ids)) {
        for (const id of c.policy_section_ids) push(id)
      }
    }
  }

  /* 2. fall back to scanning the argument_summary text */
  const summary = typeof brief.argument_summary === 'string' ? brief.argument_summary : ''
  for (const m of summary.matchAll(POLICY_SECTION_RE)) {
    /* Reconstruct the full "source#section" string. */
    push(`${m[1]}#${m[2]}`)
  }
  for (const m of summary.matchAll(BARE_RULE_RE)) {
    if (KNOWN_RULE_IDS.includes(m[1])) push(m[1])
  }

  return out
}

/**
 * Convenience: pull the rule IDs straight from a `case_brief`
 * agent message's content. Returns [] for non-brief messages.
 */
export function extractRuleIdsFromMessage(message: AgentMessage): string[] {
  if (message.message_type !== 'case_brief') return []
  const content = (message.content ?? {}) as Record<string, unknown>
  const brief = (content.brief ?? {}) as Record<string, unknown>
  return extractRuleIds(brief)
}

/**
 * Return the "title" for a rule ID, falling back to the raw id if
 * we don't have metadata for it.
 */
export function ruleLabel(id: string): string {
  return getRuleMeta(id)?.title ?? id
}
