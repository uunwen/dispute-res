# Past rulings: route deviation and fare disputes

Resolved under policy `ryde-policy-v0.4`. Rider and driver names are left out on purpose.

### PREC-RD-01 - 45% detour, no reason
- Type: Route deviation / fare; filed by the rider
- Complaint: "Driver took a very long way around and the fare is higher."
- Key facts: planned 11.27 km vs actual 16.34 km (+45.0%); estimate $15.57, charged $20.95; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** partial_refund; refund to rider $5.38; payer: driver; driver warning: yes; escalate: no
- Policy rules: RD-2, RD-3, G-6, G-7
- Reasoning: Actual distance 45% over plan, no reason on record (RD-3). Refund charged minus estimate, recover from the driver, warn.

### PREC-RD-02 - 12% longer, inside tolerance
- Type: Route deviation / fare; filed by the rider
- Complaint: "The route was longer than the estimate."
- Key facts: planned 3.94 km vs actual 4.41 km (+12.0%); estimate $7.79, charged $8.30; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: RD-2
- Reasoning: Distance is 12% over plan, inside the 15% tolerance (RD-2). No action.

### PREC-RD-03 - Rider asked to avoid the expressway
- Type: Route deviation / fare; filed by the rider
- Complaint: "The fare is higher than the estimate and the route was long."
- Key facts: planned 9.18 km vs actual 11.75 km (+28.0%); estimate $13.35, charged $16.78; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: RD-4, G-1
- Reasoning: Rider asked in chat to avoid the expressway, which made the trip 28% longer. A rider request is a valid reason (RD-4a).

### PREC-RD-04 - App reroute, within cap
- Type: Route deviation / fare; filed by the rider
- Complaint: "The route changed from the one I saw."
- Key facts: planned 15.23 km vs actual 17.82 km (+17.0%); estimate $19.79, charged $22.77; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: RD-4, RD-10
- Reasoning: App rerouted the driver around congestion (RD-4b). Charged total was within 120% of the estimate, so no cap refund (RD-10).

### PREC-RD-05 - Unconfirmed closure from a driver with a pattern
- Type: Route deviation / fare; filed by the rider
- Complaint: "He said the road was closed. It wasn't. I paid more."
- Key facts: planned 19.16 km vs actual 25.48 km (+33.0%); estimate $23.95, charged $30.68; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 5 past disputes, 1 fraud flags, 1 warnings in last 30 days
- **Ruling:** partial_refund; refund to rider $6.73; payer: driver; driver warning: yes; escalate: no
- Policy rules: RD-4, RD-3, G-6, G-7
- Reasoning: Driver claimed a closure the feed does not show. Excess refunded (RD-4). This driver has repeat route complaints and a recent warning, so a new warning is issued (G-7).

### PREC-RD-06 - ERP avoided, fare ended lower
- Type: Route deviation / fare; filed by the rider
- Complaint: "Driver went a different way and I think he overcharged me."
- Key facts: planned 10.39 km vs actual 12.67 km (+22.0%); estimate $18.64, charged $17.08; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: RD-5
- Reasoning: Driver took a longer route to avoid an ERP gantry. The final fare ended up below the estimate, so the rider was not worse off (RD-5). No refund, no warning.

### PREC-RD-07 - Two-minute stop
- Type: Route deviation / fare; filed by the rider
- Complaint: "He stopped and I was charged for waiting."
- Key facts: planned 15.06 km vs actual 15.06 km (+0.0%); estimate $19.59, charged $20.03; unscheduled stop 2 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: RD-6
- Reasoning: A 2 min unscheduled stop is within the 3 min allowance (RD-6). Nothing to refund.

### PREC-RD-08 - Promo not applied
- Type: Route deviation / fare; filed by the rider
- Complaint: "I entered RIDE5 and was charged without the discount."
- Key facts: planned 14.78 km vs actual 15.22 km (+3.0%); estimate $14.72, charged $20.18; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** partial_refund; refund to rider $5.00; payer: ryde; driver warning: no; escalate: no
- Policy rules: RD-7, G-6
- Reasoning: Promo RIDE5 (-$5.00) was validated at booking and not applied at charge. Refund the promo, Ryde pays (RD-7). No driver fault.

### PREC-RD-09 - Meter 30% above GPS
- Type: Route deviation / fare; filed by the rider
- Complaint: "The final fare is much more than I expected for this distance."
- Key facts: planned 12.89 km vs actual 13.14 km (+2.0%); estimate $16.23, charged $19.04; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** partial_refund; refund to rider $2.57; payer: ryde; driver warning: no; escalate: no
- Policy rules: RD-8, G-6
- Reasoning: Meter distance is 30% above the GPS trail on a normal route (RD-8). Use the GPS trail, refund the overcharge, flag for engineering. Ryde pays.

### PREC-RD-10 - Route matched plan, fare matched estimate
- Type: Route deviation / fare; filed by the rider
- Complaint: "I think I was overcharged."
- Key facts: planned 17.06 km vs actual 17.06 km (+0.0%); estimate $21.31, charged $21.31; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: RD-2, G-1
- Reasoning: The route matches the plan exactly and the charge equals the estimate. Nothing in the records supports the complaint.

### PREC-RD-11 - Destination fee, edit on record
- Type: Route deviation / fare; filed by the rider
- Complaint: "Why is there an extra $3 on my receipt?"
- Key facts: planned 4.38 km vs actual 4.51 km (+3.0%); estimate $8.25, charged $11.40; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: RD-11, G-1
- Reasoning: The receipt is S$3.00 above the estimate. The event log shows the rider asked to change the destination and the driver accepted, so the add/edit destination fee is valid (RD-11).

### PREC-RD-12 - Surge x1.2 quoted, x1.5 charged
- Type: Route deviation / fare; filed by the rider
- Complaint: "The app said 1.2 times surge at booking but I was charged more than that."
- Key facts: planned 12.03 km vs actual 12.39 km (+3.0%); estimate $19.52, charged $24.83; unscheduled stop 0 min; surge x1.2
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** partial_refund; refund to rider $4.85; payer: ryde; driver warning: no; escalate: no
- Policy rules: RD-13, G-6
- Reasoning: The booking quoted surge x1.2 but the charge used x1.5. The quoted multiplier binds (RD-13): refund the surge difference, Ryde pays.

### PREC-RD-13 - 41% detour by a driver with 2 recent warnings
- Type: Route deviation / fare; filed by the rider
- Complaint: "The driver went a long way around and the fare went up."
- Key facts: planned 19.37 km vs actual 27.31 km (+41.0%); estimate $24.18, charged $32.61; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 7 past disputes, 0 fraud flags, 2 warnings in last 30 days
- **Ruling:** partial_refund; refund to rider $8.43; payer: driver; driver warning: yes; escalate: no; fraud review recommended
- Policy rules: RD-3, G-10, G-6, G-7
- Reasoning: Actual distance 41% over plan with no reason on record (RD-3): refund the excess, charge the driver, warn. The driver already has 2 warnings in 30 days, so a fraud review is recommended (G-10e).

### PREC-RD-14 - Driver-filed: fare complaint, route inside tolerance
- Type: Route deviation / fare; filed by the driver
- Complaint: "The rider says the route was too long and wants money back. I followed the GPS."
- Key facts: planned 12.66 km vs actual 13.67 km (+8.0%); estimate $17.04, charged $18.12; unscheduled stop 0 min; surge x1.0
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: RD-2, RD-12
- Reasoning: Filed by the driver, who is contesting a rider's complaint. Distance is 8% over plan, inside tolerance (RD-2). The same rules apply whoever files (RD-12).
