from pydantic import BaseModel, Field


class FraudReason(BaseModel):
    code: str
    description: str
    evidence_id: str


class FraudSignal(BaseModel):
    trip_id: int
    rider_risk: float
    driver_risk: float
    reasons: list[FraudReason] = Field(default_factory=list)
