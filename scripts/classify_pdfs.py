#!/usr/bin/env python3
"""
classify_pdfs.py
================
Classify one or more PDFs for the accessibility pipeline.

Output classes:
  tagged              — genuine Tagged PDF (StructTreeRoot + BDC/EMC > 0)
  phantom_tree        — has StructTreeRoot but zero BDC operators (shell only)
  born_digital_untagged — has extractable text, no structure tree
  scanned             — no extractable text (image-only or OCR not yet applied)

Usage:
  python3 classify_pdfs.py file.pdf
  python3 classify_pdfs.py originals/          # classify all PDFs in a folder
"""
from __future__ import annotations
import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("ERROR: pypdf not installed. Run: pip install --upgrade pypdf")


def classify(path: Path) -> dict:
    try:
        r = PdfReader(str(path))
        root = r.trailer["/Root"]
        has_tree = "/StructTreeRoot" in root

        bdc = 0
        for page in r.pages:
            try:
                data = page.get_contents()
                if data:
                    bdc += data.get_data().count(b"BDC")
            except Exception:
                continue

        try:
            text = r.pages[0].extract_text() or ""
            has_text = len(text.strip()) > 50
        except Exception:
            has_text = False

        if has_tree and bdc > 0:
            cls = "tagged"
        elif has_tree and bdc == 0:
            cls = "phantom_tree"
        elif not has_text:
            cls = "scanned"
        else:
            cls = "born_digital_untagged"

        return {
            "file": path.name,
            "class": cls,
            "pages": len(r.pages),
            "has_tree": has_tree,
            "bdc": bdc,
            "has_text": has_text,
            "error": None,
        }
    except Exception as e:
        return {"file": path.name, "class": "error", "error": str(e),
                "pages": 0, "has_tree": False, "bdc": 0, "has_text": False}


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = Path(sys.argv[1])
    paths = sorted(target.glob("*.pdf")) if target.is_dir() else [target]

    if not paths:
        print(f"No PDFs found at {target}", file=sys.stderr)
        sys.exit(1)

    fmt = "{class:<25} bdc={bdc:<6} pages={pages:<4} text={has_text}  {file}"
    for path in paths:
        result = classify(path)
        print(fmt.format(**result))


if __name__ == "__main__":
    main()
