"""Generate synthetic fax PDFs for testing FaxFlow end-to-end.

Uses only fake names and fake data so you never test against real PHI.
Run:  python make_sample_faxes.py ./inbox
"""

from __future__ import annotations

import sys
from pathlib import Path

import pypdfium2 as pdfium  # noqa: F401  (ensures dep is installed)
from PIL import Image, ImageDraw, ImageFont


SAMPLES = [
    {
        "to": "Dr. Jane Smith",
        "type": "Radiology Report",
        "patient": "John Q. Public",
        "body": [
            "CHEST X-RAY, 2 VIEWS",
            "Findings: No acute cardiopulmonary process.",
            "Impression: Normal study.",
        ],
        "signature": False,
    },
    {
        "to": "Dr. Jane Smith",
        "type": "Referral / Consult Request",
        "patient": "Mary A. Sample",
        "body": [
            "Referring to Cardiology for evaluation of palpitations.",
            "Please sign and return to authorize the consult.",
            "Physician signature: ____________________",
        ],
        "signature": True,
    },
    {
        "to": "Dr. Robert Lee",
        "type": "Prescription Refill Request",
        "patient": "Carlos Example",
        "body": [
            "Pharmacy requests refill authorization for Lisinopril 10mg.",
            "Authorize? [ ] Yes [ ] No",
            "Prescriber signature: ____________________",
        ],
        "signature": True,
    },
    {
        "to": "Dr. Robert Lee",
        "type": "Lab Results",
        "patient": "Dana Fictional",
        "body": [
            "CBC with differential — all values within normal limits.",
            "No action required.",
        ],
        "signature": False,
    },
]


def _font(size: int):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def render(sample: dict, path: Path) -> None:
    img = Image.new("RGB", (1240, 1600), "white")
    d = ImageDraw.Draw(img)
    d.text((60, 50), "FAX TRANSMISSION", font=_font(40), fill="black")
    d.line((60, 110, 1180, 110), fill="black", width=2)
    d.text((60, 150), f"TO: {sample['to']}", font=_font(30), fill="black")
    d.text((60, 200), f"RE: {sample['type']}", font=_font(30), fill="black")
    d.text((60, 250), f"PATIENT: {sample['patient']}", font=_font(28), fill="black")
    d.line((60, 300, 1180, 300), fill="gray", width=1)
    y = 360
    for line in sample["body"]:
        d.text((60, y), line, font=_font(26), fill="black")
        y += 60
    img.save(path, "PDF", resolution=150)


def main(argv: list[str]) -> int:
    out = Path(argv[1] if len(argv) > 1 else "./inbox").expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    for i, sample in enumerate(SAMPLES, start=1):
        path = out / f"fax_{i:03d}.pdf"
        render(sample, path)
        print(f"wrote {path}")
    print(f"\n{len(SAMPLES)} sample faxes written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
