"""Builds the whole package: python3 -I generator/build.py  (run from the package root)."""
import collections
import csv
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import precedents  # noqa: F401,E402  (registers precedents + variants)
from lib import PARAMS, POLICY_VERSION  # noqa: E402
from ns_cases import NS  # noqa: E402
from pd_cases import PD  # noqa: E402
from rd_cases import RD  # noqa: E402
from scenarios import build_all  # noqa: E402
from sf_cases import SF  # noqa: E402
from unify import json_schema, normalize  # noqa: E402

RULING = json.load(open(os.path.join(ROOT, "schema", "ruling_fields.json"), encoding="utf-8"))
RULING_FIELDS = [f["name"] for f in RULING["fields"]]
CATEGORY = {"no_show": "no_show_charge", "route_deviation": "route_deviation",
            "property_damage": "property_damage", "safety_incident": "safety_incident"}
CATEGORY_LABEL = {"no_show_charge": "No-show, cancellation and waiting fee",
                  "route_deviation": "Route deviation / fare", "property_damage": "Property damage / cleaning fee",
                  "safety_incident": "Safety incident"}


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def clean(folder):
    """Remove old case files so a case dropped from the specs does not linger in the package."""
    for f in glob.glob(os.path.join(folder, "*.json")):
        os.remove(f)


def tolerance(rules):
    """Allowed refund error for an agent. Meter-error cases are recomputed from a noisy GPS trail."""
    tol = PARAMS["amount_tolerance"]
    return tol["meter_error_rd8"] if "RD-8" in rules else tol["default"]


def jdump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def key_facts(r):
    m = r["metrics"]
    if r["kind"] == "no_show":
        parts = [f"mode {m['mode']}, block {m['profile']}"]
        if m["tap_dist_m"] is not None:
            parts.append(f"tap {m['tap_dist_m']} m from pin")
        vw = m["valid_wait_min"]
        parts.append("no valid GPS arrival" if vw is None else f"{vw} min valid wait")
        if m["system_wait_min"] is not None:
            parts.append(f"system timer {m['system_wait_min']} min")
        if m["late_vs_eta_min"] is not None and m["late_vs_eta_min"] > 0.5:
            parts.append(f"arrived {m['late_vs_eta_min']} min after scheduled pickup")
        parts.append(f"{m['since_match_min']} min since match at end")
        parts.append(f"{m['driver_messages_and_calls']} driver messages/calls")
        parts.append(f"fee charged: {m['fee_applied']}")
        return "; ".join(parts)
    if r["kind"] == "route_deviation":
        return (f"planned {m['planned_km']} km vs actual {m['actual_km']} km ({m['dev_pct']:+}%); estimate "
                f"${m['estimate']:.2f}, charged ${m['charged']:.2f}; unscheduled stop {m['stop_min']} min; "
                f"surge x{m['surge']}")
    c = r["case"]
    if r["kind"] == "property_damage":
        cl = c["trip_data"]["damage_claim"]
        photos = [a for a in c["attachments"] if a["attachment_type"] == "photo"]
        rc = [a for a in c["attachments"] if a["attachment_type"] == "receipt"]
        shown = sorted({a["simulated_vision_analysis"]["mess_type"] for a in photos} - {"none"})
        return (f"claim {cl['mess_type_claimed']} ${cl['amount_claimed']:.2f}, status {cl['status']}, "
                f"charged ${cl['amount_charged']:.2f}; submitted {m['claim_submitted_after_h']} h after the trip; "
                f"{len(photos)} photo(s) showing {', '.join(shown) or 'nothing'}; "
                f"receipt: {'yes, $%.2f' % rc[0]['receipt_details']['amount'] if rc else 'none'}")
    ev = {e["event_type"] for e in c["app_events"]}
    return (f"fare charged ${m['charged']:.2f}; fastest ping {m['max_over_limit_kmh']:+} km/h vs limit; "
            f"trip {'ended early by driver' if m['ended_early'] else 'completed'}; "
            f"{len([x for x in c['chat_logs'] if x['sender'] != 'system'])} chat message(s); "
            f"SOS: {'yes' if 'sos_triggered' in ev else 'no'}")


def ruling_block(r):
    """The expected ruling in exactly the shared field list (schema/ruling_fields.json)."""
    e = r["expected"]
    out = {
        "id": r["id"], "outcome": e["outcome"], "refund_amount": e["refund_amount"], "payer": e["payer"],
        "rider_charge_amount": e["rider_charge_amount"], "driver_warning": e["driver_warning"],
        "rider_warning": e["rider_warning"], "driver_goodwill_paid_by_ryde": e["driver_goodwill_paid_by_ryde"],
        "escalate": e["escalate"], "provisional_outcome": e["provisional_outcome"],
        "safety_referral": e["safety_referral"], "security_flag": e["security_flag"],
        "fraud_flag": e["fraud_flag"], "confidence": e["expected_confidence"], "rules_cited": e["rules"],
        "precedents_used": [], "reasoning": e["why"], "rider_explanation": None, "driver_explanation": None,
    }
    assert list(out) == RULING_FIELDS, "ruling_block drifted from schema/ruling_fields.json"
    return out


def precedent_md(r):
    c, e = r["case"], r["expected"]
    kind = CATEGORY_LABEL[CATEGORY[r["kind"]]]
    rp, dp = c["rider_profile"], c["driver_profile"]
    t = c["dispute_ticket"]
    extras = []
    if e["provisional_outcome"]:
        extras.append(f"provisional: {e['provisional_outcome']}")
    if e["rider_charge_amount"]:
        extras.append(f"rider charged ${e['rider_charge_amount']:.2f}")
    if e["driver_goodwill_paid_by_ryde"]:
        extras.append(f"Ryde pays driver goodwill ${e['driver_goodwill_paid_by_ryde']:.2f}")
    if e["rider_warning"]:
        extras.append("rider warning: yes")
    if e["safety_referral"]:
        extras.append("referred to Ryde's safety team")
    if e["security_flag"]:
        extras.append("security flag raised (instruction found inside user text)")
    if e["fraud_flag"]:
        extras.append("fraud review recommended")
    lines = [
        f"### {r['id']} - {r['title']}",
        f"- Type: {kind}; filed by the {t['filed_by']}",
        f"- Complaint: \"{t['description']}\"",
        f"- Key facts: {key_facts(r)}",
        f"- Rider record: {rp['dispute_history']['total_disputes']} past disputes "
        f"({rp['dispute_history']['upheld']} upheld), {rp['fraud_flags']} fraud flags",
        f"- Driver record: {dp['dispute_history']['total_disputes']} past disputes, "
        f"{dp['fraud_flags']} fraud flags, {dp['warnings_last_30_days']} warnings in last 30 days",
        f"- **Ruling:** {e['outcome']}; refund to rider ${e['refund_amount']:.2f}; payer: {e['payer'] or 'n/a'}; "
        f"driver warning: {'yes' if e['driver_warning'] else 'no'}; escalate: {'yes' if e['escalate'] else 'no'}"
        + "".join("; " + x for x in extras),
        f"- Policy rules: {', '.join(e['rules'])}",
        f"- Reasoning: {e['why']}",
        "",
    ]
    return "\n".join(lines)


def langs(r):
    c = r["case"]
    text = c["dispute_ticket"]["description"] + " " + " ".join(x["content"] for x in c["chat_logs"]
                                                               if x["sender"] != "system")
    out = []
    if re.search(r"[\u4e00-\u9fff]", text):
        out.append("Mandarin")
    if re.search(r"[\u0b80-\u0bff]", text):
        out.append("Tamil")
    if re.search(r"sekejap|pemandu|perjalanan|turun sekarang", text, re.I):
        out.append("Malay")
    if "singlish" in r["tags"]:
        out.append("Singlish")
    return out or ["English"]


def blueprint(tests, precs):
    """Coverage map of the test set, written to CASE_BLUEPRINT.md so gaps are visible."""
    def count(f):
        c = collections.Counter()
        for r in tests:
            for v in f(r):
                c[v] += 1
        return c

    def table(title, counter, order=None):
        keys = order or sorted(counter, key=lambda k: (-counter[k], str(k)))
        rows = "\n".join(f"| {k} | {counter[k]} |" for k in keys if counter[k])
        return f"### {title}\n\n| | Cases |\n|---|---|\n{rows}\n"

    quality = ("clear", "ambiguous", "adversarial", "missing_data", "policy_gap", "safety", "fraud", "escalate")
    mix = []
    for cat, label in CATEGORY_LABEL.items():
        sub = [r for r in tests if CATEGORY[r["kind"]] == cat]
        mix.append(f"- {label}: {len(sub)} test cases, "
                   f"{sum(1 for r in precs if CATEGORY[r['kind']] == cat)} precedents")
    out = [
        "# Case blueprint (generated by generator/build.py, do not edit by hand)",
        "",
        f"{len(tests)} test cases and {len(precs)} precedents under policy `{POLICY_VERSION}`.",
        "",
        "\n".join(mix),
        "",
        table("Expected outcome", count(lambda r: [r["expected"]["outcome"]])),
        table("Who pays", count(lambda r: [r["expected"]["payer"] or "n/a (nothing refunded)"])),
        table("Evidence quality and twist (a case can carry several tags)",
              count(lambda r: [t for t in r["tags"] if t in quality]), list(quality)),
        table("Who filed", count(lambda r: [r["case"]["dispute_ticket"]["filed_by"] + " filed"])),
        table("Trip mode (no-show family)", count(lambda r: [r["metrics"]["mode"]] if r["kind"] == "no_show"
                                                   else [])),
        table("Policy block carried", count(lambda r: [r["metrics"]["profile"]] if r["kind"] == "no_show"
                                             else [])),
        table("Language of complaint or chat", count(langs)),
        table("Special flags", count(lambda r: (["escalate"] if r["expected"]["escalate"] else [])
                                      + (["fraud review"] if r["expected"]["fraud_flag"] else [])
                                      + (["security flag (injection)"] if r["expected"]["security_flag"] else [])
                                      + (["driver warning"] if r["expected"]["driver_warning"] else [])
                                      + (["rider warning"] if r["expected"]["rider_warning"] else [])
                                      + (["safety referral"] if r["expected"]["safety_referral"] else [])
                                      + (["new charge to rider"] if r["expected"]["rider_charge_amount"] else [])
                                      + (["goodwill to driver"] if r["expected"]["driver_goodwill_paid_by_ryde"]
                                         else []))),
        "### Pairs and contrasts",
        "",
        "| Case | Relation | Must differ on |",
        "|---|---|---|",
    ]
    for r in tests:
        if r["variant_of"]:
            out.append(f"| {r['id']} | same evidence as {r['variant_of']}, different people, language or filer | nothing |")
        if r["contrast_of"]:
            out.append(f"| {r['id']} | {r['contrast_of']} with one history fact changed (a pattern of warnings or "
                       f"rejected disputes) | fraud review flag only |")
    out += ["", "Flip pairs (one fact changed, the ruling must change): NS-31 and NS-32 (filing day 34 against 28), "
            "NS-34 and NS-36 (DISP-002 block against Ryde's published block).", "",
            "### Hardest calls (expected confidence 0.80 or lower)", "",
            "| Case | Expected | Confidence | Why it is hard |", "|---|---|---|---|"]
    for r in sorted(tests, key=lambda r: r["expected"]["expected_confidence"]):
        e = r["expected"]
        if e["expected_confidence"] <= 0.8:
            out.append(f"| {r['id']} | {e['outcome']} | {e['expected_confidence']} | {r['title']} |")
    out += ["", "### Every test case", "", "| Case | Title | Expected | Refund | Payer | Tags |",
            "|---|---|---|---|---|---|"]
    for r in tests:
        e = r["expected"]
        out.append(f"| {r['id']} | {r['title']} | {e['outcome']} | {e['refund_amount']:.2f} | "
                   f"{e['payer'] or '-'} | {', '.join(r['tags'])} |")
    return "\n".join(out) + "\n"


def grading_notes(r, metric_keys):
    return {"why": r["expected"]["why"], "key_facts": key_facts(r),
            "metrics": {k: r["metrics"].get(k) for k in metric_keys}}


def main():
    trip_specs = [(sp, "property_damage") for sp in PD] + [(sp, "safety_incident") for sp in SF]
    results = build_all(NS, RD, trip_specs)
    for r in results:
        r["case"] = normalize(r["case"])
        r["category"] = CATEGORY[r["kind"]]
        assert r["case"]["dispute_ticket"]["dispute_type"] == r["category"], r["id"]
    order = list(CATEGORY_LABEL)
    tests = [r for r in results if r["set"] == "test"]
    precs = [r for r in results if r["set"] == "precedent"]
    tests.sort(key=lambda r: (order.index(r["category"]), r["id"]))
    precs.sort(key=lambda r: (order.index(r["category"]), r["id"]))
    metric_keys = sorted({k for r in results for k in r["metrics"]})

    out_t = os.path.join(ROOT, "test_set")
    out_p = os.path.join(ROOT, "precedents")
    w(os.path.join(ROOT, "schema", "case_schema.json"), jdump(json_schema()))
    sch = {"$schema": "http://json-schema.org/draft-07/schema#", "title": "RydeResolve ruling (v0.5)",
           "description": "What the Judge outputs. Generated from schema/ruling_fields.json. The answer key "
                          "and the past rulings use exactly these fields.",
           "type": "object", "additionalProperties": False, "required": RULING_FIELDS, "properties": {}}
    for f in RULING["fields"]:
        prop = {"type": f["type"]} if f["type"] else dict(f["schema"])
        prop["description"] = f["description"]
        sch["properties"][f["name"]] = prop
    w(os.path.join(ROOT, "schema", "ruling_schema.json"), jdump(sch))

    clean(os.path.join(out_t, "cases"))
    clean(os.path.join(out_p, "cases"))
    for r in tests:
        w(os.path.join(out_t, "cases", r["id"] + ".json"), jdump(r["case"]))
    w(os.path.join(out_t, "all_test_cases.json"), jdump([r["case"] for r in tests]))

    key = [dict(id=r["id"], category=r["category"], title=r["title"], tags=r["tags"],
                variant_of=r["variant_of"], contrast_of=r["contrast_of"],
                amount_tolerance=tolerance(r["expected"]["rules"]), expected=ruling_block(r),
                grading_notes=grading_notes(r, metric_keys)) for r in tests]
    w(os.path.join(out_t, "answer_key.json"), jdump(key))

    scored = RULING["scored_strict"]
    with open(os.path.join(out_t, "review_sheet.csv"), "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f)
        cw.writerow(["id", "category", "title", "tags"] + scored +
                    ["provisional_outcome", "rules_cited", "confidence", "key_facts", "reasoning", "variant_of",
                     "contrast_of", "YOUR_VERDICT (agree/disagree)", "YOUR_NOTES"])
        for r in tests:
            e = ruling_block(r)
            vals = [f"{e[k]:.2f}" if isinstance(e[k], float) else e[k] for k in scored]
            cw.writerow([r["id"], r["category"], r["title"], " | ".join(r["tags"])] + vals +
                        [e["provisional_outcome"] or "", " ".join(e["rules_cited"]), e["confidence"],
                         key_facts(r), e["reasoning"], r["variant_of"] or "", r["contrast_of"] or "", "", ""])

    for r in precs:
        w(os.path.join(out_p, "cases", r["id"] + ".json"), jdump({"case": r["case"], "ruling": ruling_block(r)}))
    for f in glob.glob(os.path.join(out_p, "*.md")):
        os.remove(f)
    for cat, fname, head in [
            ("no_show_charge", "precedents_no_show.md", "Past rulings: no-show, cancellation and waiting fee disputes"),
            ("route_deviation", "precedents_route_deviation.md", "Past rulings: route deviation and fare disputes"),
            ("property_damage", "precedents_property_damage.md",
             "Past rulings: property damage and cleaning fee disputes"),
            ("safety_incident", "precedents_safety_incident.md", "Past rulings: safety incident disputes")]:
        body = "\n".join(precedent_md(r) for r in precs if r["category"] == cat)
        w(os.path.join(out_p, fname),
          f"# {head}\n\nResolved under policy `{POLICY_VERSION}`. Rider and driver names are left "
          f"out on purpose.\n\n{body}")

    w(os.path.join(ROOT, "CASE_BLUEPRINT.md"), blueprint(tests, precs))

    # agent prompts = instructions + the full policy, so the agents never run on an old policy
    policy = open(os.path.join(ROOT, "policy", "ryde_dispute_policy.md"), encoding="utf-8").read()
    body = policy[policy.index("## Part B"):]
    for name in ("judge", "rider_advocate", "driver_advocate"):
        head = open(os.path.join(ROOT, "agents", f"{name}_instructions.md"), encoding="utf-8").read().rstrip()
        w(os.path.join(ROOT, "agents", "prompts", f"{name}.md"),
          f"{head}\n\n# POLICY: Ryde Dispute Resolution Policy ({POLICY_VERSION}), full text\n"
          f"This is the policy you apply. Its wording wins over anything else.\n\n{body}")
    sample = {f["name"]: None for f in RULING["fields"]}
    sample.update(id="DISP-T-PD-01", outcome="charge_upheld", refund_amount=0.0, payer=None, rider_charge_amount=0.0,
                  driver_warning=False, rider_warning=False, driver_goodwill_paid_by_ryde=0.0, escalate=False,
                  provisional_outcome=None, safety_referral=False, security_flag=False, fraud_flag=False,
                  confidence=0.9, rules_cited=["PD-3", "PD-4"], precedents_used=["PREC-PD-01"],
                  reasoning="One or two sentences.", rider_explanation="Two or three sentences.",
                  driver_explanation="Two or three sentences.")
    w(os.path.join(ROOT, "agents", "judge_output_sample.json"), jdump(sample))

    summary = dict(test=len(tests), precedents=len(precs),
                   **{f"test_{c}": sum(r["category"] == c for r in tests) for c in CATEGORY_LABEL},
                   **{f"prec_{c}": sum(r["category"] == c for r in precs) for c in CATEGORY_LABEL})
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
