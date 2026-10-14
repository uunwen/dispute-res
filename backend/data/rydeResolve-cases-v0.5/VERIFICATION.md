# Verification (v0.5, 12 Oct 2026)

What was checked, what it proves, and what it does not.

## Results

| Check | Result |
|---|---|
| Every ruling re-derived from the raw case data by `tools/validate.py` (code written separately from the generator) | 134 of 134 match the key: no-show 59/59, route 39/39, property damage 18/18, safety 18/18 |
| Every case against `schema/case_schema.json` (all keys required, no extras, types fixed) | 134 of 134 pass; all 134 files have the identical key tree |
| Every answer key entry and past ruling against `schema/ruling_fields.json` | 93 + 41 pass, same 19 fields in the same order |
| Self-test: the checkers catch broken evidence, broken format and scoring errors | 76 of 76 (was 46) |
| Realism checks (GPS on land, speeds matching distances between pings, photo, receipt and claim timing, receipt arithmetic, nothing filed after 12 Oct 2026) | 0 of 134 cases with issues |
| ADP slice sizes (policy sections under 4,800 characters, past rulings under 1,500) | All pass |
| Existing 69 test cases compared with v0.4 | Content identical. Ruling changes only where listed in `CHANGELOG_v0.5.md` (new fields on 6 cases) |
| Blind re-ruling of the 36 new cases (12 damage tests, 12 safety tests, 12 new past rulings) by three independent reviewers, from the policy and the case only, with no key | 36 of 36 agree with the key on every scored field. PD-03 matched once a free-text note the reviewer wrote into the provisional outcome field is set aside |

The no-show and route cases were blind-checked in the v0.4 audit (89 of 95, then 29 of 29 and 39 of 39 after fixes). Their content is unchanged.

## What the blind reviewers flagged, and what was done

**Fixed in the cases:**
- **SF-03, SF-04, SF-11 and PREC-SF-02:** the driver complained about waiting in the chat before the app showed the driver had arrived. The arrival is now earlier, so the chat follows it.
- **PD-04, PD-11 and PREC-PD-04:** a photo taken hours from the trip, or during the next trip, carried a location at the drop-off point. Photos now carry a location only when taken at the car within 30 minutes of the trip ending.
- **PD-03:** the repair quotation was marked as professional cleaning. It now says it is not.
- **SF-12:** the rider's dispute counts did not add up (6 total, 1 upheld, 4 rejected). Now 5, 1 and 4.
- **PREC-SF-04:** the complaint mentioned a toll the trip did not have. Reworded.
- **PREC-SF-06:** a named expressway had an unrealistic limit. The complaint now refers to a main road.

**Clarified in the policy** (each was a place where two reasonable readings existed; none changes a ruling):
- **G-6:** the S$4.50 limit on what a driver repays is for cancellation and waiting fees only. For fare and cleaning refunds, "driver pays" means the refund comes out of the driver's earnings.
- **SF-1:** SF-1 comes before every other safety rule. A reported threat goes to a human even when SF-4 or SF-6 would otherwise decide.
- **SF-3:** examples of insults ("idiot", "stupid", "go to hell", "shut up").
- **SF-4 and SF-6:** a justified early end keeps the charge (`charge_upheld`). A report the records contradict, including speeding of 20 km/h or less over the limit, is `no_action`.
- **PD-8:** when the driver claimed a costlier type of mess than the photos show, the driver pays, even if Ryde's process also let the charge through.

**Left as they are (deliberate):**
- **PD-01 and PD-12:** the rider denies being sick, with no other record. The policy treats the photo analysis as a system record (G-1), so the fee stands.
- **PD-10 and PD-02:** a mislabelled claim gets no warning. Only false evidence (PD-7) earns one.
- **PD-03:** a repair claim is approved provisionally on a quotation. PD-9 sends it to a human, who decides the amount.
- **SF-05:** a threat made after the trip still gets a provisional fare refund, following SF-1.

The reviewers ruled under the policy as it stood before these clarifications. The clarifications only spell out readings the key already used.

## What this does not prove

- **The reviewers are not fully independent of the author.** They are Claude sub-agents, the same model family that wrote the cases. Agreement shows the key follows from the policy as written. It does not show the policy matches how Ryde really decides.
- **Ryde does not publish most of the safety rules (Part SF).** Ryde publishes no rules for deciding safety incidents. The speed thresholds follow Singapore's speeding tiers; the rest is our design.
- **Chat language is checked by keyword.** Whether a chat message is abuse or a threat is checked by keyword lists in the validator and by the reviewers' reading. Borderline language would need a human, which is why the policy escalates threats and anything no record can check.
- **The photos are simulated.** Property damage photos are simulated records, not images.
