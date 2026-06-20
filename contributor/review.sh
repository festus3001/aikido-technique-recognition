#!/usr/bin/env bash
# Launch the teacher review tool: ensure the env exists, install the package if needed,
# start the local server, and open the browser. Any flags are forwarded to atr-review
# (e.g. --reviewer person:slug --reviewer-name "Name" --port 8000).
#
#   contributor/review.sh --reviewer person:morihiro-saito-lineage-teacher --reviewer-name "Sensei"
#
# Set REVIEW_NO_OPEN=1 to skip opening the browser.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
ENV="atr-contributor"

# -- locate conda --------------------------------------------------------------
if ! command -v conda >/dev/null 2>&1; then
  for base in "$HOME/miniconda3" "$HOME/miniforge3" "$HOME/anaconda3" \
              "/opt/homebrew/Caskroom/miniforge/base" "/opt/conda"; do
    if [ -f "$base/etc/profile.d/conda.sh" ]; then
      # shellcheck disable=SC1091
      source "$base/etc/profile.d/conda.sh"; break
    fi
  done
fi
command -v conda >/dev/null 2>&1 || { echo "error: conda not found on PATH." >&2; exit 1; }

# -- ensure env + package ------------------------------------------------------
if ! conda env list | awk '{print $1}' | grep -qx "$ENV"; then
  echo "Creating conda env '$ENV' (first run, this takes a minute)..."
  conda env create -f "$REPO/contributor/environment.yml"
fi
if ! conda run -n "$ENV" python -c "import atr_contributor" >/dev/null 2>&1; then
  echo "Installing the contributor package..."
  conda run -n "$ENV" pip install -e "$REPO/contributor"
fi

# -- figure out the port (default 8000), scanning forwarded args ---------------
HOST="127.0.0.1"; PORT="8000"; prev=""
for a in "$@"; do
  [ "$prev" = "--port" ] && PORT="$a"
  [ "$prev" = "--host" ] && HOST="$a"
  prev="$a"
done
URL="http://${HOST}:${PORT}/"

# -- open the browser once the server answers ----------------------------------
if [ "${REVIEW_NO_OPEN:-0}" != "1" ]; then
  (
    for _ in $(seq 1 60); do
      curl -fs "http://${HOST}:${PORT}/healthz" >/dev/null 2>&1 && break
      sleep 0.5
    done
    if command -v open >/dev/null 2>&1; then open "$URL"
    elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
    else echo "Open this in your browser: $URL"; fi
  ) &
fi

echo "Review tool: $URL   (Ctrl-C to stop)"
exec conda run -n "$ENV" atr-review "$@"
