"""Runtime configuration, loaded from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Document categories the assistant currently sorts faxes into.
DOCUMENT_TYPES = [
    "radiology",
    "referral",
    "lab_results",
    "prescription_refill",
    "insurance_auth",
    "patient_records",
    "billing",
    "other",
]


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str
    confidence_threshold: float
    max_pages: int

    @classmethod
    def load(cls) -> "Config":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        return cls(
            api_key=api_key,
            model=os.environ.get("FAXFLOW_MODEL", "claude-sonnet-4-6"),
            confidence_threshold=float(
                os.environ.get("FAXFLOW_CONFIDENCE_THRESHOLD", "0.75")
            ),
            max_pages=int(os.environ.get("FAXFLOW_MAX_PAGES", "3")),
        )
