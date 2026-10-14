# No-Show and Cancellation Fee Policy

## 1. Definition and Scope

A no-show or cancellation dispute arises when a rider disputes a cancellation fee or a waiting time fee, for example "The driver didn't show up but I was charged a cancellation fee."
Category: no_show. Two fee types exist: the cancellation fee and the waiting time fee. Ryde's published policy states that it applies to all service types.
The applicable product, booking type and fee schedule must be confirmed from the trip record before an automated assessment.
A driver who cancels after a rider no-show is not penalised for that cancellation (Ryde Driver-Partner Handbook).

## 2. Decision Variables

On-demand trips (Ryde published):

- Cancellation grace period: 3 minutes from the time the rider is matched. A cancellation within 3 minutes has no fee.
- Cancellation fee: $4.50, charged if the rider cancels more than 3 minutes after being matched.
- Waiting threshold: the driver must have pressed "I'm Here" and waited more than 3 minutes for the rider to arrive or board.
- Waiting time fee: $4.50, charged if the driver waited more than 3 minutes and then cancelled (rider no-show) or completed the trip.
- Waiting fee discrepancy: another Ryde help article mentions a $5 waiting time fee. A waiting fee other than $4.50 is a discrepancy and goes to HUMAN_REVIEW.
  Advanced bookings (Ryde published):
- Free cancellation window: more than 15 minutes before the scheduled pickup time. Example: for a 6 PM trip, cancelling before 5:45 PM is free.
- Cancellation fee: $4.50 if the rider cancels inside the 15-minute window or after matching.
- Late-accepted requests: a request accepted after the 15-minute window gives the rider a 3-minute grace period.
- Waiting time fee: $4.50 under the same conditions as on-demand trips.
  Team simulation values (not Ryde rules):
- Arrival radius: 100 m. The driver counts as arrived only if the driver's recorded GPS position at the "I'm Here" press is within 100 m of the pickup point. Ryde publishes no geofence.
- GPS error tolerance: if the reported GPS accuracy is larger than the 100 m arrival radius, arrival is not proven by that position.

## 3. Evidence Required

- Required: pickup location, driver location with accuracy, match time, the driver's "I'm Here" press (timestamp and location), arrival and cancel timestamps, the charged fee, service type.
- Corroborating: chat or call metadata, driver status changes, booking terms.
- Never infer arrival or waiting time when the records do not show it.

## 4. Exceptions

- GPS uncertainty.
- An inaccessible pickup point.
- An agreed alternate pickup.
- Communication failures.

## 5. Decision Rules

- NS-001A: verified charge violates the published cancellation or waiting rule. Examples: the rider cancelled within the 3-minute grace period, the driver did not press "I'm Here", or the driver waited 3 minutes or less. Outcome: REFUND_FULL or REFUND_PARTIAL, per the confirmed rule.
- NS-001B: the charge meets all verified conditions and no exception applies. Outcome: NO_ADJUSTMENT.
- NS-001C: arrival or timing is disputed and not independently resolved. Outcome: REQUEST_EVIDENCE or HUMAN_REVIEW.

## 6. Refund Guidance

- REFUND_FULL of the disputed fee when the whole charge is not allowed by the rules in section 2.
- REFUND_PARTIAL when only part of the charge is invalid, for example when the charged amount exceeds the published fee. Show the calculation.
- The refund is a proposed action only. See [general_principles#2].

## 7. Missing or Conflicting Evidence

- Without reliable arrival or timing evidence, do not assume either party is at fault.
- Conflicting GPS and timestamp evidence on a decisive fact: NS-001C and escalation under [general_principles#4].

## 8. Sources

- Ryde Help Centre, Cancellation and Waiting Time Policy (read 10 October 2026).
- Ryde Help Centre, How Does the Waiting Fee Work? (read 10 October 2026), source of the $5 mention.
- Ryde Official Driver-Partner Handbook 2025, p. 12 (driver cancellation on rider no-show).
