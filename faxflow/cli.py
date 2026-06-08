"""Command-line entry point for FaxFlow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config, EmailConfig
from .email_connector import fetch_attachments
from .pipeline import process_inbox


def _print_progress(idx: int, total: int, pdf: Path) -> None:
    print(f"  [{idx}/{total}] {pdf.name}", file=sys.stderr)


def _do_fetch(out_dir: Path) -> int | None:
    """Returns the number of attachments downloaded, or None on error."""
    try:
        email_cfg = EmailConfig.load()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None

    mode = "read-write (will mark seen)" if email_cfg.mark_seen else "read-only"
    print(
        f"Connecting to {email_cfg.host} as {email_cfg.user} "
        f"[{email_cfg.folder}, search='{email_cfg.search}', {mode}] ...",
        file=sys.stderr,
    )
    try:
        attachments = fetch_attachments(email_cfg, out_dir)
    except Exception as exc:
        print(f"error: email fetch failed: {exc}", file=sys.stderr)
        return None
    print(f"Downloaded {len(attachments)} PDF attachment(s) to {out_dir}", file=sys.stderr)
    return len(attachments)


def _cmd_fetch(args: argparse.Namespace) -> int:
    out_dir = Path(args.out).expanduser().resolve()
    count = _do_fetch(out_dir)
    return 2 if count is None else 0


def _cmd_run(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox).expanduser().resolve()
    out_root = Path(args.out).expanduser().resolve()

    count = _do_fetch(inbox)
    if count is None:
        return 2
    if count == 0:
        print("No new fax attachments to process.", file=sys.stderr)
        return 0

    return _process(inbox, out_root, move=args.move)


def _process(inbox: Path, out_root: Path, move: bool) -> int:
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
        copy=not move,
        on_progress=_print_progress,
    )

    _summarize(results, out_root)
    return 0


def _cmd_process(args: argparse.Namespace) -> int:
    inbox = Path(args.inbox).expanduser().resolve()
    out_root = Path(args.out).expanduser().resolve()
    return _process(inbox, out_root, move=args.move)


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

    f = sub.add_parser(
        "fetch", help="Download fax PDF attachments from the IMAP mailbox."
    )
    f.add_argument(
        "-o", "--out", default="./inbox", help="Folder to save attachments (default: ./inbox)."
    )
    f.set_defaults(func=_cmd_fetch)

    r = sub.add_parser(
        "run", help="Fetch from email, then classify and sort, in one step."
    )
    r.add_argument(
        "-i", "--inbox", default="./inbox", help="Folder for downloaded faxes (default: ./inbox)."
    )
    r.add_argument(
        "-o", "--out", default="./sorted", help="Output folder (default: ./sorted)."
    )
    r.add_argument(
        "--move", action="store_true", help="Move files instead of copying them."
    )
    r.set_defaults(func=_cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
