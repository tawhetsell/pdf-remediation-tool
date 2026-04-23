#!/usr/bin/env python3
"""
run_priority_zero.py
====================
Execute Priority 0 from UNIFIED_ACCESSIBILITY_HANDOFF_v2.md.

Goal: prove that the ODL-seeded path (Variant B) produces a tagged PDF
equivalent-or-better than the v1 Acrobat-seeded path (Variant A) on the
two v1 positive controls, without requiring Adobe Acrobat.

What it does per input PDF:
  1. Run opendataloader-pdf auto-tag -> <stem>_tagged.pdf
  2. Verify the output is a GENUINE Tagged PDF
     (StructTreeRoot + marked-content operators in page streams)
  3. Apply catalog-level accessibility patch
     (/MarkInfo, /Lang, /Title) via patch_catalog_accessibility
  4. Optionally invoke the existing bookmark/figure-alt patcher if available
  5. Optionally run veraPDF if available on PATH
  6. Emit a per-file JSON report + a combined markdown summary

Exit codes:
  0 — every input produced a verifiable tagged PDF with catalog patches
  1 — at least one input failed structural verification (critical)
  2 — every input verified but no comparison data could be gathered

Usage:
  # Default targets: Week_9_Causal_Inference.pdf, Week_12_BCA.pdf
  python run_priority_zero.py \\
      --materials course_materials_updated/course_materials \\
      --out       course_materials_updated/remediated_pdfs \\
      --reports   course_materials_updated/reports/priority_zero

  # Override targets
  python run_priority_zero.py --targets Week_9_Causal_Inference.pdf Week_12_BCA.pdf \\
      --materials ... --out ... --reports ...

Prerequisites:
  pip install --upgrade opendataloader-pdf pypdf
  java -version   # must be 11+
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

try:
    import opendataloader_pdf as odl     # ODL Python wrapper
except ImportError:
    sys.stderr.write("ERROR: opendataloader-pdf not installed. "
                     "Run: pip install --upgrade opendataloader-pdf\n")
    sys.exit(3)

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.stderr.write("ERROR: pypdf not installed. "
                     "Run: pip install --upgrade pypdf\n")
    sys.exit(3)

# Local import — live in the same directory as this script
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from patch_catalog_accessibility import patch_catalog  # noqa: E402


DEFAULT_TARGETS = ["Week_9_Causal_Inference.pdf", "Week_12_BCA.pdf"]


# ---------- structural verification ----------

@dataclass
class VerifyResult:
    """What a PDF looks like to the accessibility pipeline."""
    has_struct_tree: bool = False           # /StructTreeRoot in /Root
    has_mark_info: bool = False             # /MarkInfo << /Marked true >>
    has_lang: bool = False
    has_title: bool = False                 # non-placeholder title
    title_value: Optional[str] = None
    lang_value: Optional[str] = None
    bdc_count: int = 0                      # total marked-content opens
    emc_count: int = 0                      # total marked-content closes
    page_count: int = 0
    struct_root_kids: int = 0               # crude size of the struct tree
    error: Optional[str] = None

    @property
    def is_genuinely_tagged(self) -> bool:
        """
        A PDF is *genuinely* tagged only if both conditions hold:
          - the catalog points to a /StructTreeRoot
          - at least one page has BDC/EMC marked-content operators
        A StructTreeRoot with zero BDC/EMC is a phantom tree — common in
        some faulty tagging tools — and does not help screen readers.
        """
        return self.has_struct_tree and self.bdc_count > 0 and self.emc_count > 0


def verify_pdf(path: Path) -> VerifyResult:
    r = VerifyResult()
    try:
        reader = PdfReader(str(path))
        root = reader.trailer["/Root"]
        r.page_count = len(reader.pages)

        r.has_struct_tree = "/StructTreeRoot" in root
        if r.has_struct_tree:
            tree = root["/StructTreeRoot"]
            k = tree.get("/K")
            # /K can be a single node, an array, or absent
            if k is None:
                r.struct_root_kids = 0
            elif hasattr(k, "__len__") and not isinstance(k, (str, bytes)):
                r.struct_root_kids = len(k)
            else:
                r.struct_root_kids = 1

        if "/MarkInfo" in root:
            mi = root["/MarkInfo"]
            r.has_mark_info = bool(mi.get("/Marked", False))
        if "/Lang" in root:
            r.lang_value = str(root["/Lang"])
            r.has_lang = True

        meta = reader.metadata or {}
        title = meta.get("/Title")
        if title:
            r.title_value = str(title)
            placeholder = str(title).strip().lower() in {"untitled", "none", "document", "pdf", ""}
            r.has_title = not placeholder

        # Count BDC/EMC across every page — tagged PDFs should have many
        for page in reader.pages:
            try:
                data = page.get_contents()
                if data is None:
                    continue
                blob = data.get_data()
                r.bdc_count += blob.count(b"BDC")
                r.emc_count += blob.count(b"EMC")
            except Exception:
                # Some pages have no content stream; that's fine
                continue
    except Exception as e:
        r.error = f"{type(e).__name__}: {e}"
    return r


# ---------- per-file pipeline ----------

@dataclass
class FileResult:
    source: str
    tagged_pdf: Optional[str] = None
    patched_pdf: Optional[str] = None
    verify_before_patch: Optional[dict] = None
    verify_after_patch: Optional[dict] = None
    catalog_changes: Optional[dict] = None
    verapdf_ran: bool = False
    verapdf_exit_code: Optional[int] = None
    verapdf_report_path: Optional[str] = None
    pipeline_patcher_ran: bool = False
    pipeline_patcher_exit_code: Optional[int] = None
    notes: list = field(default_factory=list)


def derive_title(pdf_path: Path) -> str:
    """Turn Week_9_Causal_Inference.pdf into 'Week 9 Causal Inference'."""
    return pdf_path.stem.replace("_", " ").strip()


def run_odl(input_pdf: Path, out_dir: Path) -> Path:
    """
    Call opendataloader-pdf with format=tagged-pdf. ODL writes
    <stem>_tagged.pdf into out_dir. Returns that path.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    odl.convert(
        input_path=str(input_pdf),
        output_dir=str(out_dir),
        format="tagged-pdf",      # the magic: gives us a real /StructTreeRoot
        quiet=True,
    )
    return out_dir / f"{input_pdf.stem}_tagged.pdf"


def apply_catalog_patch(tagged_pdf: Path, patched_pdf: Path,
                        title: str, lang: str = "en-US") -> dict:
    reader = PdfReader(str(tagged_pdf))
    writer = PdfWriter(clone_from=reader)    # clone_from preserves StructTreeRoot
    changed = patch_catalog(reader, writer, lang=lang, title=title)
    with open(patched_pdf, "wb") as f:
        writer.write(f)
    return changed


def maybe_run_pipeline_patcher(patched_pdf: Path, scripts_dir: Path) -> tuple[bool, Optional[int]]:
    """
    If the repo's existing patch_tagged_pdf_accessibility.py is present,
    invoke it in a best-effort way. We don't know its exact CLI, so we
    try two common shapes and give up gracefully otherwise.
    """
    script = scripts_dir / "patch_tagged_pdf_accessibility.py"
    if not script.exists():
        return False, None

    # Shape 1: positional IN OUT (most common)
    out = patched_pdf.with_name(patched_pdf.stem + "_patch1.pdf")
    attempts = [
        [sys.executable, str(script), str(patched_pdf), str(out)],
        [sys.executable, str(script), "--input", str(patched_pdf), "--output", str(out)],
    ]
    for cmd in attempts:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and out.exists():
                return True, 0
        except Exception:
            continue
    return True, 99   # attempted but failed; caller can inspect


def maybe_run_verapdf(pdf: Path, report_dir: Path) -> tuple[bool, Optional[int], Optional[Path]]:
    """If verapdf is on PATH, run a UA-1 check and save the XML report."""
    if not shutil.which("verapdf"):
        return False, None, None
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f"{pdf.stem}.verapdf.xml"
    try:
        # --flavour ua1: check against PDF/UA-1
        # --format xml: machine-readable report for downstream diffing
        result = subprocess.run(
            ["verapdf", "--flavour", "ua1", "--format", "xml", str(pdf)],
            capture_output=True, text=True, timeout=180,
        )
        report.write_text(result.stdout)
        return True, result.returncode, report
    except Exception:
        return True, 99, None


# ---------- main pipeline ----------

def process_file(src: Path, out_dir: Path, report_dir: Path,
                 scripts_dir: Path, tagged_dir: Optional[Path] = None) -> FileResult:
    fr = FileResult(source=str(src))

    # Step 1: ODL auto-tag — write to tagged_dir if provided, else out_dir
    odl_dest = tagged_dir if tagged_dir else out_dir
    try:
        tagged = run_odl(src, odl_dest)
    except Exception as e:
        fr.notes.append(f"ODL failed: {type(e).__name__}: {e}")
        return fr
    fr.tagged_pdf = str(tagged)

    # Step 2: verify the ODL output is genuinely tagged (the critical gate)
    v_before = verify_pdf(tagged)
    fr.verify_before_patch = asdict(v_before)
    if not v_before.is_genuinely_tagged:
        fr.notes.append(
            "ODL output is not genuinely tagged "
            f"(StructTree={v_before.has_struct_tree}, "
            f"BDC={v_before.bdc_count}, EMC={v_before.emc_count}). "
            "Do NOT proceed with this file — escalate via fallback ladder."
        )
        return fr

    # Step 3: catalog patch (MarkInfo/Lang/Title) — always written to out_dir
    patched = out_dir / f"{src.stem}_tagged_patched.pdf"
    try:
        fr.catalog_changes = apply_catalog_patch(tagged, patched, title=derive_title(src))
        fr.patched_pdf = str(patched)
    except Exception as e:
        fr.notes.append(f"Catalog patch failed: {type(e).__name__}: {e}")
        return fr

    # Step 4: verify post-patch
    v_after = verify_pdf(patched)
    fr.verify_after_patch = asdict(v_after)

    # Step 5: optional — run the existing bookmark/figure-alt patcher
    ran, rc = maybe_run_pipeline_patcher(patched, scripts_dir)
    fr.pipeline_patcher_ran = ran
    fr.pipeline_patcher_exit_code = rc
    if ran and rc != 0:
        fr.notes.append(
            f"patch_tagged_pdf_accessibility.py returned {rc}; "
            "its CLI shape may differ from what run_priority_zero.py assumes. "
            "Invoke it manually with the correct args."
        )

    # Step 6: optional — veraPDF
    vran, vrc, vpath = maybe_run_verapdf(patched, report_dir)
    fr.verapdf_ran = vran
    fr.verapdf_exit_code = vrc
    fr.verapdf_report_path = str(vpath) if vpath else None

    return fr


def write_markdown_summary(results: list[FileResult], out: Path) -> None:
    lines = ["# Priority 0 — ODL Variant B verification", ""]
    lines.append(f"Files processed: `{len(results)}`")
    genuine = sum(1 for r in results
                  if r.verify_before_patch
                  and r.verify_before_patch.get("has_struct_tree")
                  and r.verify_before_patch.get("bdc_count", 0) > 0)
    lines.append(f"Genuinely tagged by ODL: `{genuine}` / `{len(results)}`")
    lines.append("")

    for r in results:
        src = Path(r.source).name
        lines.append(f"## `{src}`")
        lines.append("")
        if r.verify_before_patch:
            vb = r.verify_before_patch
            lines.append(f"- Pages: `{vb['page_count']}`")
            lines.append(f"- StructTreeRoot: `{vb['has_struct_tree']}` "
                         f"(top-level kids: `{vb['struct_root_kids']}`)")
            lines.append(f"- Marked content: BDC=`{vb['bdc_count']}` EMC=`{vb['emc_count']}`")
            lines.append(f"- Genuinely tagged: `{vb['has_struct_tree'] and vb['bdc_count'] > 0}`")
        if r.catalog_changes:
            keys = ", ".join(r.catalog_changes.keys()) or "none"
            lines.append(f"- Catalog patch added: {keys}")
        if r.verify_after_patch:
            va = r.verify_after_patch
            lines.append(f"- After patch — MarkInfo: `{va['has_mark_info']}`, "
                         f"Lang: `{va['lang_value']}`, Title: `{va['title_value']}`")
        if r.verapdf_ran:
            lines.append(f"- veraPDF UA-1 exit: `{r.verapdf_exit_code}` "
                         f"(report: `{r.verapdf_report_path}`)")
        else:
            lines.append("- veraPDF: not run (binary not on PATH)")
        if r.pipeline_patcher_ran:
            lines.append(f"- Repo patcher exit: `{r.pipeline_patcher_exit_code}`")
        for note in r.notes:
            lines.append(f"- NOTE: {note}")
        lines.append("")

    lines.append("## Next step")
    lines.append("")
    lines.append("Upload each `*_tagged_patched*.pdf` to Canvas and record the Ally score. "
                 "Compare against the v1 Acrobat-seeded results for the same files.")
    out.write_text("\n".join(lines))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--materials", type=Path, required=True,
                   help="Directory containing the source PDFs")
    p.add_argument("--out", type=Path, required=True,
                   help="Directory for patched output PDFs (work/patched/)")
    p.add_argument("--tagged-dir", type=Path, default=None,
                   help="Directory for raw ODL-tagged PDFs (work/tagged/); "
                        "if omitted, tagged files go to --out alongside patched files")
    p.add_argument("--reports", type=Path, required=True,
                   help="Directory for per-file JSON and markdown summary")
    p.add_argument("--scripts", type=Path, default=Path("scripts"),
                   help="Repo scripts directory (for patch_tagged_pdf_accessibility.py)")
    p.add_argument("--targets", nargs="+", default=DEFAULT_TARGETS,
                   help=f"PDF filenames to process (default: {DEFAULT_TARGETS})")
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    args.reports.mkdir(parents=True, exist_ok=True)
    if args.tagged_dir:
        args.tagged_dir.mkdir(parents=True, exist_ok=True)

    results: list[FileResult] = []
    all_genuine = True
    for name in args.targets:
        src = args.materials / name
        if not src.exists():
            print(f"SKIP: {src} does not exist", file=sys.stderr)
            continue
        print(f"→ {name}", file=sys.stderr)
        fr = process_file(src, args.out, args.reports, args.scripts,
                          tagged_dir=args.tagged_dir)

        # Per-file JSON report
        (args.reports / f"{src.stem}.priority_zero.json").write_text(
            json.dumps(asdict(fr), indent=2, default=str)
        )
        results.append(fr)

        if not (fr.verify_before_patch
                and fr.verify_before_patch.get("has_struct_tree")
                and fr.verify_before_patch.get("bdc_count", 0) > 0):
            all_genuine = False

    write_markdown_summary(results, args.reports / "priority_zero_summary.md")

    if not results:
        return 2
    return 0 if all_genuine else 1


if __name__ == "__main__":
    sys.exit(main())
