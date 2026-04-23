---
name: remediate
description: PDF accessibility remediation pipeline for Canvas/Ally compliance. Use when the user wants to process, tag, patch, or stage a PDF for upload — or when they drop a file into originals/ and want it remediated. Do not use for general PDF questions or viewing.
---

# remediate

PDF accessibility remediation pipeline. Classifies, tags, patches, and stages a PDF for Canvas/Ally upload.

## Usage

```
/remediate <filename> [module_folder]
```

- **filename** — PDF in `originals/` to process. Omit to list unprocessed files.
- **module_folder** — target subfolder in `work/canvas_ready/`. Omit to be prompted.

---

## Steps

### 1 — Bootstrap

```bash
bash scripts/bootstrap.sh
```

Stop if nonzero. Do not proceed with a broken environment.

---

### 2 — Classify

```bash
python3 scripts/classify_pdfs.py originals/<filename>
```

Read the output class and route accordingly:

| Class | Route |
|---|---|
| `born_digital_untagged` or `phantom_tree` | Step 3a |
| `scanned` | Step 3b |
| `tagged` (BDC > 0) | Skip to Step 4 |

---

### 3a — ODL auto-tag (born-digital / phantom-tree)

```bash
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
cp -n originals/<file> work/inputs/
RUN_DIR="work/runs/$(date +%F)_remediate_<stem>"
mkdir -p "$RUN_DIR"
python3 scripts/run_priority_zero.py \
  --materials  work/inputs \
  --tagged-dir work/tagged \
  --out        work/patched \
  --reports    "$RUN_DIR" \
  --targets    <file>
```

Check `$RUN_DIR/priority_zero_summary.md`:
- `Genuinely tagged: True` → proceed to Step 4
- `Genuinely tagged: False` (phantom tree in output) → go to Step 3b with `--force-ocr`

---

### 3b — OCR + ODL (scanned or ODL failure)

```bash
# Standard OCR:
ocrmypdf --output-type pdf originals/<file> work/inputs/<file>
```

Then re-run Step 3a. If the output is still a phantom tree:

```bash
# Force-OCR (strips existing content layer before OCR):
ocrmypdf --force-ocr --output-type pdf originals/<file> work/inputs/<file>
```

Then re-run Step 3a again. If still failing after force-OCR → escalate: open the file in Adobe Acrobat Pro → Tools → Make Accessible, save the result to `work/inputs/<file>`, re-run Step 3a.

---

### 4 — Verify and note BDC

Read the summary. Confirm BDC > 0. Note the count:
- BDC ≥ 200 → strong tagging, expect High or Perfect
- BDC 50–199 → moderate; likely passes but watch the Ally score
- BDC < 50 → weak; OCR-derived structure, flag for close review after upload

---

### 5 — Canonical name

Ask the human for the canonical filename following the convention in `AGENTS.md`:

| File type | Pattern | Example |
|---|---|---|
| Lecture slide | `descriptive_topic.pdf` | `market_failures.pdf` |
| Textbook chapter | `lastname_ch##.pdf` | `weimer_ch08.pdf` |
| Author-year reading | `lastname_year.pdf` | `shields_2017.pdf` |
| Policy document | descriptive | `omb_circular_a94.pdf` |
| Example / exercise | `example_description.pdf` | `example_decision_making.pdf` |

Rules: all lowercase, underscores only, no week prefix (order may change).

---

### 6 — Module folder

If not provided in arguments, list existing `work/canvas_ready/` folders and ask which one. If the target module folder doesn't exist yet, create it:

```bash
mkdir -p "work/canvas_ready/<module_folder>"
```

---

### 7 — Stage

```bash
cp "work/patched/<stem>_tagged_patched.pdf" "work/canvas_ready/<module>/<canonical_name>.pdf"
```

Also copy the new original to `originals/` if it came from outside the workspace.

---

### 8 — Update STATUS.md

Add a row to the appropriate module section:

```
| `<canonical_name>.pdf` | <bdc> | — | — | <note if low BDC> |
```

---

### 9 — Report

Tell the human:

> Staged `<canonical_name>.pdf` → `<module>/`. BDC=<n>. Ready to upload.
> [If BDC < 50: ⚠ Low BDC — watch Ally score. If it scores below High, run Acrobat Make Accessible as a fallback.]
