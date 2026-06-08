"""Reads a fax with Claude's vision model and returns structured fields.

Uses tool-use to force a structured JSON result, and prompt caching on the
static system prompt + tool schema to cut cost across a batch of faxes."""

from __future__ import annotations

from pathlib import Path

import anthropic

from .config import Config, DOCUMENT_TYPES
from .models import FaxClassification
from .pdf_utils import page_count, render_pdf_to_png, to_base64

SYSTEM_PROMPT = (
    "You are a medical front-office assistant that triages inbound faxes for a "
    "clinic. Faxes are scanned, often low quality, and may include a cover sheet. "
    "Your job is to identify (1) which of OUR providers the fax is associated with "
    "— i.e. the recipient/attending provider at our practice, NOT the sending "
    "facility or an unrelated referring doctor unless they are the recipient — "
    "(2) what kind of document it is, and (3) whether it requires a physician's "
    "signature (look for signature lines, 'sign and return', attestation blocks, "
    "order forms). Be conservative: if you are unsure about the provider, lower "
    "your confidence rather than guessing."
)

RECORD_FAX_TOOL = {
    "name": "record_fax",
    "description": "Record the structured triage result for one fax document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "provider_name": {
                "type": "string",
                "description": "Full name of the associated provider at our practice "
                "(e.g. 'Dr. Jane Smith'). Use 'UNKNOWN' if it cannot be determined.",
            },
            "document_type": {
                "type": "string",
                "enum": DOCUMENT_TYPES,
                "description": "Best-fit category for the document.",
            },
            "needs_signature": {
                "type": "boolean",
                "description": "True if a physician signature is required.",
            },
            "patient_name": {
                "type": "string",
                "description": "Patient name if present, else empty string.",
            },
            "summary": {
                "type": "string",
                "description": "One short sentence describing the fax.",
            },
            "confidence": {
                "type": "number",
                "description": "0.0-1.0 confidence in the provider + type assignment.",
            },
        },
        "required": [
            "provider_name",
            "document_type",
            "needs_signature",
            "confidence",
        ],
    },
}


class FaxClassifier:
    def __init__(self, config: Config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.api_key)

    def classify(self, pdf_path: Path) -> FaxClassification:
        pages = render_pdf_to_png(pdf_path, max_pages=self.config.max_pages)
        if not pages:
            raise ValueError(f"No renderable pages in {pdf_path}")

        content: list[dict] = []
        for png in pages:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": to_base64(png),
                    },
                }
            )
        content.append(
            {
                "type": "text",
                "text": "Triage this fax. Call record_fax with your result.",
            }
        )

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[RECORD_FAX_TOOL],
            tool_choice={"type": "tool", "name": "record_fax"},
            messages=[{"role": "user", "content": content}],
        )

        tool_input = self._extract_tool_input(response)
        return FaxClassification(
            provider_name=tool_input.get("provider_name", "UNKNOWN") or "UNKNOWN",
            document_type=tool_input.get("document_type", "other") or "other",
            needs_signature=bool(tool_input.get("needs_signature", False)),
            confidence=float(tool_input.get("confidence", 0.0)),
            patient_name=(tool_input.get("patient_name") or None),
            summary=(tool_input.get("summary") or None),
            page_count=page_count(pdf_path),
        )

    @staticmethod
    def _extract_tool_input(response) -> dict:
        for block in response.content:
            if block.type == "tool_use" and block.name == "record_fax":
                return block.input
        raise RuntimeError("Model did not return a record_fax tool call.")
