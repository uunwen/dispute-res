from pydantic import BaseModel, Field


class CaseClaim(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    policy_section_ids: list[str] = Field(default_factory=list)


class CaseBrief(BaseModel):
    position: str
    argument_summary: str
    claims: list[CaseClaim] = Field(default_factory=list)
    requested_outcome: str
    weaknesses: list[str] = Field(default_factory=list)
