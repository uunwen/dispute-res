# Route Deviation Policy

### 1.1 General Principle

Drivers are permitted to reroute from the GPS-recommended path in response to real-time traffic conditions, road closures, or congestion. However, the rider must be informed of any deviation.

### 1.2 Notification Requirement

- The driver **MUST** inform the rider of a route deviation via **in-app chat** or **verbally** (with the trip call recording as evidence) **before or at the point of deviation**.
- A brief reason (e.g., "traffic jam ahead on Nicoll Highway, taking alternate route") is sufficient.

### 1.3 Refund Eligibility Matrix

| Scenario | Rider Informed? | Deviation > 1km? | Refund |
|---|---|---|---|
| Driver reroutes for traffic, rider informed and agrees | Yes | Yes | No refund |
| Driver reroutes for traffic, rider **not** informed | No | Yes | Partial refund of excess distance fare |
| Driver reroutes for traffic, rider not informed | No | No (≤ 1km) | No refund (within tolerance) |
| Driver reroutes **without** traffic justification (no evidence of congestion) | N/A | Yes | **Full refund** of excess distance fare |
| Driver reroutes without justification, deviation ≤ 1km | N/A | No | No refund (within tolerance) |

### 1.4 Evidence Requirements

- Traffic justification is verified via **historical traffic API data** for the route segment at the trip time.
- Route deviation distance is calculated as: `actual_route_distance − recommended_route_distance`.
- If the driver's in-app chat or call recording confirms rider acknowledgment, the deviation is considered agreed.

---
