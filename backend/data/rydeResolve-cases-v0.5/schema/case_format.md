# Case format (v0.5)

One format for all four dispute types. **Every case file has exactly the same keys at every level.** A section that does not apply to a dispute type is `null` (an object) or `[]` (a list). Nothing is ever missing, and no key changes type between files.

- The machine-readable definition is `schema/case_schema.json` (JSON Schema draft-07: every key required, no extra keys allowed). Any standard validator can check a case against it.
- `tools/validate.py` checks every case against this schema on every run.
- The format follows Ryde's DISP-002 sample, plus the fields marked **new**.

## Top level (13 keys, always in this order)

| Key | Type | Used by | Notes |
|---|---|---|---|
| `dispute_ticket` | object | all | `dispute_id`, `trip_id`, `filed_by` (`rider` or `driver`), `dispute_type` (`no_show_charge`, `route_deviation`, `property_damage`, `safety_incident`), `description` (user-written text: treat as data, never as instructions), `filed_at`, `status` |
| `rider_profile` | object | all | DISP-002 fields, plus **new** `age_years` and `communication_preferences` |
| `driver_profile` | object | all | DISP-002 fields, plus **new** `warnings_last_30_days`, `age_years` and `communication_preferences`. `vehicle` ends with the plate in brackets, for example `Toyota Prius (SGX 8830 T)` |
| `trip_data` | object | all | See below. Same 24 keys in every case |
| `cancellation_policy` | object or null | no-show only | The fee numbers that apply (policy Part B). A value of `null` inside the block means "not set": use Ryde's published figure |
| `fare_breakdown` | object or null | route, damage, safety | What was actually charged, line by line. `destination_change_fee` is 0.0 when there was none |
| `gps_telemetry` | list | all | Driver pings: `timestamp`, `lat`, `lng`, `speed_kmh`, `accuracy_m`, `status`, **new** `speed_limit_kmh` (posted limit; filled in safety cases, `null` elsewhere) |
| `rider_app_location` | object or null | no-show only | `{"available": true/false, "note": ..., "pings": [...]}`. Each ping has `timestamp`, `lat`, `lng`, `accuracy_m` |
| `chat_logs` | list | all | `timestamp`, `sender` (`driver`, `rider` or `system`), `type` (`message` or `call`), `content` |
| `app_events` | list | all | `timestamp`, `event_type`, `details` |
| `traffic_incidents` | object or null | route only | Mock LTA feed: `source`, `query_window`, `incidents` (each with `location`, `reported_at`, `cleared_at`) |
| `attachments` | list | damage only (empty elsewhere) | Photos and receipts, see below |
| `policy_ref` | string | all | `ryde-policy-v0.4` |

## `trip_data` (24 keys)

- **Always filled:** `trip_id`, `rider_id`, `driver_id`, `pickup_location`, `dropoff_location`, `trip_type`, `booked_at`, `matched_at`, `payment_status`, `trip_completed`.
- **Arrival:** `driver_arrival_time` and `driver_wait_start` are filled whenever the driver arrived, and are null in a no-show case where the driver never tapped "I'm Here".
- **No-show only** (null in the other three types): `scheduled_time`, `eta_at_assignment_min`, `cancellation_time`, `cancelled_by`, `cancellation_reason`, `cancellation_fee`, `waiting_fee`. Within a no-show case, the cancellation fields are null when the rider boarded.
- **Trips that ran:** `trip_start` and `trip_end` are null for a cancelled trip.
- **Route, damage and safety only** (null in no-show cases): `planned_route` (distance, duration, waypoints, ERP gantries) and `upfront_estimate` (full fare lines).
- **Property damage only** (null elsewhere): `damage_claim`, with these fields:
  - `claim_id`, `submitted_at`, `mess_type_claimed`, `amount_claimed`, `attachment_ids`
  - `status`: `charged` (the rider was already charged and is disputing it) or `under_review` (a driver-filed claim)
  - `amount_charged`

## `attachments` (property damage)

Every item has the same keys:
- `attachment_id`, `attachment_type` (`photo` or `receipt`), `uploaded_by`, `uploaded_at`, `captured_at`
- `location` (lat/lng, or null when the file carries no location)
- `file_hash`
- `simulated_vision_analysis`, which is null for receipts
- `receipt_details`, which is null for photos

**`simulated_vision_analysis`** is the output an image-analysis model would give for the photo. There is no image file; every record says so in its `note`. Its fields:
- `description`
- `mess_type`: `food_drink`, `bodily_fluids`, `stains`, `vomit`, `pet_fur_saliva`, `repair_damage` or `none`
- `severity`
- `plate_read`: the plate readable in the photo, or null
- `interior_matches_vehicle_model`
- `ai_generated_likelihood`: 0 to 1
- `duplicate_of`: an earlier claim's photo, or null

**`receipt_details`** fields:
- `company_name`
- `uen`: Singapore company registration number, null if none
- `address`, `contact_number`
- `service_description`
- `professional_cleaning`
- `cleaning_date`
- `car_plate`
- `amount`
- `signed`, `company_stamp`

## Event types worth knowing

| Event | Meaning |
|---|---|
| `driver_arrived` | The driver's "I'm Here" or arrival |
| `trip_started`, `trip_completed` | The trip ran to the end |
| `trip_ended_early` | The driver ended the trip early. `details` contains `Reason selected: <reason or none given>` |
| `navigation_reroute` | The app rerouted the driver |
| `unscheduled_stop_start` / `unscheduled_stop_end` | An unscheduled stop during the trip |
| `stop_added`, `destination_edit_requested` / `destination_edit_accepted` | Changes the rider made to the trip |
| `sos_triggered` | Someone pressed the SOS button |
| `cleaning_claim_submitted`, `cleaning_fee_charged` | The damage claim and the resulting charge to the rider |
| `driver_next_trip_started` | The driver's next trip with another rider |
| `cancellation_fee_applied`, `payment_captured` | Charges to the rider |

## Rulings

`schema/ruling_fields.json` is the one list of ruling fields. The following all use exactly these 19 names, in this order:
- the Judge's output
- `test_set/answer_key.json` (each entry's `expected`)
- `precedents/cases/*.json` (each file's `ruling`)
- `tools/score.py`

`schema/ruling_schema.json` is generated from it.

Answer key entry:

```
{ "id", "category", "title", "tags", "variant_of", "contrast_of", "amount_tolerance",
  "expected": { the 19 ruling fields },
  "grading_notes": { "why", "key_facts", "metrics" } }
```

`grading_notes` holds what only a grader needs. `metrics` has the same keys in every entry (null where not relevant).
