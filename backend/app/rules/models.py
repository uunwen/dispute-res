from pydantic import BaseModel, Field


class Rule(BaseModel):
    id: str
    category: str
    citation: str = ""
    conditions: str
    outcome: str
    amount: str = "0"


class RuleResult(BaseModel):
    outcome: str
    refund_amount: float
    matched_rule_ids: list[str] = Field(default_factory=list)
    explanation: str
