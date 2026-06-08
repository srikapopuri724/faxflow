"""Pulls PDF fax attachments from an IMAP mailbox into a local inbox folder.

Uses only the standard library (imaplib, email). Read-only by default: it does
not mark messages seen, move, or delete them unless explicitly configured, so
re-runs are idempotent and the shared mailbox is never mutated by surprise.
"""

from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message
from pathlib import Path

from .config import EmailConfig


@dataclass
class FetchedAttachment:
    uid: str
    original_filename: str
    saved_path: str
    from_addr: str
    subject: str


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _safe_filename(name: str) -> str:
    name = name.strip() or "fax.pdf"
    name = re.sub(r"[^\w.\- ]", "_", name)
    name = re.sub(r"\s+", "_", name)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def extract_pdf_attachments(msg: Message) -> list[tuple[str, bytes]]:
    """Pure function: return (filename, bytes) for each PDF attachment.

    Testable without any network connection.
    """
    out: list[tuple[str, bytes]] = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = _decode(part.get_filename())
        ctype = (part.get_content_type() or "").lower()
        is_pdf = ctype == "application/pdf" or filename.lower().endswith(".pdf")
        if not is_pdf:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        out.append((_safe_filename(filename or "fax.pdf"), payload))
    return out


def _unique_path(out_dir: Path, filename: str) -> Path:
    candidate = out_dir / filename
    if not candidate.exists():
        return candidate
    stem, suffix = Path(filename).stem, Path(filename).suffix
    i = 1
    while True:
        candidate = out_dir / f"{stem}__{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _build_search(cfg: EmailConfig) -> list[str]:
    criteria = cfg.search.split() if cfg.search else ["ALL"]
    if cfg.from_filter:
        criteria += ["FROM", cfg.from_filter]
    return criteria


def fetch_attachments(cfg: EmailConfig, out_dir: Path) -> list[FetchedAttachment]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fetched: list[FetchedAttachment] = []

    conn = imaplib.IMAP4_SSL(cfg.host, cfg.port)
    try:
        conn.login(cfg.user, cfg.password)
        # readonly=True unless we're allowed to mark messages seen.
        conn.select(cfg.folder, readonly=not cfg.mark_seen)

        typ, data = conn.uid("search", None, *_build_search(cfg))
        if typ != "OK":
            raise RuntimeError(f"IMAP search failed: {typ}")
        uids = data[0].split()

        for uid in uids:
            uid_str = uid.decode()
            typ, msg_data = conn.uid("fetch", uid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            from_addr = _decode(msg.get("From"))
            subject = _decode(msg.get("Subject"))

            for filename, payload in extract_pdf_attachments(msg):
                dest = _unique_path(out_dir, f"{uid_str}_{filename}")
                dest.write_bytes(payload)
                fetched.append(
                    FetchedAttachment(
                        uid=uid_str,
                        original_filename=filename,
                        saved_path=str(dest),
                        from_addr=from_addr,
                        subject=subject,
                    )
                )

            if cfg.mark_seen:
                conn.uid("store", uid, "+FLAGS", "(\\Seen)")
    finally:
        try:
            conn.close()
        except Exception:
            pass
        conn.logout()

    return fetched
