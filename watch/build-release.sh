#!/usr/bin/env bash
# Build the .iq package for a Connect IQ Store upload (beta or public), and
# promote it into the repo-root dist/ folder (tracked in git, same layout as
# every other app's repo — see claude-docs root CLAUDE.md "Release artifacts"
# convention). Whatever .iq was previously in dist/ moves to dist/archive/
# first, so dist/ always holds exactly the current version and nothing is
# ever silently overwritten.
#
# Output name always carries the version, derived from AppVersion in
# strings.xml — never a bare "volvowatch.iq" that gives no way to tell a
# current build from a stale one.
#
# Refuses to build if DevConfig.mc still carries a device token — that would
# ship a live credential for the author's car inside a downloadable app.
set -euo pipefail

cd "$(dirname "$0")"

KEY="${CIQ_DEVELOPER_KEY:-$HOME/.garmin-ciq/developer_key.der}"
DEV_CONFIG="source/DevConfig.mc"
STRINGS="resources/strings/strings.xml"
DIST="../dist"

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

VERSION=$(grep -oE '<string id="AppVersion">[^<]+' "$STRINGS" | cut -d'>' -f2)
[ -n "$VERSION" ] || fail "no AppVersion found in $STRINGS"
OUT="bin/VolvoWatch-v${VERSION}.iq"

# --- build -----------------------------------------------------------------
mkdir -p bin
rm -f "$OUT"
monkeyc -f monkey.jungle -e -o "$OUT" -y "$KEY" -r -w

printf '\n\033[32mOK\033[0m  %s (%s bytes)\n' "$OUT" "$(wc -c < "$OUT" | tr -d ' ')"

# --- promote into dist/ (tracked, archive whatever was there before) ------
mkdir -p "$DIST/archive"
for old in "$DIST"/VolvoWatch-v*.iq; do
    [ -e "$old" ] && mv "$old" "$DIST/archive/"
done
cp "$OUT" "$DIST/"

printf '\033[32mOK\033[0m  %s/VolvoWatch-v%s.iq\n' "$DIST" "$VERSION"
echo "Upload it at https://apps-developer.garmin.com  (the dashboard is NOT on"
echo "apps.garmin.com any more) -> sign in -> upload app -> mark it Beta."
