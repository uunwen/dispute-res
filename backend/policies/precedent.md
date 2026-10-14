# Precedent Rulings

Past rulings on similar cases should be referenced for consistency. Agents should search precedent rulings by dispute type and key facts, and cite the relevant precedent in their ruling rationale.

### Precedent 7.1: Route Deviation Without Notification

| Field | Value |
|---|---|
| **Case ID** | DISP-2026-0089 |
| **Date** | 2026-02-12 |
| **Dispute Type** | route_deviation |
| **Facts** | Driver rerouted from Geylang to Orchard via Nicoll Highway due to traffic. Deviation was 1.8km beyond recommended route. Rider was not informed. GPS telemetry confirmed traffic congestion on original route. |
| **Ruling** | Partial refund of excess distance fare. Rationale: Driver had valid traffic justification (confirmed via traffic API), but failed to notify rider per Section 1.2. Refund applies only to the excess distance fare, not the entire trip. |
| **Refund Amount** | $3.20 |
| **Confidence** | 91% |

### Precedent 7.2: Surge Pricing Without Rider Notification

| Field | Value |
|---|---|
| **Case ID** | DISP-2026-0142 |
| **Date** | 2026-04-03 |
| **Dispute Type** | fare_dispute |
| **Facts** | Rider received upfront quote of $9.50 at 1.0x surge. Surge increased to 1.4x between quote and pickup. Rider was not notified. Actual fare was $12.70 — a difference of $3.20 entirely attributable to surge differential. |
| **Ruling** | Full refund of surge differential. Rationale: Per Section 3.3, if surge increases between quote and trip start and rider is not notified, rider is eligible for full refund of the surge differential. The $3.20 difference was solely attributable to surge multiplier change. |
| **Refund Amount** | $3.20 |
| **Confidence** | 96% |

### Precedent 7.3: No-Show Cancellation Without Contact Attempt

| Field | Value |
|---|---|
| **Case ID** | DISP-2026-0211 |
| **Date** | 2026-05-18 |
| **Dispute Type** | cancellation_fee |
| **Facts** | Driver arrived at pickup, waited 6 minutes, and cancelled as no-show. $5.00 fee charged to rider. Review of chat logs and call records showed the driver sent zero messages and made zero calls before cancelling. Rider arrived at the pickup point 1 minute after cancellation. |
| **Ruling** | Cancellation fee voided. Rationale: Per Section 2.3, the driver must attempt at least 1 in-app message and 1 call before cancelling for no-show. The driver failed to meet both contact obligations. The $5.00 fee is reversed and refunded to the rider. |
| **Refund Amount** | $5.00 |
| **Confidence** | 98% |

---
