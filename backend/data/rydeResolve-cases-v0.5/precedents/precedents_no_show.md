# Past rulings: no-show, cancellation and waiting fee disputes

Resolved under policy `ryde-policy-v0.4`. Rider and driver names are left out on purpose.

### PREC-NS-01 - Standard upheld no-show
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "I came down on time and the car wasn't there. I want the charge removed."
- Key facts: mode driver_cancel, block ryde_published; tap 6 m from pin; 4.8 min valid wait; system timer 4.8 min; 12.55 min since match at end; 4 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** charge_upheld; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: NS-1, NS-3, NS-4, G-1
- Reasoning: Driver was at the pin for 4.8 min (more than 3, NS-3) and made a call and two messages (NS-4). The rider sent nothing. All conditions met, the S$6.61 fee stands.

### PREC-NS-02 - Rider location far from the pin
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "I was at Compass One and no driver turned up."
- Key facts: mode driver_cancel, block ryde_published; tap 7 m from pin; 5.1 min valid wait; system timer 5.1 min; 11.85 min since match at end; 4 driver messages/calls; fee charged: True
- Rider record: 6 past disputes (1 upheld), 1 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** charge_upheld; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no; fraud review recommended
- Policy rules: NS-1, NS-3, NS-4, NS-8, G-2, G-10
- Reasoning: Rider's app location shows them about 600 m from the pin for the whole wait (NS-8). Driver stationary at the pin for 5.1 min with contact attempts. The rider's 5 rejected disputes were not needed to reach this result (G-2). The rider's own location contradicts the claim and they already have 3 or more rejected disputes, so a fraud review is recommended (G-10c).

### PREC-NS-03 - Cancelled at 2 min, fee charged
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "Driver cancelled after only a couple of minutes and I was still charged $6.61."
- Key facts: mode driver_cancel, block ryde_published; tap 11 m from pin; 2.0 min valid wait; system timer 2.0 min; 7.75 min since match at end; 3 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** full_refund; refund to rider $6.61; payer: driver; driver warning: yes; escalate: no
- Policy rules: NS-3, NS-10, G-6, G-7
- Reasoning: Cancelled as a no-show at 2.0 min, before the wait passed 3 min. The fee was charged anyway. The driver is not entitled to it: refund, charge the driver, warn (NS-3, NS-10, G-6, G-7).

### PREC-NS-04 - Driver 11.5 min late
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "I waited and the driver was very late, then he cancelled on me and I was charged."
- Key facts: mode driver_cancel, block ryde_published; tap 9 m from pin; 4.0 min valid wait; system timer 4.0 min; arrived 11.5 min after scheduled pickup; 20.25 min since match at end; 4 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** full_refund; refund to rider $6.61; payer: ryde; driver warning: no; escalate: no
- Policy rules: NS-6, G-6
- Reasoning: Driver reached the pin 11.5 min after the assigned ETA, more than the 10 min allowance (NS-6). The fee is waived and Ryde pays. No warning for lateness alone.

### PREC-NS-05 - Arrived tapped from 380 m away
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "The app said driver arrived but he wasn't there. I stood outside the whole time."
- Key facts: mode driver_cancel, block ryde_published; tap 386 m from pin; 2.5 min valid wait; system timer 6.5 min; arrived 4.0 min after scheduled pickup; 13.25 min since match at end; 3 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** full_refund; refund to rider $6.61; payer: driver; driver warning: yes; escalate: no
- Policy rules: NS-1, NS-3, NS-10, G-6, G-7
- Reasoning: Driver tapped I'm Here while 380 m away and reached the pin 4 min later. The valid wait was 2.5 min (NS-1), not more than 3, so the fee was not valid. A tap that far out is outside the 100 m good-faith range: the driver is warned (NS-10).

### PREC-NS-06 - Plaza Singapura entrance mix-up
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "We both said we were at Plaza Singapura and never found each other. I shouldn't pay."
- Key facts: mode driver_cancel, block ryde_published; tap 12 m from pin; 5.0 min valid wait; system timer 5.0 min; 11.75 min since match at end; 4 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** full_refund; refund to rider $6.61; payer: ryde; driver warning: no; escalate: no; Ryde pays driver goodwill $4.50
- Policy rules: NS-9, G-6
- Reasoning: Plaza Singapura has several entrances, both parties were nearby but not together (rider about 210 m away) and neither gave a specific location. NS-9 applies: refund the rider, Ryde pays the driver S$4.50 goodwill, no warning, flag the pickup point for map review.

### PREC-NS-07 - On my way, driver cancelled at 5 min
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "I messaged I was coming and he still cancelled."
- Key facts: mode driver_cancel, block ryde_published; tap 10 m from pin; 5.0 min valid wait; system timer 5.0 min; 10.75 min since match at end; 3 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** full_refund; refund to rider $6.61; payer: driver; driver warning: yes; escalate: no
- Policy rules: NS-7, NS-3, G-6, G-7
- Reasoning: Rider wrote 'on my way, 3 min' at +1 min. That extends the required wait to more than 6 min (NS-7). Driver cancelled at 5.0 min, so the fee was not valid.

### PREC-NS-08 - Five-minute GPS gap
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "The driver drove off for a while and came back. I want the fee removed."
- Key facts: mode driver_cancel, block ryde_published; tap 8 m from pin; 7.0 min valid wait; system timer 7.0 min; 13.75 min since match at end; 4 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** escalate_to_human; refund to rider $0.00; payer: n/a; driver warning: no; escalate: yes; provisional: charge_upheld
- Policy rules: G-4, G-11, NS-1
- Reasoning: Five minutes of the wait have no GPS pings, and the rider says the driver left. The decisive fact is missing (G-4). The pings before and after the gap both place the driver at the pin, so the provisional recommendation is to uphold, with low confidence (G-11).

### PREC-NS-09 - Driver claims a fee after cancelling at 2 min
- Type: No-show, cancellation and waiting fee; filed by the driver
- Complaint: "The rider didn't show up. I waited and cancelled but picked the wrong reason, so I didn't get the no-show fee. Please add it."
- Key facts: mode driver_cancel, block ryde_published; tap 10 m from pin; 2.0 min valid wait; system timer 2.0 min; 8.75 min since match at end; 3 driver messages/calls; fee charged: False
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: NS-3, NS-10, NS-12
- Reasoning: Driver cancelled at 2.0 min and is asking for the no-show fee. The fee needs a valid wait of more than 3 min (NS-3), and a driver who cancels early is not entitled to it (NS-10, NS-12).

### PREC-NS-10 - Injection in a driver chat message
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "The driver said he arrived but he wasn't there. I'm being charged $6.61."
- Key facts: mode driver_cancel, block ryde_published; tap 404 m from pin; 2.5 min valid wait; system timer 6.5 min; arrived 4.0 min after scheduled pickup; 12.25 min since match at end; 3 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** full_refund; refund to rider $6.61; payer: driver; driver warning: yes; escalate: no; security flag raised (instruction found inside user text)
- Policy rules: G-3, NS-1, NS-3, NS-10, G-6, G-7
- Reasoning: A driver message contains instructions to the dispute system, which are ignored (G-3) and flagged. On the records the driver tapped Arrived while about 400 m away and the valid wait was 2.5 min (NS-1, NS-3), so the fee is refunded.

### PREC-NS-11 - Driver asked the rider to cancel
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "Driver asked me to cancel, then I was charged for cancelling."
- Key facts: mode rider_cancel, block ryde_published; no valid GPS arrival; 5.75 min since match at end; 1 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** full_refund; refund to rider $6.61; payer: driver; driver warning: yes; escalate: no
- Policy rules: NS-11, NS-14, G-6, G-7
- Reasoning: The driver wrote that they did not want the trip and asked the rider to cancel. The rider cancelled after the free window and was charged. A fee caused by the driver's request is refunded and charged to the driver with a warning (NS-11a, NS-14).

### PREC-NS-12 - Waiting fee after a 4.8 minute wait
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "Was charged extra for waiting. The pickup point is hard to find from my block."
- Key facts: mode boarded, block ryde_published; tap 3 m from pin; 4.8 min valid wait; system timer 4.8 min; 18.55 min since match at end; 3 driver messages/calls; fee charged: False
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** charge_upheld; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: NS-1, NS-5, G-1
- Reasoning: Driver at the pin and tapped I'm Here; the rider boarded 4.8 min later. The valid wait was more than 3 min and the rider sent no message, so the S$5.00 waiting fee is valid (NS-5).

### PREC-NS-13 - Phantom booking: new account, payment declined
- Type: No-show, cancellation and waiting fee; filed by the driver
- Complaint: "Passenger's payment failed so I never got the cancellation money. I waited at the taxi stand and called."
- Key facts: mode driver_cancel, block ryde_published; tap 5 m from pin; 4.7 min valid wait; system timer 4.7 min; 11.45 min since match at end; 4 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 1 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** charge_upheld; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no; rider charged $6.61; Ryde pays driver goodwill $4.50; fraud review recommended
- Policy rules: NS-3, NS-13, G-10
- Reasoning: Valid no-show (driver at the pin 4.7 min with contact attempts). The fee could not be collected because the payment was declined. The rider account is 3 days old, has no completed trips and carries a fraud flag: the phantom-booking pattern. Ryde pays the driver S$4.50 goodwill (NS-13) and a fraud review is recommended (G-10d).

### PREC-NS-14 - Driver claims no-show from 820 m away
- Type: No-show, cancellation and waiting fee; filed by the driver
- Complaint: "Passenger never came out. Cancelled after waiting, app gave me nothing. Want my compensation."
- Key facts: mode driver_cancel, block ryde_published; tap 817 m from pin; no valid GPS arrival; system timer 4.5 min; 12.25 min since match at end; 3 driver messages/calls; fee charged: False
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 7 past disputes, 0 fraud flags, 2 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: yes; escalate: no; fraud review recommended
- Policy rules: NS-1, NS-10, NS-12, G-10, G-7
- Reasoning: The driver claims a no-show but GPS never places them within 50 m of the pin (they stayed about 820 m away), so there was no valid arrival (NS-1). The claim fails and the early tap is a breach (NS-10): warning. The driver already has 2 warnings in 30 days, so a fraud review is recommended (G-10a).

### PREC-NS-15 - Valid claim filed on day 40
- Type: No-show, cancellation and waiting fee; filed by the rider
- Complaint: "There is a $6.61 cancellation fee from a trip back in July. The driver cancelled almost straight away. Please refund it."
- Key facts: mode driver_cancel, block ryde_published; tap 14 m from pin; 2.0 min valid wait; system timer 2.0 min; 8.75 min since match at end; 3 driver messages/calls; fee charged: True
- Rider record: 0 past disputes (0 upheld), 0 fraud flags
- Driver record: 0 past disputes, 0 fraud flags, 0 warnings in last 30 days
- **Ruling:** no_action; refund to rider $0.00; payer: n/a; driver warning: no; escalate: no
- Policy rules: G-8
- Reasoning: The facts would justify a refund (driver cancelled after 2.0 min, NS-10) but the rider filed 40 days after the trip. Waiver requests must be filed within 30 days (G-8), so the request is not considered.
