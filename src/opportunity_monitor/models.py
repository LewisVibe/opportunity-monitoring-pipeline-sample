from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


SourceKind = Literal["web", "newsletter"]
Priority = Literal["high", "medium", "low"]
SourceStatus = Literal["healthy", "failed"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RawOpportunity(StrictModel):
    source_id: str = Field(min_length=2)
    source_kind: SourceKind
    external_id: str | None = None
    url: HttpUrl
    title: str = Field(min_length=3)
    content: str = Field(min_length=8)
    discovered_at: datetime
    deadline: date | None = None

    @model_validator(mode="after")
    def validate_timezone(self) -> "RawOpportunity":
        if self.discovered_at.tzinfo is None:
            raise ValueError("discovered_at must include a timezone")
        return self


class Classification(StrictModel):
    category: str = Field(min_length=2)
    priority: Priority
    summary: str = Field(min_length=8)
    relevance_reason: str = Field(min_length=8)
    confidence: float = Field(ge=0, le=1)


class OpportunityRecord(StrictModel):
    canonical_id: str = Field(min_length=12)
    title: str
    category: str
    priority: Priority
    summary: str
    relevance_reason: str
    confidence: float = Field(ge=0, le=1)
    review_required: bool
    deadline: date | None
    discovered_at: datetime
    source_ids: list[str] = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)


class SourceHealth(StrictModel):
    source_id: str
    status: SourceStatus
    item_count: int = Field(ge=0)
    consecutive_failures: int = Field(ge=0)
    last_error: str | None = None


class PipelineResult(StrictModel):
    records: list[OpportunityRecord]
    source_health: list[SourceHealth]
    review_queue: list[str]
