#!/usr/bin/env bash
# INC-03: the worker was down overnight and the queue piled up.
# Make sure the worker is NOT running before you inject this.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m app.producer --count "${1:-150}" --bad 5 >/dev/null
echo "INC-03 injected. Ticket: 'Claims submitted since last night are not processed.'"
python -m app.status --summary
echo "Follow RUNBOOK.md section INC-03."
