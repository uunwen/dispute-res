import type { AgentMessage } from '../api'

/* ============================================================
 * Debate-round builder
 * ============================================================
 * Translates the raw list of AgentMessage rows from
 * GET /api/disputes/:id/messages into a list of debate "rounds"
 * suitable for the playback timeline.
 *
 * Crucially: this function NEVER invents rounds. If the backend
 * did not produce a rebuttal message, we do not show a rebuttal
 * step. The list is built strictly from what the API returned.
 *
 * Persisted message types we care about:
 *   - case_brief  (RiderAdvocate / DriverAdvocate / Judge)
 *   - escalation  (Judge -> HumanReviewer, when escalated)
 *   - fraud_signal (skipped — informational, not spoken)
 *
 * The backend orders messages by created_at, but the speaker order
 * is well-defined by the pipeline:
 *   opening: Rider, Driver
 *   rebuttal (if rebuttal_enabled): Rider, Driver
 *   judge: 1 ruling (deliberation) + 1 escalation if escalated
 */

export type Speaker = 'rider' | 'driver' | 'judge'

export interface DebateRound {
  /** Stable id derived from the backend message id. */
  id: string
  /** Speaker for this round. */
  speaker: Speaker
  /** Short label used in the right-hand list and progress bar. */
  label: string
  /** Subtitle shown under the speaker card on the stage. */
  speakerSubtitle: string
  /** Verbatim text from the agent, trimmed to the first 1–2 sentences. */
  preview: string
  /** Full verbatim text, used by the transcript drawer. */
  fullText: string
  /** Original message, for the transcript drawer header. */
  message: AgentMessage
}

const SPEAKER_SUBTITLE: Record<Speaker, string> = {
  rider: "Presents the rider's case",
  driver: "Presents the driver's defense",
  judge: 'Evaluates evidence and policy',
}

function sentencePreview(s: string, max = 2): string {
  const trimmed = s.replace(/\s+/g, ' ').trim()
  if (!trimmed) return ''
  // Split on sentence-ending punctuation followed by whitespace.
  const parts = trimmed.split(/(?<=[.!?])\s+/)
  return parts.slice(0, max).join(' ')
}

function speakerFromSender(sender: string): Speaker | null {
  if (sender === 'RiderAdvocate') return 'rider'
  if (sender === 'DriverAdvocate') return 'driver'
  if (sender === 'Judge') return 'judge'
  return null
}

function labelFor(messageType: string, speaker: Speaker, round: string | undefined): string {
  // Judge messages: 'escalation' -> "Final decision", otherwise -> "Judge deliberation"
  if (speaker === 'judge') {
    return messageType === 'escalation' ? 'Final decision' : 'Judge deliberation'
  }
  const isRebuttal = round === 'rebuttal'
  if (speaker === 'rider') return isRebuttal ? 'Rider rebuttal' : 'Rider opening argument'
  return isRebuttal ? 'Driver rebuttal' : 'Driver opening argument'
}

function extractText(m: AgentMessage): { preview: string; fullText: string } {
  // The content shape varies:
  //  - case_brief: { brief: { argument_summary: "..." }, round: "opening"|"rebuttal", ... }
  //  - escalation: HumanReviewSummary (top-level fields: dispute, rider_brief, ...)
  //  - fraud_signal: skipped before reaching here
  const content = (m.content ?? {}) as Record<string, unknown>

  if (m.message_type === 'case_brief') {
    const brief = (content.brief ?? {}) as Record<string, unknown>
    const summary = (brief.argument_summary as string | undefined) ?? ''
    return {
      preview: sentencePreview(summary, 2),
      fullText: summary || 'No brief produced (LLM unavailable).',
    }
  }

  if (m.message_type === 'escalation') {
    const ruling = (content.ruling as string | undefined) ?? ''
    const reason = (content.escalation_reason as string | undefined) ?? ''
    const recommended = (content.recommended_action as string | undefined) ?? ''
    const composed = [ruling, reason ? `Reason: ${reason}` : '', recommended]
      .filter(Boolean)
      .join(' · ')
    return {
      preview: sentencePreview(composed, 2),
      fullText: composed || 'Escalation summary unavailable.',
    }
  }

  // Fallback (unknown future type): serialize the content
  return {
    preview: '',
    fullText: JSON.stringify(content, null, 2),
  }
}

export function buildRounds(messages: AgentMessage[]): DebateRound[] {
  const rounds: DebateRound[] = []
  for (const m of messages) {
    if (m.message_type === 'fraud_signal') continue

    const speaker = speakerFromSender(m.sender)
    if (speaker === null) continue

    const content = (m.content ?? {}) as Record<string, unknown>
    const round = (content.round as string | undefined) ?? 'opening'

    const { preview, fullText } = extractText(m)

    rounds.push({
      id: `m-${m.id}`,
      speaker,
      label: labelFor(m.message_type, speaker, round),
      speakerSubtitle: SPEAKER_SUBTITLE[speaker],
      preview,
      fullText,
      message: m,
    })
  }
  return rounds
}
