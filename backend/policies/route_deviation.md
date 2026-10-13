# Route Deviation Policy

## 1. Definition
A route deviation occurs when the driver's GPS path strays from the optimal route
by more than the buffer threshold for a material portion of the trip.

## 2. Detection Thresholds
- Off-route buffer: 100 m from the optimal route polyline.
- Minor deviation: extra distance under 0.5 km.
- Moderate deviation: extra distance between 0.5 km and 2.0 km.
- Major deviation: extra distance over 2.0 km.
- A deviation is "bad-faith" when it exceeds 2.0 km and no traffic or road-closure
  justification is recorded.

## 3. Legitimate Detours
A deviation is legitimate when it is supported by a traffic signal (average speed on
the optimal route below 15 km/h) or a documented road closure. No penalty applies.

## 4. Refund Guidance
- Major bad-faith deviation: full refund of the fare.
- Moderate deviation without justification: partial refund of 25% of the fare.
- Minor or justified deviation: no refund.

## 5. Evidence Requirements
Rulings must cite route evidence (fraction off-route, extra distance, traffic signal)
by evidence id before a refund is granted.
