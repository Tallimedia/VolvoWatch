#!/usr/bin/env bash
# Build the .iq package for a Connect IQ Store upload (beta or public).
#
# Refuses to build if DevConfig.mc still carries a device token — that would
# ship a live credential for the author's car inside a downloadable app.
set -euo pipefail

cd "$(dirname "$0")"

KEY="${CIQ_DEVELOPER_KEY:-$HOME/.garmin-ciq/developer_key.der}"
OUT="bin/volvowatch.iq"
DEV_CONFIG="source/DevConfig.mc"

export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home}"
export PATH="$JAVA_HOME/bin:$HOME/Library/Application Support/Garmin/ConnectIQ/Sdks/current/bin:$PATH"

fail() { printf '\n\033[31mERROR:\033[0m %s\n\n' "$1" >&2; exit 1; }

# --- safety gate -----------------------------------------------------------
leaked=$(grep -E '^\s*const\s+(DEVICE_TOKEN|CAR_LABEL)\s*=\s*"[^"]+"' "$DEV_CONFIG" || true)
leaked+=$(grep -E '^\s*const\s+FAKE_FLAGS\s*=\s*true' "$DEV_CONFIG" || true)
if [ -n "$leaked" ]; then
    fail "$DEV_CONFIG still has values set:
$leaked

A published/beta app must pair through app settings, and a compiled-in device
token would give anyone who installs it control of your car.

Blank them out first:
    const DEVICE_TOKEN = \"\";
    const CAR_LABEL = \"\";"
fi

[ -f "$KEY" ] || fail "developer key not found at $KEY (set CIQ_DEVELOPER_KEY)"

# --- build -----------------------------------------------------------------
mkdir -p bin
rm -f "$OUT"
monkeyc -f monkey.jungle -e -o "$OUT" -y "$KEY" -r -w

printf '\n\033[32mOK\033[0m  %s (%s bytes)\n' "$OUT" "$(wc -c < "$OUT" | tr -d ' ')"
echo "Upload it at https://apps-developer.garmin.com  (the dashboard is NOT on"
echo "apps.garmin.com any more) -> sign in -> upload app -> mark it Beta."
