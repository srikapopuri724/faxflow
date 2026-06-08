"""Decides where a classified fax belongs on disk and files it there."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .config import Config
from .models import FaxClassification, ProcessedFax

REVIEW_FOLDER = "_needs_review"
SIGNATURE_FOLDER = "_needs_signature"


def slugify(name: str) -> str:
    name = name.strip()
    if not name or name.upper() == "UNKNOWN":
        return "unknown_provider"
    name = re.sub(r"^(dr\.?|doctor)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name.lower() or "unknown_provider"


def _unique_destination(dest_dir: Path, filename: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem, suffix = Path(filename).stem, Path(filename).suffix
    i = 1
    while True:
        candidate = dest_dir / f"{stem}__{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def route(
    source: Path,
    classification: FaxClassification,
    config: Config,
    out_root: Path,
    copy: bool = True,
) -> ProcessedFax:
    """File a fax into out_root based on its classification.

    Low-confidence faxes go to a review folder instead of a provider folder so a
    human checks them before they ever reach a doctor's queue.
    """
    review_reasons: list[str] = []
    if classification.confidence < config.confidence_threshold:
        review_reasons.append(
            f"low confidence ({classification.confidence:.2f} < "
            f"{config.confidence_threshold:.2f})"
        )
    if classification.provider_name.upper() == "UNKNOWN":
        review_reasons.append("provider could not be identified")

    needs_review = bool(review_reasons)

    if needs_review:
        dest_dir = out_root / REVIEW_FOLDER
    else:
        provider = slugify(classification.provider_name)
        dest_dir = out_root / provider / classification.document_type
        if classification.needs_signature:
            dest_dir = out_root / provider / SIGNATURE_FOLDER

    destination = _unique_destination(dest_dir, source.name)
    if copy:
        shutil.copy2(source, destination)
    else:
        shutil.move(str(source), str(destination))

    return ProcessedFax(
        source_path=str(source),
        destination_path=str(destination),
        classification=classification,
        needs_review=needs_review,
        review_reasons=review_reasons,
    )
