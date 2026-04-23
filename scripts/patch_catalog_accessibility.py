"""
patch_catalog_accessibility.py
==============================
Three catalog-level accessibility writes that every tagged PDF needs:
  /MarkInfo << /Marked true >>   — declares the doc as tagged
  /Lang "en-US"                  — document language for screen readers
  /Title "<string>"              — document title in info dict

These are the gaps observed in ODL v2.3.0 output on 2026-04-22. Safe to run
against Acrobat-seeded or Adobe-API-seeded outputs too — it's idempotent:
missing keys are added, existing keys are left alone.

Designed to slot into `scripts/patch_tagged_pdf_accessibility.py` as a
pre-step before the bookmark and figure-alt passes. All three writes happen
on the writer's catalog, so they do not touch the struct tree.

Usage (as a module):
    from patch_catalog_accessibility import patch_catalog
    patch_catalog(reader, writer, lang="en-US", title="Week 9 Causal Inference")

Usage (as a CLI, for quick testing):
    python patch_catalog_accessibility.py input_tagged.pdf output_patched.pdf \\
        --lang en-US --title "Week 9 Causal Inference"
"""
from __future__ import annotations
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, TextStringObject, DictionaryObject


def patch_catalog(reader: PdfReader, writer: PdfWriter,
                  lang: str = "en-US",
                  title: str | None = None) -> dict:
    """
    Add /MarkInfo, /Lang, /Title to the writer's catalog if missing.

    Returns a dict of what was actually changed (useful for reporting).
    Does not touch /StructTreeRoot or page content streams.
    """
    root = writer.root_object          # pypdf 5.x: the /Root (catalog) dict
    changed = {}

    # /MarkInfo declares the doc as "really tagged" — some validators refuse
    # to trust a /StructTreeRoot without it.
    if "/MarkInfo" not in root:
        root[NameObject("/MarkInfo")] = DictionaryObject({
            NameObject("/Marked"): BooleanObject(True),
        })
        changed["/MarkInfo"] = {"/Marked": True}

    # /Lang is WCAG 3.1.1; most screen readers fall back to system locale without it.
    if "/Lang" not in root:
        root[NameObject("/Lang")] = TextStringObject(lang)
        changed["/Lang"] = lang

    # /Title goes in the DocInfo dict, not the catalog. add_metadata handles that.
    # Overwrite when existing title is absent OR is a common placeholder —
    # many PDFs carry junk like "untitled" or "Microsoft Word - foo.docx"
    # that hurts screen-reader UX and Ally scoring.
    existing = (reader.metadata or {}).get("/Title", "") if reader.metadata else ""
    placeholder = (
        not existing
        or str(existing).strip().lower() in {"untitled", "none", "document", "pdf"}
        or str(existing).strip().lower().startswith("microsoft word - ")
        or str(existing).strip().lower().startswith("microsoft powerpoint - ")
    )
    if title and placeholder:
        writer.add_metadata({"/Title": title})
        changed["/Title"] = title

    return changed


def _cli() -> None:
    import argparse, json, sys
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("input", type=Path, help="Input (already-tagged) PDF")
    p.add_argument("output", type=Path, help="Output patched PDF")
    p.add_argument("--lang", default="en-US",
                   help="BCP-47 language tag (default: en-US)")
    p.add_argument("--title", default=None,
                   help="Document title; if omitted, derived from filename stem")
    args = p.parse_args()

    # Derive a sensible title if none was provided — filename stem with
    # underscores replaced by spaces reads better for screen readers.
    title = args.title or args.input.stem.replace("_", " ").strip()

    reader = PdfReader(str(args.input))
    writer = PdfWriter(clone_from=reader)   # clone_from preserves StructTreeRoot
    changed = patch_catalog(reader, writer, lang=args.lang, title=title)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "wb") as f:
        writer.write(f)

    json.dump({"output": str(args.output), "changed": changed},
              sys.stdout, indent=2, default=str)
    print()


if __name__ == "__main__":
    _cli()
