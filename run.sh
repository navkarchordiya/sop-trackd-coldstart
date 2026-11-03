#!/usr/bin/env bash
# Build the function image and run the benchmark. Everything (commands + output) is saved
# to logs/run-<timestamp>.log. Usage:  ./run.sh            (50 trials per condition)
#                                      TRIALS=20 ./run.sh  (quicker)
set -euo pipefail
cd "$(dirname "$0")"
TRIALS="${TRIALS:-50}"
mkdir -p logs
LOG_FILE="logs/run-$(date '+%Y%m%d-%H%M%S').log"
exec > >(tee "$LOG_FILE") 2>&1

echo "=== started $(date '+%Y-%m-%d %H:%M:%S %Z') | seed 6 (BITS ID f20231006) ==="
echo; echo "\$ docker version --format '{{.Server.Version}}'"; docker version --format '{{.Server.Version}}'
echo; echo "\$ python3 --version"; python3 --version
echo; echo "\$ docker build -t coldstart-fn:1.0 function"; docker build -t coldstart-fn:1.0 function
echo; echo "\$ python3 bench.py --trials $TRIALS"; python3 bench.py --trials "$TRIALS"
echo "=== finished $(date '+%H:%M:%S') | log: $LOG_FILE ==="
