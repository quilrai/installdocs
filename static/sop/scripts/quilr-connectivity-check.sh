#!/usr/bin/env sh
# ============================================================================
# quilr-connectivity-check.sh
# Tests outbound TCP/443 reachability to the Quilr backplane hosts that the
# Quilr Endpoint Agent needs, for a given tenant environment.
#
# Usage:
#   curl -fsSL https://quilr-extensions.quilr.ai/Quilr-SOP/EndpointAgent/macOS/quilr-connectivity-check.sh | sh             # defaults to: us
#   curl -fsSL https://quilr-extensions.quilr.ai/Quilr-SOP/EndpointAgent/macOS/quilr-connectivity-check.sh | sh -s -- usa   # pick an environment
#   sh quilr-connectivity-check.sh japan
#
#   <env> = us (default) | usa | japan | india
#
# Exit code: 0 = every host reachable, 1 = one or more BLOCKED, 2 = bad usage.
# A BLOCKED host must be unblocked AND added to the SSL-bypass / no-decrypt
# list on any TLS-intercepting proxy before installing the agent.
# ============================================================================

set -u

ENVNAME="${1:-us}"
PORT=443
TIMEOUT=5

SHARED="discover.quilrai.dev log.quilrai.dev quilr-extensions.quilr.ai"

case "$ENVNAME" in
  us|US|default)
    LABEL="quilr-saas (US default)"
    HOSTS="$SHARED app.quilr.ai dlpone.quilr.ai" ;;
  usa|usa-prod|usaprod)
    LABEL="quilr-saas-usa-prod"
    HOSTS="$SHARED quilr-extensions.quilrai.com app.quilrai.com dlpone.quilrai.com" ;;
  japan|jp)
    LABEL="quilr-saas-japan"
    HOSTS="$SHARED app-jp.quilr.ai dlpone-jp-1.quilr.ai" ;;
  india|ind|ind-prod)
    LABEL="quilr-saas-ind-prod (India)"
    HOSTS="$SHARED quilr-extensions.quilrai.com platform.quilrai.com dlp-platform.quilrai.com" ;;
  *)
    echo "Unknown environment: '$ENVNAME'"
    echo "Use one of: us | usa | japan | india"
    exit 2 ;;
esac

printf '\nQuilr connectivity check  -  %s\n' "$LABEL"
printf '%s\n' "------------------------------------------------------------"

FAIL=0

probe() {
  _h="$1"
  if command -v nc >/dev/null 2>&1; then
    # macOS nc uses -G (connect timeout); most Linux nc uses -w. Try both.
    if nc -z -G "$TIMEOUT" "$_h" "$PORT" >/dev/null 2>&1 \
       || nc -z -w "$TIMEOUT" "$_h" "$PORT" >/dev/null 2>&1; then
      _status=OK
    else
      _status=BLOCKED
    fi
  else
    # Fallback: bash/ksh /dev/tcp pseudo-device
    if (exec 3<>"/dev/tcp/$_h/$PORT") 2>/dev/null; then
      _status=OK
      exec 3>&- 2>/dev/null
    else
      _status=BLOCKED
    fi
  fi
  printf '%-34s  TCP/%s  %s\n' "$_h" "$PORT" "$_status"
  [ "$_status" = OK ] || FAIL=1
}

for h in $HOSTS; do
  probe "$h"
done

printf '%s\n' "------------------------------------------------------------"
if [ "$FAIL" -eq 0 ]; then
  printf 'RESULT: all hosts reachable on TCP/%s.\n\n' "$PORT"
else
  printf 'RESULT: one or more hosts BLOCKED - unblock and SSL-bypass them before installing.\n\n'
fi

exit "$FAIL"
