#!/usr/bin/env bash
# INC-01: an upstream system drops a corrupt (non-JSON) claim file.
set -euo pipefail
# Explicit --endpoint-url keeps older CLIs from bypassing the emulator.
aws_l() { aws --endpoint-url "${AWS_ENDPOINT_URL:?run: source scripts/env.sh}" "$@"; }
ID="CLM-CORRUPT01"
KEY="incoming/$ID.json"
printf '{"claim_id": "%s", "member_id": "MBR-123456", "amount": 120.5,' "$ID" > /tmp/$ID.json  # truncated on purpose
aws_l s3 cp /tmp/$ID.json "s3://claims-incoming/$KEY" >/dev/null
QURL=$(aws_l sqs get-queue-url --queue-name claims-queue --query QueueUrl --output text)
aws_l sqs send-message --queue-url "$QURL" \
  --message-body "{\"claim_id\":\"$ID\",\"bucket\":\"claims-incoming\",\"key\":\"$KEY\"}" >/dev/null
echo "INC-01 injected. Ticket: 'Claim $ID stuck, member says it was submitted.'"
echo "Run the worker, then follow RUNBOOK.md section INC-01."
