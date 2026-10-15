import type { EvidenceItem } from '../api'
import {
  buildRouteEvidence,
  buildFareEvidence,
  buildNoShowEvidence,
  buildChatAnalysisEvidence,
  buildHistoryProfile,
  isoAt,
} from './fixtures'

/* ============================================================
 * Evidence items per trip
 * ============================================================
 * Each trip needs the evidence items the backend's deterministic
 * analyzers would produce. The evidence page reads these to render
 * route maps, fare details, no-show timelines, and chat analysis.
 */

export const EVIDENCE_BY_TRIP: Record<number, EvidenceItem[]> = {
  1: [
    buildRouteEvidence(1, 8.5, 5.3, 22, 14),
    buildFareEvidence(1, 5.0, 20.0, 1.2, 4.0, 0.0, 8.5, 'rider', 0.85),
    buildHistoryProfile(1, 0.15, 0.10, 1, 0),
  ],
  2: [
    buildRouteEvidence(2, 5.4, 5.0, 18, 16),
    buildFareEvidence(2, 5.0, 30.0, 1.0, 0.0, 0.0, 4.0, 'driver', 0.6),
    buildHistoryProfile(2, 0.10, 0.05, 0, 0),
  ],
  3: [
    buildNoShowEvidence(3, false, null, 0, 320, 18.0, 'rider', 0.91),
    buildHistoryProfile(3, 0.08, 0.12, 0, 1),
  ],
  4: [
    buildNoShowEvidence(4, false, null, 0, 800, 5.0, 'driver', 0.88),
    buildHistoryProfile(4, 0.25, 0.05, 2, 0),
  ],
  5: [
    buildNoShowEvidence(5, true, isoAt(12, 16, 2), 2.5, 50, 16.5, 'neutral', 0.79),
    buildHistoryProfile(5, 0.12, 0.08, 1, 0),
  ],
  6: [
    buildChatAnalysisEvidence(
      6,
      [],
      [],
      'Rider reported luggage damage immediately. Driver denied responsibility. No photo evidence provided.',
      'rider', 0.55,
    ),
    buildHistoryProfile(6, 0.10, 0.08, 0, 0),
  ],
  7: [
    buildChatAnalysisEvidence(
      7,
      [],
      ['I am sorry about that. The cup slipped.'],
      'Driver admitted to spilling coffee on the rider\'s laptop bag. Rider requested compensation.',
      'rider', 0.65,
    ),
    buildHistoryProfile(7, 0.08, 0.05, 0, 0),
  ],
  8: [
    buildChatAnalysisEvidence(
      8,
      ['You were speeding through the school zone!'],
      [],
      'Rider reported speeding through a school zone during the trip. Driver denied the claim.',
      'rider', 0.45,
    ),
    buildHistoryProfile(8, 0.20, 0.15, 1, 0),
  ],
  9: [
    buildChatAnalysisEvidence(
      9,
      ['You ran the red light at the intersection!'],
      ['I know, I am sorry. I misjudged the timing.'],
      'Rider reported driver ran a red light. Driver admitted fault and apologized.',
      'rider', 0.62,
    ),
    buildHistoryProfile(9, 0.15, 0.10, 0, 0),
  ],
  10: [
    buildNoShowEvidence(10, false, null, 0, 500, 5.0, 'rider', 0.7),
    buildHistoryProfile(10, 0.18, 0.10, 1, 0),
  ],
  11: [
    buildRouteEvidence(11, 6.2, 4.8, 20, 15),
    buildFareEvidence(11, 5.0, 30.0, 1.3, 9.0, 0.0, 8.0, 'rider', 0.8),
    buildHistoryProfile(11, 0.12, 0.08, 0, 1),
  ],
  12: [
    buildRouteEvidence(12, 8.0, 4.5, 24, 14),
    buildFareEvidence(12, 5.0, 14.0, 1.0, 0.0, 0.0, 11.0, 'rider', 0.93),
    buildHistoryProfile(12, 0.05, 0.05, 0, 0),
  ],
}
