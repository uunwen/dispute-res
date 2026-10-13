from app.schemas.evidence import EvidenceItem


def build_evidence(etype, ref, summary, data, supports, strength, trip_id=None) -> EvidenceItem:
    return EvidenceItem(
        id=f"{etype}:{ref}",
        type=etype,
        trip_id=trip_id,
        summary=summary,
        data=data,
        supports=supports,
        strength=round(min(max(strength, 0.0), 1.0), 3),
    )


def result_to_evidence(etype, ref, trip_id, result) -> EvidenceItem:
    return build_evidence(
        etype,
        ref,
        result["summary"],
        result["data"],
        result["supports"],
        result["strength"],
        trip_id=trip_id,
    )
