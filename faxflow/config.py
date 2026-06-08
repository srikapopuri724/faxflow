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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EmailConfig:
    host: str
    port: int
    user: str
    password: str
    folder: str
    search: str
    from_filter: str | None
    mark_seen: bool

    @classmethod
    def load(cls) -> "EmailConfig":
        host = os.environ.get("FAXFLOW_IMAP_HOST", "")
        user = os.environ.get("FAXFLOW_IMAP_USER", "")
        password = os.environ.get("FAXFLOW_IMAP_PASSWORD", "")
        missing = [
            n
            for n, v in (
                ("FAXFLOW_IMAP_HOST", host),
                ("FAXFLOW_IMAP_USER", user),
                ("FAXFLOW_IMAP_PASSWORD", password),
            )
            if not v
        ]
        if missing:
            raise RuntimeError(
                "Missing email settings: "
                + ", ".join(missing)
                + ". Add them to your .env (see .env.example)."
            )
        return cls(
            host=host,
            port=int(os.environ.get("FAXFLOW_IMAP_PORT", "993")),
            user=user,
            password=password,
            folder=os.environ.get("FAXFLOW_IMAP_FOLDER", "INBOX"),
            search=os.environ.get("FAXFLOW_IMAP_SEARCH", "UNSEEN"),
            from_filter=os.environ.get("FAXFLOW_IMAP_FROM") or None,
            # Marking messages seen mutates a shared mailbox, so default off.
            mark_seen=_env_bool("FAXFLOW_IMAP_MARK_SEEN", False),
        )
