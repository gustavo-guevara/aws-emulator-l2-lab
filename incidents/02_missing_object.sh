#!/usr/bin/env bash
# INC-02: the message arrives but the file was never uploaded (or was deleted).
set -euo pipefail
# Explicit --endpoint-url keeps older CLIs from bypassing the emulator.
aws_l() { aws --endpoint-url "${AWS_ENDPOINT_URL:?run: source scripts/env.sh}" "$@"; }
ID="CLM-MISSING01"
QURL=$(aws_l sqs get-queue-url --queue-name claims-queue --query QueueUrl --output text)
aws_l sqs send-message --queue-url "$QURL" \
  --message-body "{\"claim_id\":\"$ID\",\"bucket\":\"claims-incoming\",\"key\":\"incoming/$ID.json\"}" >/dev/null
echo "INC-02 injected. Ticket: 'Claim $ID shows ERROR in the portal.'"
echo "Run the worker, then follow RUNBOOK.md section INC-02."
