# Route Deviation Policy

## 1. Definition

A route deviation occurs when the driver's actual GPS path differs from the reference (optimal) route between pickup and drop-off.
A deviation only matters if it is unjustified and causes a verified excess charge. A longer distance alone is not enough to uphold a dispute.
Category: route_deviation. Typical complaint: "The driver took a longer route and I was overcharged."
Ryde's Driver-Partner Handbook tells drivers to travel directly to the pick-up and drop-off locations and treats overcharging riders or manipulating fares as fraud. Neither Ryde source sets a numeric detour threshold.

## 2. Decision Variables

- Off-route buffer: 100 m from the reference route polyline. GPS points inside the buffer count as on-route. (simulation assumption, not a Ryde rule)
- Major deviation: extra distance over 2.0 km compared with the reference route. (simulation assumption, not a Ryde rule)
- Reference route: the optimal route between the recorded pickup and drop-off, compared as data points (route, distance, time).
- Excess charge: charged fare minus the fare for the reference route under the same pricing basis, including any surge multiplier or promo applied.
- GPS quality: no accuracy threshold is set. If GPS gaps or low accuracy affect the decisive part of the route, treat the evidence as insufficient (see section 7).
- Traffic-explained: a deviation is explained by traffic or closure only when contemporaneous traffic or closure evidence for that time and location is in the evidence record. Without it the justification is unproven.

## 3. Evidence Required

- Required where available: actual GPS route and time, reference route and time, trip fare and pricing basis (surge multiplier, promo code).
- Corroborating: traffic or closure information, rider-driver messages, stops, pickup or drop-off changes.
- Never infer that missing GPS, messages or fare data exist.

## 4. Exceptions

A deviation is justified, and no route-deviation adjustment applies, when reliable contemporaneous evidence shows one of these:

- Road closure or traffic that blocked or slowed the reference route.
- A safety need.
- A rider-requested detour, an added stop (multi-stop), an edited destination, or a changed pickup or drop-off.
- Legitimate route optimisation, where the driver's route was equal or better than the reference route.
  A rider-requested change exempts the driver for the part of the route it affected.

## 5. Decision Rules

- RD-001A: verified unjustified detour AND verified attributable excess charge. Outcome: REFUND_PARTIAL. Calculation and evidence citations are required.
- RD-001B: detour justified by reliable contemporaneous evidence. Outcome: NO_ADJUSTMENT on route-deviation grounds.
- RD-001C: material route or price contradiction, or insufficient evidence. Outcome: REQUEST_EVIDENCE or HUMAN_REVIEW.
- A deviation over 2.0 km extra distance is labelled major in the ruling. The label does not change the refund rule and does not by itself show bad faith.

## 6. Refund Guidance

- REFUND_PARTIAL equals the verified excess charge from section 2, not the whole fare.
- Show the calculation: reference versus actual distance and time, fare difference, pricing basis.
- If fraud or abuse is suspected, refer for review under [general_principles#4]. Never label a person guilty.
- The refund is a proposed action only. See [general_principles#2].

## 7. Missing or Conflicting Evidence

- Reference route or pricing basis unavailable: do not calculate an unsupported excess fare. Outcome: REQUEST_EVIDENCE.
- Evidence sources contradict on a decisive fact: HUMAN_REVIEW under [general_principles#4].
- Do not decide in favour of either party by default.

## 8. Sources

- Ryde Official Driver-Partner Handbook 2025 (last updated 11 April 2025), pp. 2 and 13.
- Tencent Cloud AI Singapore Hackathon 2026 Handbook, Digital Native Track - Ryde, p. 24 (sample dispute categories).
