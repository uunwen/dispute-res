import type { ChatMessage, EvidenceItem, GpsPoint, Trip, TripGps } from '../api'

/* ============================================================
 * Fixtures: trips, GPS, chat, evidence
 * ============================================================
 */

export function isoAt(day: number, hour: number, min: number): string {
  const d = new Date(2026, 9, day, hour, min, 0)
  return d.toISOString()
}

export const TRIPS: Trip[] = [
  { id: 1, rider_id: 101, driver_id: 201, rider: 'Sarah Chen', driver: 'Marcus Webb', fare: 28.50, scenario: 'route_deviation' },
  { id: 2, rider_id: 102, driver_id: 202, rider: 'David Park', driver: 'Luis Gomez', fare: 34.00, scenario: 'route_deviation' },
  { id: 3, rider_id: 103, driver_id: 203, rider: 'Emily Tran', driver: 'James Okoro', fare: 18.00, scenario: 'no_show' },
  { id: 4, rider_id: 104, driver_id: 204, rider: 'Alex Kim', driver: 'Rosa Vargas', fare: 22.00, scenario: 'no_show' },
  { id: 5, rider_id: 105, driver_id: 205, rider: 'Jenna Wu', driver: 'Tom Hardy', fare: 16.50, scenario: 'no_show' },
  { id: 6, rider_id: 106, driver_id: 206, rider: 'Mark Liu', driver: 'Sara Patel', fare: 30.00, scenario: 'property_damage' },
  { id: 7, rider_id: 107, driver_id: 207, rider: 'Nina Park', driver: 'Carl Reed', fare: 42.00, scenario: 'property_damage' },
  { id: 8, rider_id: 108, driver_id: 208, rider: 'Owen Diaz', driver: 'Maya Singh', fare: 35.00, scenario: 'safety_incident' },
  { id: 9, rider_id: 109, driver_id: 209, rider: 'Iris Wong', driver: 'Ben Carter', fare: 27.50, scenario: 'safety_incident' },
  { id: 10, rider_id: 110, driver_id: 210, rider: 'Paul Ng', driver: 'Eva Lin', fare: 19.00, scenario: 'no_show' },
  { id: 11, rider_id: 111, driver_id: 211, rider: 'Kate Ho', driver: 'Ryan Cole', fare: 38.00, scenario: 'route_deviation' },
  { id: 12, rider_id: 112, driver_id: 212, rider: 'Leo Chang', driver: 'Anna Diaz', fare: 25.00, scenario: 'route_deviation' },
]

/* ---------- GPS fixtures ---------- */

function makeGps(
  day: number,
  startHour: number,
  points: [number, number, number][], // [lat, lng, speed]
  optimal: [number, number][],
): TripGps {
  const ts0 = new Date(2026, 9, day, startHour, 0, 0).getTime()
  const gpsPoints: GpsPoint[] = points.map(([lat, lng, speed], i) => ({
    lat,
    lng,
    ts: new Date(ts0 + i * 30_000).toISOString(),
    speed_kmh: speed,
  }))
  return { optimal_route: optimal, points: gpsPoints }
}

export const GPS_FIXTURES: Record<number, TripGps> = {
  // Trip 1: route deviation — driver took a longer route
  1: makeGps(
    10, 9,
    [
      [40.7505, -73.9934, 0],
      [40.7510, -73.9920, 25],
      [40.7520, -73.9890, 35],
      [40.7535, -73.9870, 30],
      [40.7550, -73.9850, 28],
      [40.7560, -73.9820, 32],
      [40.7570, -73.9790, 30],
      [40.7580, -73.9760, 25],
      [40.7590, -73.9730, 20],
      [40.7600, -73.9700, 0],
    ],
    [
      [40.7505, -73.9934],
      [40.7515, -73.9900],
      [40.7530, -73.9860],
      [40.7550, -73.9820],
      [40.7570, -73.9780],
      [40.7600, -73.9700],
    ],
  ),
  // Trip 2: route deviation — minor, driver took a slightly longer path
  2: makeGps(
    11, 14,
    [
      [40.7300, -74.0100, 0],
      [40.7310, -74.0080, 22],
      [40.7325, -74.0050, 30],
      [40.7340, -74.0020, 28],
      [40.7350, -73.9990, 25],
      [40.7360, -73.9960, 0],
    ],
    [
      [40.7300, -74.0100],
      [40.7315, -74.0060],
      [40.7335, -74.0020],
      [40.7355, -73.9970],
      [40.7360, -73.9960],
    ],
  ),
  // Trip 3: no-show — driver arrived but rider didn't come out
  3: makeGps(
    10, 8,
    [
      [40.7400, -73.9800, 0],
      [40.7410, -73.9790, 20],
      [40.7420, -73.9785, 15],
      [40.7425, -73.9782, 0],
      [40.7425, -73.9782, 0],
      [40.7420, -73.9785, 10],
    ],
    [[40.7400, -73.9800], [40.7425, -73.9782]],
  ),
  // Trip 4: no-show — driver never arrived
  4: makeGps(
    11, 10,
    [
      [40.7100, -74.0000, 0],
      [40.7110, -73.9990, 30],
      [40.7120, -73.9980, 25],
      [40.7125, -73.9975, 0],
    ],
    [[40.7100, -74.0000], [40.7200, -73.9900]],
  ),
  // Trip 5: no-show — driver waited briefly
  5: makeGps(
    12, 16,
    [
      [40.7200, -73.9900, 0],
      [40.7210, -73.9890, 18],
      [40.7220, -73.9885, 12],
      [40.7220, -73.9885, 0],
      [40.7220, -73.9885, 0],
      [40.7215, -73.9890, 8],
    ],
    [[40.7200, -73.9900], [40.7220, -73.9885]],
  ),
  // Trip 10: no-show — driver never arrived (in progress dispute)
  10: makeGps(
    14, 11,
    [
      [40.7150, -74.0050, 0],
      [40.7160, -74.0040, 28],
      [40.7170, -74.0030, 22],
      [40.7175, -74.0025, 0],
    ],
    [[40.7150, -74.0050], [40.7250, -73.9950]],
  ),
  // Trip 11: route deviation (in progress dispute)
  11: makeGps(
    14, 13,
    [
      [40.7600, -73.9700, 0],
      [40.7610, -73.9680, 26],
      [40.7625, -73.9650, 34],
      [40.7640, -73.9620, 30],
      [40.7650, -73.9590, 25],
      [40.7660, -73.9560, 0],
    ],
    [
      [40.7600, -73.9700],
      [40.7620, -73.9660],
      [40.7640, -73.9620],
      [40.7660, -73.9560],
    ],
  ),
  // Trip 12: route deviation — full refund
  12: makeGps(
    13, 10,
    [
      [40.7400, -73.9900, 0],
      [40.7420, -73.9870, 30],
      [40.7450, -73.9830, 35],
      [40.7480, -73.9790, 32],
      [40.7510, -73.9750, 28],
      [40.7540, -73.9710, 0],
    ],
    [
      [40.7400, -73.9900],
      [40.7430, -73.9860],
      [40.7460, -73.9820],
      [40.7490, -73.9780],
      [40.7520, -73.9740],
      [40.7540, -73.9710],
    ],
  ),
}

/* ---------- Chat fixtures ---------- */

export function buildChat(
  tripId: number,
  messages: [number, string, string, number][], // [sender_id, sender_name, text, min_offset]
  day: number,
  hour: number,
): ChatMessage[] {
  const ts0 = new Date(2026, 9, day, hour, 0, 0).getTime()
  return messages.map(([sender_id, sender, text, min], i) => ({
    id: tripId * 1000 + i,
    trip_id: tripId,
    sender_id,
    sender,
    text,
    ts: new Date(ts0 + min * 60_000).toISOString(),
  }))
}

export const CHAT_FIXTURES: Record<number, ChatMessage[]> = {
  // Trip 6: property damage
  6: buildChat(6, [
    [101, 'Sarah Chen', 'Hi, I noticed my luggage has a scratch after the ride.', 0],
    [201, 'Marcus Webb', 'I did not damage your luggage. It was already like that.', 2],
    [101, 'Sarah Chen', 'It was brand new. You loaded it roughly.', 4],
    [201, 'Marcus Webb', 'I was careful. There is no way I caused that.', 6],
  ], 10, 9),
  // Trip 7: property damage — driver admits
  7: buildChat(7, [
    [107, 'Nina Park', 'You spilled coffee on my laptop bag!', 0],
    [207, 'Carl Reed', 'I am sorry about that. The cup slipped.', 2],
    [107, 'Nina Park', 'I need compensation for the damage.', 4],
    [207, 'Carl Reed', 'I understand. Let me know what I can do.', 6],
  ], 11, 14),
  // Trip 8: safety incident
  8: buildChat(8, [
    [108, 'Owen Diaz', 'You were speeding through the school zone!', 0],
    [208, 'Maya Singh', 'I was going the speed limit. You are mistaken.', 1],
    [108, 'Owen Diaz', 'I felt very unsafe. Please slow down.', 3],
    [208, 'Maya Singh', 'You are overreacting. I was driving safely.', 5],
  ], 12, 8),
  // Trip 9: safety incident — driver admits
  9: buildChat(9, [
    [109, 'Iris Wong', 'You ran the red light at the intersection!', 0],
    [209, 'Ben Carter', 'I know, I am sorry. I misjudged the timing.', 1],
    [109, 'Iris Wong', 'That was extremely dangerous. We could have been hit.', 3],
    [209, 'Ben Carter', 'You are right. It was a mistake and I apologize.', 5],
  ], 13, 10),
}

/* ---------- Evidence builders ---------- */

export function buildRouteEvidence(
  tripId: number,
  actualKm: number,
  optimalKm: number,
  actualMin: number,
  estimatedMin: number,
): EvidenceItem {
  return {
    id: `route_deviation:${tripId}`,
    type: 'route_deviation',
    trip_id: tripId,
    summary: `Actual route was ${actualKm.toFixed(1)} km vs optimal ${optimalKm.toFixed(1)} km (${((actualKm - optimalKm) / optimalKm * 100).toFixed(0)}% longer).`,
    data: {
      actual_distance_km: actualKm,
      optimal_distance_km: optimalKm,
      actual_duration_min: actualMin,
      estimated_duration_min: estimatedMin,
      deviation_pct: ((actualKm - optimalKm) / optimalKm) * 100,
    },
    supports: 'rider',
    strength: 0.85,
  }
}

export function buildFareEvidence(
  tripId: number,
  baseFare: number,
  expectedFare: number,
  surgeMultiplier: number,
  surgePremium: number,
  promoDiscount: number,
  discrepancy: number,
  supports: 'rider' | 'driver' | 'neutral' = 'rider',
  strength = 0.8,
): EvidenceItem {
  return {
    id: `fare_validation:${tripId}`,
    type: 'fare_validation',
    trip_id: tripId,
    summary: `Recomputed expected fare $${expectedFare.toFixed(2)} vs charged $${(expectedFare + discrepancy).toFixed(2)}.`,
    data: {
      recomputed_base_fare: baseFare,
      recomputed_expected_fare: expectedFare,
      surge_multiplier: surgeMultiplier,
      surge_premium: surgePremium,
      promo_discount: promoDiscount,
      arithmetic_discrepancy: discrepancy,
      quote_discrepancy: discrepancy,
    },
    supports,
    strength,
  }
}

export function buildNoShowEvidence(
  tripId: number,
  driverArrived: boolean,
  arrivalTime: string | null,
  waitMin: number,
  minDistM: number,
  fee: number,
  supports: 'rider' | 'driver' | 'neutral',
  strength: number,
): EvidenceItem {
  return {
    id: `noshow:${tripId}`,
    type: 'noshow',
    trip_id: tripId,
    summary: driverArrived
      ? `Driver arrived at pickup and waited ${waitMin.toFixed(1)} min. Closest distance to rider: ${minDistM.toFixed(0)} m.`
      : `Driver did not reach the pickup area. Closest distance: ${minDistM.toFixed(0)} m.`,
    data: {
      driver_arrived: driverArrived,
      driver_arrival_time: arrivalTime,
      wait_duration_min: waitMin,
      min_distance_to_pickup_m: minDistM,
      fee,
    },
    supports,
    strength,
  }
}

export function buildChatAnalysisEvidence(
  tripId: number,
  threats: string[],
  admissions: string[],
  summary: string,
  supports: 'rider' | 'driver' | 'neutral',
  strength: number,
): EvidenceItem {
  return {
    id: `chat_analysis:${tripId}`,
    type: 'chat_analysis',
    trip_id: tripId,
    summary,
    data: {
      threats: threats.map((t) => ({ message_ids: [], text: t })),
      admissions: admissions.map((t) => ({ message_ids: [], text: t })),
      agreements: [],
      disagreements: [],
      key_claims: [],
    },
    supports,
    strength,
  }
}

export function buildHistoryProfile(
  tripId: number,
  riderRisk: number,
  driverRisk: number,
  riderPrevDisputes: number,
  driverPrevDisputes: number,
): EvidenceItem {
  return {
    id: `history_profile:${tripId}`,
    type: 'history',
    trip_id: tripId,
    summary: `Rider has ${riderPrevDisputes} previous disputes (risk ${riderRisk.toFixed(2)}). Driver has ${driverPrevDisputes} previous disputes (risk ${driverRisk.toFixed(2)}).`,
    data: {
      rider_abuse_risk_score: riderRisk,
      driver_abuse_risk_score: driverRisk,
      rider_previous_disputes: riderPrevDisputes,
      driver_previous_disputes: driverPrevDisputes,
    },
    supports: 'neutral',
    strength: 0.5,
  }
}
