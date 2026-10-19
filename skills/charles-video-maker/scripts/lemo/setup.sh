#!/bin/sh
# Lemo-Opuscar style library (MIT, https://github.com/lemomo-ai/lemo-opuscar): find it or download it, then hand
# the rest of the arguments to the library's own setup.sh, which keeps it updated and installs its packages.
#   sh setup.sh                      library ready? prints LIB=<path> on the last line
#   sh setup.sh deps [voice] [music] core tools (readcheck, sampler) / Kokoro voice / plucked strings
# LEMO_OPUSCAR_HOME = where the library lives (default ~/lemo-opuscar).
set -e
LIB=${LEMO_OPUSCAR_HOME:-$HOME/lemo-opuscar}
INNER=plugin/skills/lemo-opuscar/scripts/setup.sh
if [ ! -f "$LIB/$INNER" ]; then
  [ -e "$LIB" ] && [ -n "$(ls -A "$LIB" 2>/dev/null)" ] && { echo "✗ $LIB exists but is not the Lemo-Opuscar library. Set LEMO_OPUSCAR_HOME to another folder."; exit 1; }
  command -v git >/dev/null || { echo "✗ git is needed to download the library"; exit 1; }
  echo "↓ downloading the style library into $LIB"
  # bootstrap with only the setup script; marked as managed, the library's setup.sh then syncs main and sets its own sparse rules
  git clone --quiet --depth 1 --filter=blob:none --sparse --branch main https://github.com/lemomo-ai/lemo-opuscar.git "$LIB"
  git -C "$LIB" sparse-checkout set --no-cone '/plugin/'
  git -C "$LIB" config lemo.managed true
fi
LEMO_OPUSCAR_HOME=$LIB exec sh "$LIB/$INNER" "$@"
