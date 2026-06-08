# FaxFlow

Automated inbound-fax triage for clinics. Point it at a folder of fax PDFs and
it reads each one with Claude's vision model, identifies the associated
provider, classifies the document type, flags faxes that need a physician
signature, and files everything into per-provider folders — with a review queue
for anything it isn't confident about.

This is an MVP / prototype: a CLI that proves the core OCR + classification
pipeline on real (or synthetic) faxes. It is the "thin layer beside the EMR"
stage — no SRS/EMR integration yet.

## What it does

```
inbox/                          sorted/
  fax_001.pdf      ─────►         smith_jane/
  fax_002.pdf                       radiology/        fax_001.pdf
  fax_003.pdf                       _needs_signature/ fax_002.pdf
  fax_004.pdf                     lee_robert/
                                    _needs_signature/ fax_003.pdf
                                    lab_results/      fax_004.pdf
                                  _needs_review/      (low-confidence faxes)
                                  manifest.json       (full audit log)
                                  review_queue.json   (human-in-the-loop)
```

## Setup

```bash
cd ~/faxflow
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your ANTHROPIC_API_KEY
```

## Try it (no real patient data)

```bash
python make_sample_faxes.py ./inbox     # generates synthetic, fake-PHI faxes
python -m faxflow process ./inbox --out ./sorted
```

Then open `sorted/` and `sorted/review_queue.json`.

## Run on real faxes (from a folder)

```bash
python -m faxflow process /path/to/fax/folder --out ./sorted
```

By default files are **copied**, not moved, so your originals are untouched.
Pass `--move` only when you're confident.

## Pull faxes straight from email (IMAP)

Add the `FAXFLOW_IMAP_*` settings to `.env` (see `.env.example`), then:

```bash
python -m faxflow fetch --out ./inbox     # download PDF attachments only
python -m faxflow run                      # fetch + classify + sort in one step
```

- **Read-only by default.** FaxFlow does not mark, move, or delete messages
  unless you set `FAXFLOW_IMAP_MARK_SEEN=true`, so re-runs are safe and your
  mailbox is never mutated by surprise.
- Use `FAXFLOW_IMAP_SEARCH` (e.g. `UNSEEN`, `ALL`) and `FAXFLOW_IMAP_FROM` to
  scope which emails are pulled.
- For Gmail / Microsoft 365, generate an **app password** — your normal login
  password won't work with IMAP.

## Configuration (.env)

| Variable | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | required |
| `FAXFLOW_MODEL` | `claude-sonnet-4-6` | vision model used |
| `FAXFLOW_CONFIDENCE_THRESHOLD` | `0.75` | below this → review queue |
| `FAXFLOW_MAX_PAGES` | `3` | pages per fax sent to the model |

## ⚠️ Compliance — read before using real faxes

Faxes contain PHI. Sending them to any cloud API requires a signed **Business
Associate Agreement (BAA)** with the vendor, plus encryption, access controls,
and audit logging. Do **not** run this on real patient data until that is in
place. The synthetic generator (`make_sample_faxes.py`) uses only fake data and
is safe for development.

## Architecture

- `faxflow/pdf_utils.py` — rasterize fax PDFs to PNG
- `faxflow/classifier.py` — Claude vision + tool-use → structured fields
- `faxflow/router.py` — confidence-gated filing logic
- `faxflow/email_connector.py` — IMAP fetch of PDF attachments (stdlib only)
- `faxflow/pipeline.py` — orchestration + manifest/review-queue output
- `faxflow/cli.py` — `faxflow process` / `fetch` / `run` commands

## Roadmap

1. ~~CLI on a folder~~ ✅
2. ~~Email connector (IMAP) to auto-pull fax emails~~ ✅
3. **Next:** Review dashboard for the medical assistant.
4. E-signature instead of print → sign → refax.
5. SRS / HL7 / FHIR write-back (the defensible moat).
