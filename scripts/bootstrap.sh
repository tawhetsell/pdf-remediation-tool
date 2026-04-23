#!/usr/bin/env bash
# bootstrap.sh — verify prerequisites before any remediation run.
# Run at session start. Nonzero exit = stop and fix; do not proceed.

# set -e : abort on command failure
# set -u : abort on unset variable references (catches typos)
# set -o pipefail : fail pipeline if any stage fails
set -euo pipefail

fail() { echo "[BOOTSTRAP FAIL] $*" >&2; exit 1; }
ok()   { echo "[ok] $*"; }
warn() { echo "[warn] $*" >&2; }

echo "=== Workspace bootstrap ==="

# --- Java 11+ (ODL's Java CLI runtime) ---
# macOS ships a stub /usr/bin/java that satisfies `command -v` but is not a real JDK.
# Always prepend the Homebrew openjdk path when it exists so it wins over the stub.
BREW_JAVA="/opt/homebrew/opt/openjdk/bin"
[ -x "$BREW_JAVA/java" ] && export PATH="$BREW_JAVA:$PATH"
command -v java >/dev/null 2>&1 || fail "java not found. Install JDK 11+: brew install openjdk@17"
# java -version prints to stderr; capture with 2>&1
# Parses '17.0.9' or legacy '1.8.0_...' → normalize to major version
JAVA_MAJOR=$(java -version 2>&1 | awk -F'"' '/version/ {print $2}' | awk -F. '{print ($1=="1") ? $2 : $1}')
[ -n "$JAVA_MAJOR" ] && [ "$JAVA_MAJOR" -ge 11 ] \
    || fail "Java 11+ required, found: $(java -version 2>&1 | head -1)"
ok "Java $JAVA_MAJOR"

# --- Python 3.10+ ---
command -v python3 >/dev/null 2>&1 || fail "python3 not found"
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || fail "Python 3.10+ required, found: $PY_VER"
ok "Python $PY_VER"

# --- Required Python packages ---
for pkg in opendataloader_pdf pypdf; do
    python3 -c "import $pkg" 2>/dev/null \
        || fail "Python package '$pkg' missing. Run: pip install --upgrade opendataloader-pdf pypdf"
done
ok "Python packages: opendataloader-pdf, pypdf"

# --- Optional tools (warn, don't fail) ---
if command -v verapdf >/dev/null 2>&1; then
    ok "veraPDF on PATH (UA-1 validation available)"
else
    warn "veraPDF not on PATH — validation skipped. See https://verapdf.org if needed."
fi

if command -v ocrmypdf >/dev/null 2>&1; then
    ok "ocrmypdf on PATH (scanned-PDF OCR available)"
else
    warn "ocrmypdf not on PATH — scanned-PDF handling will fail if attempted."
fi

# --- Required workspace directories ---
# Refuse to run from wrong CWD. The top-level shape is what the runbook assumes.
for d in originals work scripts docs; do
    [ -d "$d" ] || fail "Expected directory '$d' missing. Run from workspace root, or run setup.sh."
done
ok "Workspace layout correct"

# --- Ensure pipeline subdirectories exist (idempotent) ---
mkdir -p work/inputs work/tagged work/patched work/runs
ok "Work subdirectories ready"

echo "=== Bootstrap complete ==="
