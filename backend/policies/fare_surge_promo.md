# Fare, Surge and Promo Policy

## 1. Definition

A fare dispute arises when a rider disputes the fare itself rather than the route, for example a surge multiplier they did not expect or a promo code that was not applied.
Category: fare_dispute. The hackathon handbook lists the fare breakdown, surge pricing and promo usage as evidence sources.
No published Ryde pricing rule was found in the sources reviewed, so the rules below are proposed prototype rules.

## 2. Decision Variables

- Fare tolerance: a charged fare within 5% of the expected fare counts as matching. (simulation assumption, not a Ryde rule)
- Expected fare: the fare computed from the pricing basis recorded in the trip and booking record, including the surge multiplier and promo applied.
- Surge accepted at booking: a surge multiplier that the booking record shows was displayed to and confirmed by the rider is part of the verified pricing basis. A surge that was applied but not shown or not confirmed is not. (proposed rule)
- Promo: a promo code recorded as applied or eligible at booking must be reflected in the charged fare.

## 3. Evidence Required

- Required: fare breakdown, surge multiplier and the time it applied, promo code usage, booking record showing what the rider saw and accepted.
- Corroborating: rider-driver messages, route or trip changes that affected the fare.
- Never infer missing fare data.

## 4. Exceptions

- A surge multiplier shown to and confirmed by the rider at booking.
- A promo that the record shows was expired or ineligible under its terms.
- A fare change caused by a rider-requested change to the trip.

## 5. Decision Rules

Rule ids follow the v2.0 policy document.

- RD-002A: the verified fare breakdown does not match the pricing basis, surge multiplier or promo terms, and the difference is above the 5% tolerance. Outcome: REFUND_PARTIAL, or REFUND_FULL if the whole charge is unsupported. Calculation and evidence citations are required.
- RD-002B: the fare matches the verified pricing basis, surge and promo terms, or is within tolerance. Outcome: NO_ADJUSTMENT.
- RD-002C: pricing basis, surge or promo terms are unavailable or contradictory. Outcome: REQUEST_EVIDENCE or HUMAN_REVIEW.

## 6. Refund Guidance

- REFUND_PARTIAL equals the charged fare minus the expected fare, only where the difference is above the 5% tolerance.
- Show the calculation: charged fare, expected fare, surge multiplier, promo value.
- The refund is a proposed action only. See [general_principles#2].

## 7. Missing or Conflicting Evidence

- If the pricing basis, surge terms or promo terms are missing, do not calculate an unsupported refund. Outcome: REQUEST_EVIDENCE.
- If the booking record and the charge contradict each other on a decisive fact: HUMAN_REVIEW under [general_principles#4].

## 8. Sources

- Tencent Cloud AI Singapore Hackathon 2026 Handbook, Digital Native Track - Ryde, pp. 20-25 (fare disputes and fare data evidence).
