# RydeResolve case set v0.5

**What's here:**
- 93 test cases and 41 past rulings, covering all four dispute types in the hackathon brief.
- One case format and one ruling format.
- A policy (v0.4) built on Ryde's published rules.
- Scripts that build, check and score everything.

**Changes since v0.4:** see `CHANGELOG_v0.5.md`. What was checked and what it proves is in `VERIFICATION.md`.

## The four dispute types

| Type (`dispute_type`) | Test cases | Past rulings | Policy part |
|---|---|---|---|
| No-show, cancellation and waiting fee (`no_show_charge`) | 44 | 15 | NS |
| Route deviation and fare (`route_deviation`) | 25 | 14 | RD |
| Property damage and cleaning fee (`property_damage`) | 12 | 6 | PD |
| Safety incident (`safety_incident`) | 12 | 6 | SF |

**Expected outcomes across the 93 test cases:**

| Outcome | Cases |
|---|---|
| full refund | 29 |
| charge upheld | 18 |
| no action | 18 |
| partial refund | 16 |
| escalate to a human | 12 |

**Who filed:** 79 rider-filed, 14 driver-filed.

**Flags in the expected rulings:**
- 28 driver warnings
- 13 safety referrals
- 10 fraud reviews
- 4 prompt-injection cases

The full coverage map is in `CASE_BLUEPRINT.md`.

## One format for everyone (read `FORMAT_NOTE.md` first)

**Cases:**
- Every case file has the same 13 top-level keys and the same keys at every level below.
- A section a dispute type does not use is `null` or `[]`.
- Definition: `schema/case_schema.json`. Explanation: `schema/case_format.md`.

**Rulings:**
- The Judge's output, the answer key's `expected`, the past rulings and the scorer all use the same 19 fields from `schema/ruling_fields.json`.
- Grader-only notes are in each key entry's `grading_notes`.

## What is in here

| Folder or file | What it is | Who sees it |
|---|---|---|
| `policy/ryde_dispute_policy.md` | The policy, rule IDs G, NS, RD, PD, SF, each tagged Sourced, Benchmark or Assumed | Agents (ADP knowledge base, and inside the prompts) |
| `policy/ryde_sources.md` | The Ryde pages (S1 to S22) and public references (B1 to B3) behind the Sourced and Benchmark rules | Team |
| `policy/params.json` | Every number the rules use | Generator and validator |
| `precedents/*.md` | 41 past rulings in four files, one per dispute type | Agents (ADP knowledge base) |
| `precedents/cases/` | The same past rulings as JSON (case plus ruling) | Agents (examples), team |
| `test_set/cases/`, `test_set/all_test_cases.json` | 93 cases with no answers in them | Agents, one at a time, at test time only |
| `test_set/answer_key.json` | Expected ruling per case | **Never the agents** |
| `test_set/review_sheet.csv` | The key as a sheet to mark agree or disagree | Team |
| `agents/` | The three agents' instructions, the full prompts (instructions plus policy, rebuilt on every build), and a sample of the Judge's JSON output | ADP |
| `schema/` | Case schema, ruling field list and schema, format guide, DISP-002 field list | Everyone |
| `tools/validate.py`, `tools/selftest.py`, `tools/score.py` | Checker, check of the checker, scorer | Team |
| `generator/` | Code that builds it all | Team |
| `step3_update/`, `REUPLOAD_CHECKLIST.md` | Files to upload to ADP for this version and the steps | Shivam |

## Before anyone uses it

1. **Keep the key away from the agents.** Never upload `answer_key.json`, `review_sheet.csv` or the test cases to ADP. Upload only the policy and the four precedent markdown files.
2. **Review the key.** Open `test_set/review_sheet.csv` and mark agree or disagree. Start with the cases where the key is least sure (listed in `CASE_BLUEPRINT.md` under "Hardest calls").
3. **Images.** Property damage photos are simulated: each photo record carries what an image model would report (`simulated_vision_analysis`), and there is no image file. This keeps the core agents text-only, as the brief requires. Real image analysis is a stretch goal.

## Running the scripts (from this folder)

```
python3 -I generator/build.py            # regenerate everything, including the agent prompts
python3 -I tools/validate.py             # check every case and the key against the raw data and the schemas
python3 -I tools/selftest.py             # check the checkers
python3 -I tools/score.py results.json   # score your agents' rulings (a JSON list in the ruling format)
```

`validate.py` re-derives every ruling from the raw case data with separately written code and fails on any of these:
- a mismatch with the key
- a case that breaks the schema
- a key or past ruling whose fields differ from the shared list
- an answer leaking into a case
- a person or pickup venue shared between the test set and the past rulings
- a policy number that disagrees with `params.json`
- a policy section or past ruling too long for one ADP knowledge slice

## Known limits

- **The key was never checked against a real Ryde ruling.** The validator proves the key follows from the evidence under the rules as written, not that the rules are Ryde's. The same author wrote the key and the checker, so the blind reviews in `VERIFICATION.md` are the independent check.
- **Assumed rules.** Most of Part SF and parts of Part PD are Assumed or Benchmark, not Ryde's. Fares are internally consistent but are not real Ryde prices.
- **Safety chat judgments.** Whether a chat message counts as abuse or a threat is checked by keyword in the validator and by the blind reviewers. A real system would need human review of borderline language. That is why threats and unverifiable reports escalate.
- **Route geometry** is a few straight segments kept on land, not street-level roads.
- **Not covered:** two-issue disputes (for example a detour and a missing promo together), and real images.
