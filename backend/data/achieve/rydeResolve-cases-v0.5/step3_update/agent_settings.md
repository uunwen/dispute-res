# RydeResolve agent settings (v0.5)

Keep this file. If the ADP app is ever lost, these settings plus the three prompt files rebuild the agents.

| Setting | Rider Advocate | Driver Advocate | Judge |
|---|---|---|---|
| Name | Rider Advocate | Driver Advocate | Judge |
| Model | DeepSeek-V4-Flash | DeepSeek-V4-Flash | DeepSeek-V4-Pro |
| Prompt | prompts/rider_advocate.md | prompts/driver_advocate.md | prompts/judge.md |
| Transfer description | Argues the rider's side of a Ryde dispute and returns a JSON brief. | Argues the driver's side of a Ryde dispute and returns a JSON brief. | Decides a Ryde dispute from the case, the evidence and both briefs, and returns a JSON ruling. |
| Tools | none (policy is inside the prompt; past rulings come from a workflow retrieval node in step 4) | none | none |
| Clarifying questions | Off | Off | Off |
| Thinking mode | Off | Off | On |
| Context turns | lowest allowed (0 or 1) | same | same |
| JSON output format | On, if offered | On, if offered | On, if offered |
| Temperature, if offered | 0.3 | 0.3 | 0.1 |

Why:
- Flash for the advocates keeps a 66-case run cheap. Pro for the Judge because the ruling is what gets scored.
- Clarifying questions off: in a batch run nobody is there to answer, so an agent that stops to ask breaks the run.
- Context turns at the minimum: each dispute must be decided on its own. Old cases leaking into a new one is a fairness bug.
- Thinking on for the Judge only: it has to apply rules in order and do arithmetic checks. We measure the cost on the first full run and turn it off if it is too expensive.

Smoke-test inputs are in `test_inputs/` (past rulings, not test cases, so they don't contaminate the score). Paste a file's whole content into `case_json` in Debug. Expected rulings are in `test_inputs/expected.json`:
- PREC-NS-03: full_refund, 6.61, payer driver, driver warning true, nothing else.
- PREC-RD-01: partial_refund, 5.38, payer driver, driver warning true, nothing else.
- PREC-PD-02: partial_refund, 60.00, payer driver, no warning.
- PREC-SF-06: full_refund, 20.36, payer driver, driver warning true, safety_referral true.
