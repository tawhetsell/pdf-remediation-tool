# PDF Accessibility Tool

Automated PDF remediation pipeline targeting Canvas/Ally scores at `High` or `Perfect`. Designed for instructors remediating course materials for Title II / WCAG 2.1 AA compliance.

Instructors facing compliance deadlines often remove supplementary materials rather than remediate them — students lose access to enrichment content and the institution technically passes by impoverishment. This tool makes remediation cheap enough that removal is no longer the rational choice.

While developed and validated against Canvas/Ally scoring, the pipeline is LMS-agnostic — the underlying standard is WCAG 2.1 AA / PDF/UA, which applies equally to Blackboard, Moodle, D2L Brightspace, or any direct file distribution workflow.

Contributions and adaptations from other instructors and instructional designers are welcome. If you're working on a similar problem at your institution, open an issue or pull request.

> **Disclaimer:** Files produced by this pipeline are accessibility candidates, not certified-compliant documents. Users are responsible for verifying compliance with their institution's requirements. This tool is provided as-is with no warranty — see [LICENSE](LICENSE).

## What it does

- Classifies PDFs (born-digital, scanned, phantom-tree)
- Auto-tags untagged PDFs using `opendataloader-pdf` (local, no cloud)
- Adds OCR text layer to scanned files via `ocrmypdf`
- Patches catalog metadata (`/MarkInfo`, `/Lang`, `/Title`)
- Organizes remediated files by Canvas module with clean canonical names
- Tracks Ally scores in `STATUS.md`

**AI interface:** Works with Claude Code via the `/remediate` slash command, or with OpenAI Codex via the `.agents/skills/remediate/SKILL.md` skill — both load the same workflow from `AGENT_INSTRUCTIONS.md`. Either agent can be invoked with a single command.

## Prerequisites

- **AI agent** — [Claude Code](https://claude.ai/code) or [OpenAI Codex](https://developers.openai.com/codex/quickstart)
  - Codex: `npm install -g @openai/codex` or `brew install --cask codex`
- Python 3.10+
- Java 11+ (for `opendataloader-pdf`)
  - macOS: `brew install openjdk@17`
  - Windows: install any JDK 11+ and ensure `java` is on your PATH
- `pip install --upgrade opendataloader-pdf pypdf` ([opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf), [pypdf](https://github.com/py-pdf/pypdf))
- `ocrmypdf` (optional, for scanned files)
  - macOS: `brew install ocrmypdf`
  - Windows: install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) then `pip install ocrmypdf`
- `verapdf` (optional, for local PDF/UA validation)

**Platform:** macOS and Linux natively. Windows via Git Bash with Java on PATH.

Run `bash scripts/bootstrap.sh` to verify your environment.

## Quick start

```bash
# 1. Clone and set up
git clone https://github.com/tawhetsell/pdf-remediation-tool
cd pdf-remediation-tool
bash setup.sh          # creates workspace folder structure (run once)
bash scripts/bootstrap.sh  # verifies Java, Python, and dependencies

# 2. Drop source PDFs into originals/
cp ~/Downloads/my_lecture.pdf originals/

# 3. Run the skill from your AI agent
/remediate my_lecture.pdf policy_theory
```

Your agent will classify the file, run the appropriate pipeline, ask for a canonical name, and stage the result to `work/canvas_ready/policy_theory/`.

**Claude Code:** `/remediate` is available as a slash command automatically.  
**Codex:** the skill is at `.agents/skills/remediate/SKILL.md` and loads automatically.

## Pipeline

```
originals/<file>.pdf
  → classify (born-digital / scanned / phantom-tree)
  → [OCR if scanned]       ocrmypdf
  → [Auto-tag]             opendataloader-pdf → work/tagged/
  → [Catalog patch]        patch_catalog_accessibility.py → work/patched/
  → [Rename + stage]       work/canvas_ready/<module>/<canonical_name>.pdf
  → HUMAN: Canvas upload
  → Record Ally score in STATUS.md
```

## Fallback ladder

If `opendataloader-pdf` produces a phantom tree (structure shell, no marked content):

1. `ocrmypdf --output-type pdf` then retry ODL
2. `ocrmypdf --force-ocr` then retry ODL
3. Adobe Acrobat Pro → Make Accessible (manual)
4. Adobe PDF Services Auto-Tag API (cloud, 500/month free tier — requires data governance sign-off)

## Canvas/Ally targets

- `High` (67–99) or `Perfect` (100) after upload
- Local `veraPDF` UA-1 validation is useful triage but not a substitute for the actual Canvas score
- A file can pass Canvas before every local validator item is clean

## File naming convention

The pipeline asks you for a canonical filename at staging time — use whatever convention works for your institution or course. One example system:

| Type | Pattern | Example |
|---|---|---|
| Lecture slide | `descriptive_topic.pdf` | `market_failures.pdf` |
| Textbook chapter | `lastname_ch##.pdf` | `weimer_ch08.pdf` |
| Author-year reading | `lastname_year.pdf` | `shields_2017.pdf` |
| Policy document | descriptive | `omb_circular_a94.pdf` |
| Example / exercise | `example_description.pdf` | `example_woodstock_cra.pdf` |

Whatever system you use, consistency within a course makes Canvas module management easier.

## What this tool does and does not do

ODL tags the actual content stream — BDC/EMC marked-content operators attached to real text runs, not a structural shell over nothing. A screen reader following those tags reads the real document in a navigable order. That is a genuine improvement over an untagged file.

What auto-tagging cannot do:

- **Figure alt text** — ODL cannot infer what a chart or diagram means. Files with meaningful images need manual alt text added (Acrobat Pro → Tags panel).
- **Semantic heading hierarchy** — ODL guesses from font size and position. Complex layouts may need manual correction.
- **Reading order in multi-column layouts** — auto-detected order may need verification for dense or non-linear documents.
- **Mathematical notation** — formulas are not accessible without MathML or a text equivalent.

**Intended framing:** this pipeline gets the structural prerequisite in place so that accessibility review is possible. Without tagged structure, meaningful manual remediation cannot begin. Files produced here should be treated as candidates requiring spot-check before claiming full compliance.

A screen reader spot-check is the fastest real-world test:
- **macOS** — VoiceOver (Cmd+F5), open PDF in Preview, arrow through the document
- **Windows** — [NVDA](https://www.nvaccess.org/download/) (free), open PDF in Adobe Acrobat Reader, arrow through the document

## Built with

This repository was developed with assistance from Claude Code (Opus 4.7, Sonnet 4.6) and ChatGPT 5.4.

## License

Licensed under [GPL v3](LICENSE). Free for academic and personal use. Commercial use requires a separate license — open an issue to discuss.

