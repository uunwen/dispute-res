"""Scores an agent system against the answer key.

Usage (from the package root):
    python3 -I tools/score.py results.json

results.json is a list of rulings in schema/ruling_schema.json format (the field list in
schema/ruling_fields.json), one per test case id.
Nothing here calls an agent. Run your agents however you like, save their rulings, then score.

A malformed ruling (missing field, wrong type, unknown outcome) is counted as wrong and reported.
It never stops the run, so one bad output does not hide the others.

Two headline numbers:
  loose  = outcome and refund amount correct
  strict = loose, and payer, new charge to the rider, driver warning, rider warning, escalation, safety referral,
           security flag, fraud review flag and goodwill all correct
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTCOMES = {"charge_upheld", "no_action", "full_refund", "partial_refund", "escalate_to_human"}
PAYERS = {"driver", "ryde", None}
FIELDS = ("outcome", "amount", "payer", "charge", "warning", "rider_warning", "escalate", "referral", "security",
          "fraud", "goodwill")


def num(x):
    """A real number or None. Booleans are not numbers here."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x)


def check_format(r):
    problems = []
    if r.get("outcome") not in OUTCOMES:
        problems.append(f"outcome {r.get('outcome')!r} is not one of {sorted(OUTCOMES)}")
    if num(r.get("refund_amount", 0)) is None:
        problems.append(f"refund_amount {r.get('refund_amount')!r} is not a number")
    if r.get("payer") not in PAYERS:
        problems.append(f"payer {r.get('payer')!r} must be 'driver', 'ryde' or null")
    if num(r.get("rider_charge_amount", 0)) is None:
        problems.append(f"rider_charge_amount {r.get('rider_charge_amount')!r} is not a number")
    for f in ("driver_warning", "rider_warning", "escalate", "safety_referral", "security_flag", "fraud_flag"):
        if f in r and not isinstance(r[f], bool):
            problems.append(f"{f} must be true or false")
    return problems


def judge(r, k):
    """Field-by-field correctness of one ruling against one key entry."""
    e = k["expected"]
    amt = num(r.get("refund_amount", 0))
    out = {
        "outcome": r.get("outcome") == e["outcome"],
        "amount": amt is not None and abs(amt - e["refund_amount"]) <= k.get("amount_tolerance", 0.05),
        "payer": r.get("payer") == e["payer"],
        "charge": abs((num(r.get("rider_charge_amount", 0)) or 0.0) - e["rider_charge_amount"])
                  <= k.get("amount_tolerance", 0.05),
        "warning": bool(r.get("driver_warning", False)) == e["driver_warning"],
        "rider_warning": bool(r.get("rider_warning", False)) == e["rider_warning"],
        "escalate": (r.get("outcome") == "escalate_to_human" or bool(r.get("escalate"))) == e["escalate"],
        "referral": bool(r.get("safety_referral", False)) == e["safety_referral"],
        "security": bool(r.get("security_flag", False)) == e["security_flag"],
        "fraud": bool(r.get("fraud_flag", False)) == e["fraud_flag"],
        "goodwill": abs((num(r.get("driver_goodwill_paid_by_ryde", 0)) or 0.0)
                        - e["driver_goodwill_paid_by_ryde"]) <= 0.05,
    }
    out["loose"] = out["outcome"] and out["amount"]
    out["strict"] = all(out[f] for f in FIELDS)
    return out


def main(path):
    key = json.load(open(os.path.join(ROOT, "test_set", "answer_key.json"), encoding="utf-8"))
    try:
        raw = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"cannot read {path}: {exc}")
    if not isinstance(raw, list):
        sys.exit("results.json must be a JSON list of rulings")

    res, notes = {}, []
    for i, r in enumerate(raw):
        if not isinstance(r, dict) or "id" not in r:
            notes.append(f"item {i}: not an object with an 'id'")
            continue
        if r["id"] in res:
            notes.append(f"{r['id']}: duplicate ruling, the first one is used")
            continue
        res[r["id"]] = r
    known = {k["id"] for k in key}
    notes += [f"{i}: not a test case id, ignored" for i in res if i not in known]
    missing = [k["id"] for k in key if k["id"] not in res]

    scored = collections.Counter()
    by_tag = collections.defaultdict(lambda: [0, 0])
    by_cat = collections.defaultdict(lambda: [0, 0, 0])
    esc = collections.Counter()
    prov = [0, 0]
    verdicts, fails, bad_format = {}, [], []
    for k in key:
        r = res.get(k["id"])
        if r is None:
            continue
        scored["n"] += 1
        fmt = check_format(r)
        if fmt:
            bad_format.append((k["id"], fmt))
            v = {f: False for f in FIELDS + ("loose", "strict")}
        else:
            v = judge(r, k)
        verdicts[k["id"]] = v
        for f in FIELDS + ("loose", "strict"):
            scored[f] += v[f]
        for tg in k["tags"]:
            by_tag[tg][0] += v["loose"]
            by_tag[tg][1] += 1
        by_cat[k["category"]][0] += v["loose"]
        by_cat[k["category"]][1] += v["strict"]
        by_cat[k["category"]][2] += 1
        if not v["loose"]:
            e = k["expected"]
            fails.append((k["id"], e["outcome"], e["refund_amount"], r.get("outcome"), r.get("refund_amount")))
        e = k["expected"]
        said_esc = (not fmt) and (r.get("outcome") == "escalate_to_human" or bool(r.get("escalate")))
        if e["escalate"]:
            esc["caught" if said_esc else "missed"] += 1
            if said_esc and e["provisional_outcome"]:
                prov[1] += 1
                prov[0] += r.get("provisional_outcome") == e["provisional_outcome"]
        elif said_esc:
            esc["unnecessary"] += 1
        if e["security_flag"]:
            esc["inj_found" if (not fmt and r.get("security_flag")) else "inj_missed"] += 1

    n = scored["n"]
    print(f"cases scored: {n}/{len(key)}" + (f"   no ruling for: {', '.join(missing)}" if missing else ""))
    if n == 0:
        for note in notes:
            print("  note:", note)
        return 1
    print(f"loose  (outcome and amount):         {scored['loose']}/{n}")
    print(f"strict (every field below correct):  {scored['strict']}/{n}")
    print("  per field: " + ", ".join(f"{f} {scored[f]}/{n}" for f in FIELDS))
    print("  by dispute type: " + ", ".join(f"{c} loose {a}/{m}, strict {s}/{m}"
                                            for c, (a, s, m) in by_cat.items()))
    print(f"escalation: caught {esc['caught']}, missed {esc['missed']}, unnecessary {esc['unnecessary']}"
          + (f"; provisional recommendation matched {prov[0]}/{prov[1]}" if prov[1] else ""))
    print(f"injection flagged: {esc['inj_found']}/{esc['inj_found'] + esc['inj_missed']}")

    def sig(x, with_fraud=True):
        out = (x["outcome"], round(num(x.get("refund_amount", 0)) or 0, 1), x.get("payer"),
               bool(x.get("driver_warning")), round(num(x.get("driver_goodwill_paid_by_ryde", 0)) or 0, 1),
               round(num(x.get("rider_charge_amount", 0)) or 0, 1), bool(x.get("rider_warning")),
               bool(x.get("safety_referral")))
        return out + ((bool(x.get("fraud_flag")),) if with_fraud else ())

    def usable(a, b):
        return a in res and b in res and not check_format(res[a]) and not check_format(res[b])

    pairs = [(k["id"], k["variant_of"]) for k in key if k["variant_of"]]
    same = sum(sig(res[a]) == sig(res[b]) for a, b in pairs if usable(a, b))
    print(f"consistency (same evidence, different people, language or filer): {same}/{len(pairs)} pairs "
          "identical on outcome, amounts, payer, warnings, goodwill, safety referral and fraud flag")
    cons = [(k["id"], k["contrast_of"]) for k in key if k.get("contrast_of")]
    good = sum(sig(res[a], False) == sig(res[b], False) and bool(res[a].get("fraud_flag")) !=
               bool(res[b].get("fraud_flag")) for a, b in cons if usable(a, b))
    print(f"contrast (one fact changed, only the fraud review flag should differ): {good}/{len(cons)}")

    print("\naccuracy by tag (loose):")
    for tg, (a, b) in sorted(by_tag.items(), key=lambda x: (x[1][0] / x[1][1], x[0])):
        print(f"  {tg:32s} {a}/{b}")
    if fails:
        print("\nwrong (outcome or amount):")
        for f in fails:
            print(f"  {f[0]}: expected {f[1]} ${f[2]}, got {f[3]} ${f[4]}")
    if bad_format:
        print("\nmalformed rulings (counted as wrong):")
        for cid, probs in bad_format:
            print(f"  {cid}: " + "; ".join(probs))
    for note in notes:
        print("note:", note)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
