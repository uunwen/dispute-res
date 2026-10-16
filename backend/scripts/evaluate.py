import asyncio
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from app.config import settings
from app.db import models
from app.db.session import async_session_factory
from app.llm.client import LLMError, model_for_role
from app.llm.embeddings import embeddings
from app.orchestrator.pipeline import resolve_dispute

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
EVAL_DIR = DATA_DIR / "eval"

DATASET_LABEL = "synthetic variants of organizer samples"


async def _dispute_id_by_external(session, external_id: str) -> int | None:
    return (
        await session.execute(
            select(models.Dispute.id).where(models.Dispute.external_id == external_id)
        )
    ).scalar_one_or_none()


async def _reset_disputes(dispute_ids: list[int]) -> None:
    if not dispute_ids:
        return
    async with async_session_factory() as session:
        await session.execute(delete(models.Ruling).where(models.Ruling.dispute_id.in_(dispute_ids)))
        await session.execute(delete(models.AgentMessage).where(models.AgentMessage.dispute_id.in_(dispute_ids)))
        disputes = (
            await session.execute(select(models.Dispute).where(models.Dispute.id.in_(dispute_ids)))
        ).scalars().all()
        for dispute in disputes:
            dispute.status = "open"
        await session.commit()


async def _resolve_one(semaphore: asyncio.Semaphore, dispute_id: int) -> tuple[int, float, bool]:
    async with semaphore:
        start = time.perf_counter()
        last_exc: Exception | None = None
        for attempt in range(settings.llm_max_retries + 1):
            try:
                ruling = await resolve_dispute(dispute_id)
                # A degraded ruling is almost always a transient LLM failure
                # (e.g. 429 rate limit), not a permanent one. Wait on an
                # exponential backoff and retry the whole dispute rather than
                # silently counting it as degraded.
                if ruling.llm_degraded:
                    wait = settings.llm_backoff_base * (2 ** (attempt + 2))
                    print(f"  dispute {dispute_id}: degraded (LLM); retrying in {wait:.2f}s", flush=True)
                    await asyncio.sleep(wait)
                    continue
                return dispute_id, time.perf_counter() - start, False
            except LLMError as exc:
                last_exc = exc
                wait = settings.llm_backoff_base * (2 ** attempt)
                print(f"  dispute {dispute_id}: LLM error ({exc}); retrying in {wait:.2f}s", flush=True)
                await asyncio.sleep(wait)
        return dispute_id, time.perf_counter() - start, last_exc is not None


async def _latest_ruling(session, dispute_id: int) -> models.Ruling | None:
    return (
        await session.execute(
            select(models.Ruling)
            .where(models.Ruling.dispute_id == dispute_id)
            .order_by(models.Ruling.created_at.desc())
        )
    ).scalars().first()


def _pct(numer: int, denom: int) -> float:
    return (numer / denom) if denom else 0.0


async def main() -> None:
    expected = json.loads((EVAL_DIR / "expected.json").read_text(encoding="utf-8"))

    entries: list[tuple[dict, int]] = []
    async with async_session_factory() as session:
        for entry in expected:
            dispute_id = await _dispute_id_by_external(session, entry["external_id"])
            if dispute_id is None:
                print(f"  warning: no dispute for external_id {entry['external_id']}", flush=True)
                continue
            entries.append((entry, dispute_id))

    dispute_ids = [dispute_id for _, dispute_id in entries]
    await _reset_disputes(dispute_ids)

    semaphore = asyncio.Semaphore(settings.eval_concurrency)
    print(
        f"Evaluating {len(dispute_ids)} disputes ({DATASET_LABEL}) "
        f"with concurrency {settings.eval_concurrency} (LLM_MOCK={settings.llm_mock})...",
        flush=True,
    )
    total_start = time.perf_counter()
    results = await asyncio.gather(*[_resolve_one(semaphore, dispute_id) for _, dispute_id in entries])
    total_time = time.perf_counter() - total_start

    seconds_by_id = {dispute_id: seconds for dispute_id, seconds, _failed in results}
    failed_ids = {dispute_id for dispute_id, _s, failed in results if failed}

    # --- per-dispute collection ---
    rows: list[dict] = []
    degraded_rows: list[dict] = []
    async with async_session_factory() as session:
        for entry, dispute_id in entries:
            ruling = await _latest_ruling(session, dispute_id)
            row = {
                "external_id": entry["external_id"],
                "section": entry.get("section", "?"),
                "expected_outcome": entry["outcome"],
                "expected_refund": entry["refund_amount"],
                "expected_escalate": bool(entry["escalate"]),
                "actual_outcome": None,
                "actual_refund": None,
                "actual_escalated": None,
                "llm_degraded": None,
                "seconds": round(seconds_by_id.get(dispute_id, 0.0), 3),
                "failed": dispute_id in failed_ids,
                "model_info": None,
            }
            if ruling is not None:
                row["actual_outcome"] = ruling.outcome.value
                row["actual_refund"] = ruling.refund_amount
                row["actual_escalated"] = bool(ruling.escalated)
                row["llm_degraded"] = ruling.llm_degraded
                row["model_info"] = ruling.model_info
                if ruling.llm_degraded:
                    degraded_rows.append(row)
            rows.append(row)

    # --- metrics ---
    non_degraded_rows = [r for r in rows if r["llm_degraded"] is False and r["actual_outcome"] is not None]
    total = len([r for r in rows if r["actual_outcome"] is not None])
    degraded = len(degraded_rows)

    correct = sum(1 for r in non_degraded_rows if r["actual_outcome"] == r["expected_outcome"])
    non_degraded = len(non_degraded_rows)

    refund_errors = [
        abs(r["actual_refund"] - r["expected_refund"])
        for r in non_degraded_rows
        if r["actual_refund"] is not None
    ]

    tp = fp = fn = tn = 0
    for r in non_degraded_rows:
        e = r["expected_escalate"]
        a = r["actual_escalated"]
        if e and a:
            tp += 1
        elif e and not a:
            fn += 1
        elif not e and a:
            fp += 1
        else:
            tn += 1

    per_section: dict[str, dict[str, int]] = {}
    for r in non_degraded_rows:
        bucket = per_section.setdefault(r["section"], {"correct": 0, "total": 0})
        bucket["total"] += 1
        if r["actual_outcome"] == r["expected_outcome"]:
            bucket["correct"] += 1

    times = [seconds_by_id[d] for _, d in entries if d in seconds_by_id]
    mean_time = statistics.mean(times) if times else 0.0

    models_per_role = {
        "advocate": model_for_role("advocate"),
        "judge": model_for_role("judge"),
        "tools": model_for_role("tools"),
    }

    report = {
        "meta": {
            "dataset": DATASET_LABEL,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "eval_concurrency": settings.eval_concurrency,
            "llm_mock": settings.llm_mock,
            "rebuttal_enabled": settings.rebuttal_enabled,
            "models_per_role": models_per_role,
            "embedding": {
                "provider": embeddings.active_provider,
                "model": embeddings.active_model,
                "dimension": embeddings.dimension,
                "fell_back_to_fastembed": bool(embeddings.fallback_reason),
            },
        },
        "metrics": {
            "disputes_resolved": total,
            "degraded": degraded,
            "non_degraded": non_degraded,
            "accuracy": {"correct": correct, "n": non_degraded, "value": _pct(correct, non_degraded)},
            "refund_error": {
                "mean": round(statistics.mean(refund_errors), 3) if refund_errors else None,
                "max": round(max(refund_errors), 3) if refund_errors else None,
                "n": len(refund_errors),
            },
            "escalation": {
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": _pct(tp, tp + fp),
                "recall": _pct(tp, tp + fn),
            },
            "per_section": {
                s: {
                    "correct": b["correct"],
                    "total": b["total"],
                    "accuracy": _pct(b["correct"], b["total"]),
                }
                for s, b in sorted(per_section.items())
            },
            "time": {
                "mean_seconds": round(mean_time, 2),
                "median_seconds": round(statistics.median(times), 2) if times else None,
                "max_seconds": round(max(times), 2) if times else None,
                "total_seconds": round(total_time, 2),
                "n": len(times),
            },
        },
        "degraded": degraded_rows,
        "disputes": rows,
    }

    (EVAL_DIR / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (EVAL_DIR / "report.md").write_text(_markdown(report), encoding="utf-8")

    _print_summary(report)
    print(f"\nsaved JSON -> {EVAL_DIR / 'report.json'}")
    print(f"saved markdown -> {EVAL_DIR / 'report.md'}")


def _markdown(report: dict) -> str:
    m = report["meta"]
    x = report["metrics"]
    lines: list[str] = []
    lines.append("# Evaluation report\n")
    lines.append(f"- dataset: {m['dataset']}")
    lines.append(f"- concurrency: {m['eval_concurrency']} (LLM_MOCK={m['llm_mock']})")
    lines.append(
        f"- models: advocate=`{m['models_per_role']['advocate']}` · "
        f"judge=`{m['models_per_role']['judge']}` · tools=`{m['models_per_role']['tools']}`"
    )
    e = m["embedding"]
    lines.append(f"- embedding: {e['provider']}/{e['model']} (dim {e['dimension']})\n")

    lines.append("## Summary\n")
    lines.append(f"- disputes resolved: **{x['disputes_resolved']}**")
    lines.append(f"- degraded (excluded from metrics): **{x['degraded']}**")
    if report["degraded"]:
        ids = ", ".join(r["external_id"] for r in report["degraded"])
        lines.append(f"  - {ids}")
    lines.append(f"- non-degraded: **{x['non_degraded']}**\n")

    lines.append("## Metrics\n")
    lines.append("| metric | value |")
    lines.append("|---|---|")
    a = x["accuracy"]
    lines.append(f"| outcome accuracy | {a['correct']}/{a['n']} ({a['value']:.1%}) |")
    re_ = x["refund_error"]
    if re_["mean"] is not None:
        lines.append(f"| refund error (mean |actual − expected|) | {re_['mean']:.3f} (n={re_['n']}, max {re_['max']:.3f}) |")
    else:
        lines.append("| refund error | n/a |")
    es = x["escalation"]
    lines.append(
        f"| escalation precision | {es['tp']}/{es['tp'] + es['fp']} ({es['precision']:.1%}) |"
    )
    lines.append(
        f"| escalation recall | {es['tp']}/{es['tp'] + es['fn']} ({es['recall']:.1%}) |"
    )
    lines.append(
        f"| mean time per dispute | {x['time']['mean_seconds']}s "
        f"(n={x['time']['n']}, median {x['time']['median_seconds']}s, max {x['time']['max_seconds']}s) |"
    )

    lines.append("\n## Per-section accuracy\n")
    lines.append("| section | correct | total | accuracy |")
    lines.append("|---|---|---|---|")
    for s, b in x["per_section"].items():
        lines.append(f"| {s} | {b['correct']} | {b['total']} | {b['accuracy']:.1%} |")

    lines.append("\n## Per-dispute\n")
    lines.append("| id | sec | expected | actual | escal (exp→act) | degraded | seconds |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in report["disputes"]:
        esc = f"{'Y' if r['expected_escalate'] else 'N'}→{'Y' if r['actual_escalated'] else 'N'}"
        exp = f"{r['expected_outcome']} / {r['expected_refund']:.2f}"
        act = f"{r['actual_outcome']} / {r['actual_refund']:.2f}" if r["actual_outcome"] else "—"
        lines.append(
            f"| {r['external_id']} | {r['section']} | {exp} | {act} | {esc} | "
            f"{'Y' if r['llm_degraded'] else 'N'} | {r['seconds']} |"
        )
    return "\n".join(lines) + "\n"


def _print_summary(report: dict) -> None:
    m = report["meta"]
    x = report["metrics"]
    a = x["accuracy"]
    es = x["escalation"]
    re_ = x["refund_error"]
    print("\n=== evaluation report ===", flush=True)
    print(f"dataset: {m['dataset']}")
    print(f"concurrency: {m['eval_concurrency']}  LLM_MOCK: {m['llm_mock']}")
    print(f"models: advocate={m['models_per_role']['advocate']} judge={m['models_per_role']['judge']} tools={m['models_per_role']['tools']}")
    print(f"embedding: {m['embedding']['provider']}/{m['embedding']['model']} dim={m['embedding']['dimension']}")
    print(f"\ndisputes resolved: {x['disputes_resolved']}")
    print(f"degraded (excluded): {x['degraded']}")
    if report["degraded"]:
        print("  degraded ids: " + ", ".join(r["external_id"] for r in report["degraded"]))
    print(f"non-degraded: {x['non_degraded']}")
    print(f"\noutcome accuracy: {a['correct']}/{a['n']} ({a['value']:.1%})")
    if re_["mean"] is not None:
        print(f"refund error (mean): {re_['mean']:.3f} (n={re_['n']}, max {re_['max']:.3f})")
    print(f"escalation precision: {es['tp']}/{es['tp']+es['fp']} ({es['precision']:.1%})")
    print(f"escalation recall: {es['tp']}/{es['tp']+es['fn']} ({es['recall']:.1%})")
    print("per-section accuracy:")
    for s, b in x["per_section"].items():
        print(f"  Sec {s}: {b['correct']}/{b['total']} ({b['accuracy']:.1%})")
    t = x["time"]
    print(f"\nmean time per dispute: {t['mean_seconds']}s (n={t['n']}, median {t['median_seconds']}s, max {t['max_seconds']}s)")


if __name__ == "__main__":
    asyncio.run(main())
