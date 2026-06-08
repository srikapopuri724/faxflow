"""Command-line entry point for FaxFlow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config
from .pipeline import process_inbox


def _print_progress(idx: int, total: int, pdf: Path) -> None:
    print(f"  [{idx}/{total}] {pdf.name}", file=sys.stderr)


def _cmd_process(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox).expanduser().resolve()
    out_root = Path(args.out).expanduser().resolve()

    if not inbox.is_dir():
        print(f"error: inbox '{inbox}' is not a directory", file=sys.stderr)
        return 2

    try:
        config = Config.load()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Scanning {inbox} ...", file=sys.stderr)
    results = process_inbox(
        inbox,
        out_root,
        config,
        copy=not args.move,
        on_progress=_print_progress,
    )

    _summarize(results, out_root)
    return 0


def _summarize(results, out_root: Path) -> None:
    total = len(results)
    review = sum(1 for r in results if r.needs_review)
    errors = sum(1 for r in results if r.error)
    signatures = sum(
        1
        for r in results
        if r.classification and r.classification.needs_signature and not r.needs_review
    )
    print("")
    print("FaxFlow summary")
    print("===============")
    print(f"  processed:        {total}")
    print(f"  auto-filed:       {total - review}")
    print(f"  needs review:     {review}")
    print(f"  needs signature:  {signatures}")
    print(f"  errors:           {errors}")
    print("")
    print(f"  output:           {out_root}")
    print(f"  manifest:         {out_root / 'manifest.json'}")
    print(f"  review queue:     {out_root / 'review_queue.json'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="faxflow", description="Automated inbound-fax triage for clinics."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("process", help="Classify and sort a folder of fax PDFs.")
    p.add_argument("inbox", help="Folder containing incoming fax PDFs.")
    p.add_argument(
        "-o", "--out", default="./sorted", help="Output folder (default: ./sorted)."
    )
    p.add_argument(
        "--move",
        action="store_true",
        help="Move files instead of copying them (destructive).",
    )
    p.set_defaults(func=_cmd_process)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
