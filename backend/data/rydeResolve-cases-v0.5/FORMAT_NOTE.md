# Format note (one page)

This answers one question: can every file be read the same way? Yes.

## Cases

- **Same keys everywhere.** Every one of the 134 case files (93 tests, 41 past rulings) has the same 13 top-level keys, in the same order, and the same keys inside every object and every list item. The checker fails the build if any file differs.
- **Unused sections are empty, not missing.**
  - A section a dispute type does not use is `null` (an object) or `[]` (a list). For example a route case has `"cancellation_policy": null`, and a no-show case has `"attachments": []`.
  - Code can always do `case["fare_breakdown"]`. Check for `None` before reading inside it.
- **Same types everywhere.** A key never changes type between files. The one change from v0.4: `rider_app_location` used to be a list in some files and an object in others. It is now always `{"available": ..., "note": ..., "pings": [...]}` or `null`.
- **Where it is defined:**
  - `schema/case_schema.json`: JSON Schema draft-07, every key required, no extra keys allowed.
  - `schema/case_format.md`: the same in prose.
- **How to tell the type:** `dispute_ticket.dispute_type` is one of `no_show_charge`, `route_deviation`, `property_damage` or `safety_incident`.

## Rulings

- **One field list.** `schema/ruling_fields.json` lists the 19 ruling fields. These all use exactly those names, in that order:
  - the Judge's JSON output
  - `answer_key.json` (each entry's `expected`)
  - `precedents/cases/*.json` (each file's `ruling`)
  - `tools/score.py`
- **Fixed name clash.** v0.4 had `rules` and `why` in the key but `rules_cited` and `reasoning` in the past rulings. Now both use `rules_cited` and `reasoning`.
- **Three new fields** cover property damage and safety:
  - `rider_charge_amount`: money newly charged to the rider, for example an approved cleaning claim
  - `rider_warning`
  - `safety_referral`
- **Free text in the key.** The key fills `reasoning` with its expected reasoning. It leaves `rider_explanation` and `driver_explanation` null, because they are not scored.

## Answer key entry

```
{ "id", "category", "title", "tags", "variant_of", "contrast_of", "amount_tolerance",
  "expected": { 19 ruling fields },
  "grading_notes": { "why", "key_facts", "metrics" } }
```

`category` is the case's `dispute_type`. `grading_notes.metrics` has the same keys in every entry, with null where a number does not apply.

## Using it in code (Python)

```python
import json
case = json.load(open("test_set/cases/DISP-T-PD-01.json"))
kind = case["dispute_ticket"]["dispute_type"]
photos = [a for a in case["attachments"] if a["attachment_type"] == "photo"]
key = {k["id"]: k["expected"] for k in json.load(open("test_set/answer_key.json"))}
```

To check one of your own files against the case format, use any JSON Schema validator with `schema/case_schema.json`, or run `python3 -I tools/validate.py`.
