# ADP update for v0.5 (about 30 minutes)

All files are in `step3_update/`. The workflow you built (Start, Rider_Advocate, Driver_Advocate, Judge, End) stays as it is.

## A. Knowledge base

1. Delete these files from the knowledge base: `ryde_dispute_policy.md`, `precedents_no_show.md`, `precedents_route_deviation.md`.
2. Import the 5 files in `step3_update/knowledge_base/`. Use the same splitting settings as before:

| File | Custom identifier | Max slice length | Slices to expect |
|---|---|---|---|
| `ryde_dispute_policy.md` | `##` | 4800 | 13 |
| `precedents_no_show.md` | `###` | 1500 | 16 |
| `precedents_route_deviation.md` | `###` | 1500 | 15 |
| `precedents_property_damage.md` (new) | `###` | 1500 | 7 |
| `precedents_safety_incident.md` (new) | `###` | 1500 | 7 |

In each file the first slice is the short intro, so each precedent file has one more slice than it has rulings.

3. Spot-check the slices:
   - In the policy, the slices `## Part PD ...` and `## Part SF ...` should each start at a heading.
   - In each precedent file, slice 2 should start with its first `### PREC-...`.

## B. Prompts

For each agent, select all in the Prompt box, delete, and paste the matching file from `step3_update/prompts/`. Do not click One-click optimization.

| Agent | File | Settings-page counter | Workflow-node counter |
|---|---|---|---|
| Judge | `judge.md` | about 43,376 | about 43,282 |
| Rider Advocate | `rider_advocate.md` | about 37,241 | about 37,147 |
| Driver Advocate | `driver_advocate.md` | about 37,252 | about 37,158 |

The workflow node shows 94 fewer because it skips blank lines. The end of each prompt is the Outcomes table.

## C. Judge JSON output (Advanced Settings, Output Format JSON, Set JSON)

Add these three fields. Keep the existing ones.

| Name | Description | Type | Required |
|---|---|---|---|
| `rider_charge_amount` | SGD newly charged to the rider by this ruling (approved cleaning claim, upheld driver fee claim). 0 otherwise. | float | Yes |
| `rider_warning` | True only if the records show the rider abused, threatened or discriminated against the driver (G-7b). | bool | Yes |
| `safety_referral` | Referred to Ryde's safety team (SF-1 to SF-4, or an escalation over a safety concern). | bool | Yes |

Then check that the full list has all 19 fields from `schema/ruling_fields.json`:

```
id, outcome, refund_amount, payer, rider_charge_amount, driver_warning, rider_warning,
driver_goodwill_paid_by_ryde, escalate, provisional_outcome, safety_referral, security_flag,
fraud_flag, confidence, rules_cited, precedents_used, reasoning, rider_explanation, driver_explanation
```

`agents/judge_output_sample.json` is a complete example, if ADP's Import JSON is easier.

## D. Smoke tests (Debug)

Paste the whole of a file from `step3_update/test_inputs/` into `case_json` and run.

| Input | Expected |
|---|---|
| PREC-NS-03 | full_refund, 6.61, driver pays, driver warning |
| PREC-RD-01 | partial_refund, 5.38, driver pays, driver warning |
| PREC-PD-02 | partial_refund, 60.00, driver pays, no warning |
| PREC-SF-06 | full_refund, 20.36, driver pays, driver warning, safety_referral true |

`expected.json` has every field. These are past rulings, so the knowledge base may retrieve the matching precedent. They test that the pipeline runs, not how well the agents decide.
