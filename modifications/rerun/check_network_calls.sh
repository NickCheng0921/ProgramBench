#!/usr/bin/env bash
# Scan a trajectory.json for bash commands the model tried to run that would
# attempt network egress. Network is supposed to be disabled by --network=none
# at the docker level, but this gives a quick read of what the model *intended*.
#
# Usage:
#   modifications/rerun/check_network_calls.sh <path/to/trajectory.json>
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <trajectory.json>" >&2
    exit 1
fi

TRAJ="$1"
[ -f "$TRAJ" ] || { echo "Not a file: $TRAJ" >&2; exit 1; }

PATTERN='curl|wget|nc |netcat|/dev/tcp|/dev/udp|ssh |scp |sftp|rsync|ftp |git clone|git fetch|git pull|apt(-get)? (install|update|upgrade)|pip[3]? install|npm install|cargo (install|fetch)|go get|go install|brew install|conda install'

HITS=$(jq -r '.messages[]?.tool_calls[]?.function.arguments' "$TRAJ" 2>/dev/null \
       | jq -r '.command // empty' 2>/dev/null \
       | grep -niE "$PATTERN" || true)

if [ -z "$HITS" ]; then
    echo "OK: no network-egress commands found in agent tool calls."
    exit 0
fi

echo "Found $(echo "$HITS" | wc -l) candidate network command(s):"
echo "$HITS"
exit 2
