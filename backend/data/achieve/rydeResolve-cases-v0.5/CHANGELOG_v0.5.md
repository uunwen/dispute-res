# Changelog: v0.4 to v0.5 (12 Oct 2026)

## In one paragraph

v0.5 adds the two dispute types the brief lists that v0.4 did not cover: property damage and cleaning fees, and safety incidents. It puts every file in one format.
- **Test cases:** 69 to 93. All 69 existing cases are kept, and none changed outcome or amount.
- **Past rulings:** 29 to 41.
- **Policy:** v0.3 to v0.4. It adds Parts PD and SF and clarifies how G-4, G-6, G-7 and G-10 apply to them. No earlier Sourced rule or number changed.

## Format (Yun Wen's request)

- **Cases:** every case file now has the same 13 top-level keys and the same keys at every level (`schema/case_schema.json`, checked on every build).
  - New top-level key `attachments`.
  - New `trip_data.damage_claim`.
  - New `speed_limit_kmh` on every GPS ping.
  - Sections a type does not use are `null` or `[]`.
- **`rider_app_location`** is always an object (`available`, `note`, `pings`) or `null`. It used to be a list in some files.
- **`cancellation_policy`:** keys the DISP-002 block does not set are now `null` (policy Part B: null means "use Ryde's published figure").
- **`fare_breakdown.destination_change_fee`** is always present (0.0 when there was none).
- **One ruling field list** (`schema/ruling_fields.json`, 19 fields), used by the Judge, the answer key, the past rulings and the scorer.
  - The key's `rules` and `why` are now `rules_cited` and `reasoning`, matching the past rulings.
  - Grader-only notes moved to `grading_notes`.
- **New ruling fields:** `rider_charge_amount`, `rider_warning`, `safety_referral`.

## Existing cases: what changed

Only the new fields were filled in. No outcome, amount, payer, warning, escalation or flag changed.

| Case | Change | Why |
|---|---|---|
| NS-28, NS-29, NS-43, PREC-NS-13 | `rider_charge_amount` 6.61 | A driver's upheld claim for an unapplied fee charges the rider now (NS-12) |
| NS-33 | `safety_referral` true; `rules_cited` adds SF-1 | A threat in chat (SF-1) |
| RD-20 | `safety_referral` true; `rules_cited` adds SF-1 | Rider asked to be let out and the driver refused (SF-1) |
| NS-41 | `safety_referral` true | Car did not match the app: a policy gap and a safety concern (NS-15, G-4) |

Case content (GPS, chat, events, people, tickets) of all 69 existing test cases is identical to v0.4. Only the new keys were added.

## New test cases: property damage (12)

| Case | Title | Expected | Refund | Other fields |
|---|---|---|---|---|
| PD-01 | Vomit claim with full evidence, rider denies being sick | charge_upheld | - | - |
| PD-02 | Drink spill claimed as bodily fluids | partial_refund | S$80.00 | driver pays |
| PD-03 | Torn seat, driver claims a S$350 repair | escalate_to_human | - | provisional charge_upheld |
| PD-04 | Mess photo taken before the trip | full_refund | S$110.00 | driver pays, driver warning, fraud review |
| PD-05 | Driver-filed claim with a reused photo | no_action | - | driver warning, fraud review |
| PD-06 | AI-generated vomit photo | full_refund | S$200.00 | driver pays, driver warning, fraud review |
| PD-07 | Claim filed after 48 hours, with an instruction to the AI | no_action | - | injection flagged |
| PD-08 | Driver cleaned the crumbs himself | no_action | - | - |
| PD-09 | Paint stain claim with complete evidence | charge_upheld | - | rider charged S$95.00 |
| PD-10 | Pet fur charged as pet bodily fluids | full_refund | S$120.00 | driver pays |
| PD-11 | Mess photo taken after the driver's next trip started | full_refund | S$150.00 | driver pays |
| PD-12 | Vomit claim with full evidence, rider denies being sick (Malay) | charge_upheld | - | - |

## New test cases: safety incidents (12)

| Case | Title | Expected | Refund | Other fields |
|---|---|---|---|---|
| SF-01 | Speeding at 113 and 117 km/h on a 90 km/h road | full_refund | S$18.34 | driver pays, driver warning, safety referral, injection flagged |
| SF-02 | Rider reports speeding, GPS stays under the limit | no_action | - | - |
| SF-03 | Driver insults the rider in chat | full_refund | S$11.27 | driver pays, driver warning, safety referral |
| SF-04 | Driver's remark about the rider's religion in chat | full_refund | S$24.49 | driver pays, driver warning, safety referral |
| SF-05 | Driver threatens the rider over a rating | escalate_to_human | - | safety referral, provisional full_refund |
| SF-06 | Driver reports a threat in the car and ends the trip | escalate_to_human | - | safety referral, provisional charge_upheld |
| SF-07 | Rider pressed SOS during the trip | escalate_to_human | - | safety referral, provisional full_refund |
| SF-08 | Driver behaved inappropriately, nothing on record | escalate_to_human | - | safety referral, provisional full_refund |
| SF-09 | Rider abuses the driver, driver ends the trip | charge_upheld | - | rider warning, safety referral |
| SF-10 | Driver ended the trip with no reason, rider left on the roadside | full_refund | S$7.83 | driver pays, driver warning, safety referral |
| SF-11 | Driver insults the rider in chat (Mandarin) | full_refund | S$11.27 | driver pays, driver warning, safety referral |
| SF-12 | Rider with a dispute pattern reports speeding, GPS under the limit | no_action | - | fraud review |

Fares in the safety refunds are the fare charged on that trip (`fare_breakdown.total`).

## New past rulings (12)

| Ruling | Outcome | Refund | Rules |
|---|---|---|---|
| PREC-PD-01 | charge_upheld | - | PD-1, PD-3, PD-4 |
| PREC-PD-02 | partial_refund | S$60.00 | PD-4, PD-8, G-6 |
| PREC-PD-03 | no_action | - | PD-3 |
| PREC-PD-04 | full_refund | S$120.00 | PD-7, PD-8, G-7, G-10 |
| PREC-PD-05 | no_action | - | PD-2 |
| PREC-PD-06 | partial_refund | S$30.00 | PD-4, PD-8, G-9 |
| PREC-SF-01 | no_action | - | SF-2, SF-6 |
| PREC-SF-02 | full_refund | S$14.86 | SF-3, G-6, G-7 |
| PREC-SF-03 | charge_upheld | - | SF-3, G-7 |
| PREC-SF-04 | escalate_to_human | - | SF-1, G-4 |
| PREC-SF-05 | no_action | - | SF-6, G-1 |
| PREC-SF-06 | full_refund | S$20.36 | SF-2, G-6, G-7 |

They teach different points from the tests:
- false evidence through another car's plate
- an incomplete receipt
- cleaning two days late
- Ryde's conflicting pet-mess cap
- speeding that is not dangerous
- a single ping more than 40 km/h over
- rider abuse reported by the driver
- physical contact
- a report the records contradict

## Policy v0.4

- **Part PD (new):** PD-1 to PD-9. Mostly Sourced from Ryde's cleaning-fee pages (S19 to S21): who pays, 48-hour claim, 24-hour cleaning, photo of the plate, Singapore-registered receipt, caps S$40/S$120/S$120/S$200, pet fur not claimable. Assumed: when a photo counts (PD-6), false evidence (PD-7), who pays a refund (PD-8). Repairs are a policy gap (PD-9).
- **Part SF (new):** SF-1 to SF-6. Mostly Assumed:
  - threats, physical contact, sexual misconduct, SOS and refused requests to leave always go to a human (SF-1)
  - dangerous driving over 20 km/h on 2 consecutive pings or over 40 km/h once, benchmarked on Singapore's speeding tiers (SF-2)
  - abuse or discrimination in chat (SF-3)
  - trip ended early (SF-4, Sourced S16)
  - reports no record can check escalate (SF-5)
  - reporters are never warned (SF-6)
- **Changed for the new parts:**
  - G-4: safety now points at SF-1 and SF-5, and repairs are a gap.
  - G-6: `rider_charge_amount`; the S$4.50 limit applies to fees only.
  - G-7 and the new G-7b: rider warnings.
  - G-10: (g) false damage evidence, (h) a contradicted safety report with a dispute pattern.
  - Part B: how to read `null`.
  - The outcome table.
- **Clarifications after the blind review:** see `VERIFICATION.md`.
- **Sources:** `ryde_sources.md` adds S19 to S22 and the public benchmarks B1 to B3. It also records a fourth Ryde contradiction: S21 says pet mess S$150 and vomit $140, while S19 and S20 say S$120 and S$200. The policy follows S19 and S20.

## Agents

- `agents/` now holds the instructions for the Judge and both advocates and the full prompts (instructions plus policy, rebuilt on every build).
- The Judge's instructions cover Parts PD and SF and output the 19 fields.
- `agents/judge_output_sample.json` is a sample of the Judge's JSON.

## Checks added

- **Schema check** on every case.
- **Ruling field check** on every key entry and past ruling.
- **ADP slice-size check:** every policy section under 4,800 characters, every past ruling under 1,500.
- **Validator derivations** for Parts PD and SF.
- **30 new self-tests** for the new rules and checks (76 in total, up from 46).
- **Realism checks** for the new cases: photo and receipt timing, speeds against the distance between pings, nothing filed after 12 Oct 2026.
