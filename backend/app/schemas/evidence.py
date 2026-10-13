from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    id: str
    type: str
    trip_id: int | None = None
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    supports: Literal["rider", "driver", "neutral"]
    strength: float = Field(ge=0.0, le=1.0)


class ChatCue(BaseModel):
    message_ids: list[int] = Field(default_factory=list)
    text: str


class ChatInsights(BaseModel):
    threats: list[ChatCue] = Field(default_factory=list)
    admissions: list[ChatCue] = Field(default_factory=list)
    agreements: list[ChatCue] = Field(default_factory=list)
    disagreements: list[ChatCue] = Field(default_factory=list)
    key_claims: list[ChatCue] = Field(default_factory=list)
