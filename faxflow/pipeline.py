"""Orchestrates: find faxes -> classify -> route -> write reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .classifier import FaxClassifier
from .config import Config
from .models import ProcessedFax
from .router import route


def find_faxes(inbox: Path) -> list[Path]:
    return sorted(p for p in inbox.rglob("*.pdf") if p.is_file())


def process_inbox(
    inbox: Path,
    out_root: Path,
    config: Config,
    copy: bool = True,
    on_progress=None,
) -> list[ProcessedFax]:
    classifier = FaxClassifier(config)
    faxes = find_faxes(inbox)
    results: list[ProcessedFax] = []

    for idx, pdf in enumerate(faxes, start=1):
        if on_progress:
            on_progress(idx, len(faxes), pdf)
        try:
            classification = classifier.classify(pdf)
            result = route(pdf, classification, config, out_root, copy=copy)
        except Exception as exc:  # keep the batch going; surface per-file errors
            result = ProcessedFax(
                source_path=str(pdf),
                destination_path="",
                classification=None,  # type: ignore[arg-type]
                needs_review=True,
                review_reasons=["processing error"],
                error=str(exc),
            )
        results.append(result)

    _write_reports(out_root, results)
    return results


def _write_reports(out_root: Path, results: list[ProcessedFax]) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "faxes": [r.to_dict() for r in results],
    }
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2))

    review_queue = [r.to_dict() for r in results if r.needs_review]
    (out_root / "review_queue.json").write_text(json.dumps(review_queue, indent=2))
