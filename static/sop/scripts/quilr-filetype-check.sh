#!/usr/bin/env sh
# ============================================================================
# quilr-filetype-check.sh
# Checks that the file types / MIME types the Quilr Endpoint Agent needs
# (.exe .msi .msp .zip .json .toml .xml) are not blocked, stripped, or
# MIME-rewritten by a web filter / SWG / download-control policy.
#
# How it works: downloads a tiny probe file per extension from the Quilr CDN
# and verifies (a) it returns HTTP 200, (b) its content marker is intact
# (a proxy block page would not contain it), and (c) reports the Content-Type.
#
# Usage:
#   curl -fsSL https://quilr-extensions.quilr.ai/Quilr-SOP/EndpointAgent/macOS/quilr-filetype-check.sh | sh
#   sh quilr-filetype-check.sh                 # default base URL
#   sh quilr-filetype-check.sh <base-url>      # override probe base URL
#
# Exit code: 0 = all types OK, 1 = one or more BLOCKED/ALTERED.
#
# Note: this detects extension/MIME-based filtering. A gateway that blocks on
# deep content inspection of real binaries may behave differently for an
# actual PE/MSI than for a probe file.
# ============================================================================

set -u

BASE="${1:-https://quilr-extensions.quilr.ai/Quilr-SOP/EndpointAgent/mime-test}"
MARKER="QUILR-MIME-PROBE-OK"
TMP="${TMPDIR:-/tmp}/quilr_probe.$$"

printf '\nQuilr file-type / MIME allow check\nBase: %s\n' "$BASE"
printf '%s\n' "----------------------------------------------------------------"

FAIL=0
for e in exe msi msp zip json toml xml; do
  url="$BASE/probe.$e"
  meta=$(curl -sS -m 15 -o "$TMP" -w '%{http_code}|%{content_type}' "$url" 2>/dev/null)
  http=${meta%%|*}
  ctype=${meta#*|}
  [ -n "$ctype" ] || ctype="(none)"

  if [ "$http" != "200" ]; then
    status=BLOCKED
    ctype="HTTP ${http:-000}"
  elif ! grep -q "$MARKER" "$TMP" 2>/dev/null; then
    status=ALTERED
  else
    status=OK
  fi

  printf '.%-5s  %-8s  %s\n' "$e" "$status" "$ctype"
  [ "$status" = OK ] || FAIL=1
done

rm -f "$TMP" 2>/dev/null

printf '%s\n' "----------------------------------------------------------------"
if [ "$FAIL" -eq 0 ]; then
  printf 'RESULT: all file types downloadable with intact content.\n\n'
else
  printf 'RESULT: one or more file types BLOCKED or ALTERED - allow them on your SWG / download policy.\n\n'
fi

exit "$FAIL"
