# Fare and Surge Pricing Policy

### 3.1 Upfront Quote Binding

- The upfront quote presented to the rider at booking is **binding at the surge multiplier in effect at quote time** (typically 1.0x in normal conditions).
- The quoted fare includes: base fare, distance fare, time fare, booking fee, and any applicable surge.

### 3.2 Surge Change Notification

- If the surge multiplier **increases** between the time of quote and the time of trip start, the rider **MUST be notified** via an **in-app notification** before or at the point of pickup.
- The notification must clearly state:
  - The new surge multiplier.
  - The revised estimated fare.
  - An option to cancel without penalty.

### 3.3 Refund Eligibility

| Scenario | Rider Notified? | Refund |
|---|---|---|
| Surge increases, rider notified, rider proceeds | Yes | No refund — higher fare applies |
| Surge increases, rider **not** notified | No | **Full refund of the surge differential** (actual fare − quoted fare) |
| Surge decreases between quote and trip start | N/A | Lower fare applies automatically (rider benefits) |
| Surge unchanged | N/A | Quoted fare applies |

### 3.4 Surge Differential Calculation

```
surge_differential = actual_fare − upfront_quote
```

Where the difference is attributable solely to a surge multiplier change (all other fare components unchanged), the full differential is refundable if the rider was not notified.

### 3.5 Surge-Exempt Components

The following fare components are **exempt** from surge pricing and remain fixed regardless of multiplier:

- Booking fee

All other components (base fare, distance fare, time fare) are subject to the surge multiplier.

---
