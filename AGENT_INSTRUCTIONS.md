# AGENT_INSTRUCTIONS.md

Auto-loaded every session. Operating context for this workspace.

## What this workspace is

A portable PDF accessibility remediation tool targeting Canvas/Ally scores at `High` (67–99) or `Perfect` (100). Standard is WCAG 2.1 AA. The primary skill is `/remediate` — see `.claude/commands/remediate.md`.

Success is only proven by a recorded Ally score on an uploaded file. Do not claim a file is remediated without one.

## Workspace layout

| Path | Write? | Purpose |
|---|---|---|
| `originals/` | **NEVER** | Canonical source PDFs. Immutable. Copy here on intake; never modify. |
| `work/inputs/` | yes | Working copies for pipeline. Always copy from `originals/` first. |
| `work/tagged/` | yes | ODL auto-tag output. `<stem>_tagged.pdf`. |
| `work/patched/` | yes | Catalog-patched output. `<stem>_tagged_patched.pdf`. |
| `work/canvas_ready/<module>/` | yes | Final renamed files organized by Canvas module. Upload from here. |
| `work/runs/<date>_<desc>/` | yes | Per-run JSON reports and markdown summaries. |
| `scripts/` | yes | Pipeline tooling. No data files. |
| `STATUS.md` | yes | Per-file state. Authoritative record of Ally scores. |

## File naming convention

All files in `canvas_ready/` follow these patterns — all lowercase, underscores, no spaces:

| Type | Pattern | Example |
|---|---|---|
| Lecture slide | `descriptive_topic.pdf` | `market_failures.pdf` |
| Textbook chapter | `lastname_ch##.pdf` | `weimer_ch08.pdf` |
| Author-year reading | `lastname_year.pdf` | `shields_2017.pdf` |
| Policy document | descriptive | `omb_circular_a94.pdf` |
| Example / exercise | `example_description.pdf` | `example_decision_making.pdf` |

No week-number prefixes — module order may change between semesters.

## Tooling fallback ladder

For creating a structure tree on a born-digital untagged PDF, try in order:

1. **`opendataloader-pdf` auto-tag** — primary path. Free, local, Apache-2.0.
2. **`ocrmypdf` + ODL** — for scanned files. Standard OCR first; `--force-ocr` if ODL still produces a phantom tree.
3. **Adobe Acrobat Pro "Make Accessible"** — manual GUI fallback for files ODL cannot handle.
4. **Adobe PDF Services Auto-Tag API** — cloud, 500/month free. Requires data governance sign-off before first use.

## Hard rules

- **Never modify `originals/`.** Always copy to `work/inputs/` first.
- **Never upload to Canvas autonomously.** Surface candidates to the human; human uploads and reports back.
- **Never claim "remediated"** without a recorded Ally score. Use "candidate" until scored.
- **Never skip `bootstrap.sh` at session start.** ODL fails silently without Java 11+.
- **Never overwrite a prior run directory.** Each invocation creates a new `work/runs/<date>_<desc>/`.

## Session start protocol

1. `bash scripts/bootstrap.sh` — stop if nonzero.
2. Read `STATUS.md` — understand current state before doing more.
3. Run `/remediate` for new files, or record Ally scores for staged files.
