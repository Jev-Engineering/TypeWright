#!/usr/bin/env bash
# CI helper: run `<python> -m pip install <args...>` up to 3 times, 15 s apart.
# Used by .github/workflows/ci.yml so every install step shares one retry policy.
# pip exit codes do not separate network failures from resolver errors, so every
# failure is retried; a deterministic error costs about 30 s before the step fails.
set -euo pipefail
if [ "$#" -lt 2 ]; then
  echo "usage: $0 <python> <pip install args...>" >&2
  exit 2
fi
python_bin="$1"
shift
attempts=3
for attempt in $(seq 1 "$attempts"); do
  if "$python_bin" -m pip install "$@"; then
    exit 0
  fi
  if [ "$attempt" -eq "$attempts" ]; then
    echo "::error::pip install failed after $attempts attempts"
    exit 1
  fi
  echo "::warning::pip install attempt $attempt failed; retrying in 15s"
  sleep 15
done
