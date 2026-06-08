"""Data structures passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class FaxClassification:
    """Structured result extracted from a single fax by the vision model."""

    provider_name: str
    document_type: str
    needs_signature: bool
    confidence: float
    patient_name: str | None = None
    summary: str | None = None
    page_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessedFax:
    """A fax after it has been classified and routed on disk."""

    source_path: str
    destination_path: str
    classification: FaxClassification
    needs_review: bool
    review_reasons: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "classification": self.classification.to_dict()
            if self.classification
            else None,
            "needs_review": self.needs_review,
            "review_reasons": self.review_reasons,
            "error": self.error,
        }
