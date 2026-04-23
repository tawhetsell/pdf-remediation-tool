#!/usr/bin/env bash
# setup.sh — create workspace directory structure (run once on first use)
set -euo pipefail

mkdir -p \
  originals \
  work/inputs \
  work/tagged \
  work/patched \
  work/canvas_ready \
  work/runs

# Gitkeep placeholders so empty dirs are tracked
touch originals/.gitkeep \
      work/inputs/.gitkeep \
      work/tagged/.gitkeep \
      work/patched/.gitkeep \
      work/canvas_ready/.gitkeep \
      work/runs/.gitkeep

echo "Workspace ready. Next: bash scripts/bootstrap.sh"
