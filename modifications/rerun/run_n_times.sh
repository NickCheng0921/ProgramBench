#!/usr/bin/env bash
# Run run_agent.py N times sequentially with the given args.
#
# Usage:
#   modifications/rerun/run_n_times.sh <N> <instance_id> [run_agent.py args...]
#
# Example:
# time  modifications/rerun/run_n_times.sh 4 arq5x__bedtools2.dd57059 \
#       --model openrouter/deepseek/deepseek-v4-flash \
#       --run-name deepseek_v4_flash --max-tokens 8192
# time  modifications/rerun/run_n_times.sh 5 doxygen__doxygen.966d98e \
#       --model openrouter/deepseek/deepseek-v4-flash \
#       --run-name deepseek_v4_flash --max-tokens 8192

# Wrap in { ... ; exit; } so bash reads the whole script before executing.
# Without this, editing the file mid-run (long jobs!) corrupts bash's parse
# stream and produces phantom syntax errors between iterations.
{
set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <N> <instance_id> [run_agent.py args...]" >&2
    exit 1
fi

N="$1"; shift
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT="$SCRIPT_DIR/run_agent.py"

for i in $(seq 1 "$N"); do
    echo "=========================================="
    echo "  Run $i / $N"
    echo "=========================================="
    python "$AGENT" "$@"
done

exit 0
}
