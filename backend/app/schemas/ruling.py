from pydantic import BaseModel, Field


class RejectedClaim(BaseModel):
    advocate: str
    claim_text: str
    reason: str


class LLMRuling(BaseModel):
    outcome: str
    refund_amount: float = 0.0
    reasoning: str = ""
    deciding_evidence_ids: list[str] = Field(default_factory=list)
    deciding_policy_sections: list[str] = Field(default_factory=list)
    rejected_claims: list[RejectedClaim] = Field(default_factory=list)


class HumanReviewSummary(BaseModel):
    dispute: str
    rider_brief: str
    driver_brief: str
    key_evidence_ids: list[str] = Field(default_factory=list)
    ruling: str
    escalation_reason: str
    recommended_action: str
