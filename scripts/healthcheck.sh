#!/usr/bin/env bash
# First thing to run during an incident: is each piece of the pipeline alive?
# Exit code 0 = healthy, 1 = something is down (usable from cron or CI).
set -uo pipefail
# Explicit --endpoint-url keeps older CLIs from bypassing the emulator.
aws_l() { aws --endpoint-url "${AWS_ENDPOINT_URL:?run: source scripts/env.sh}" "$@"; }

FAIL=0
ok()   { printf "  [ OK ] %s\n" "$1"; }
bad()  { printf "  [FAIL] %s\n" "$1"; FAIL=1; }

echo "Endpoint: ${AWS_ENDPOINT_URL:-<not set>}"
if [ -z "${AWS_ENDPOINT_URL:-}" ]; then
  bad "AWS_ENDPOINT_URL not set (run: source scripts/env.sh)"; exit 1
fi

echo "1) Emulator reachable"
if aws_l sts get-caller-identity >/dev/null 2>&1; then ok "sts get-caller-identity"
else bad "emulator not responding (is 'aws-emulator' running?)"; exit 1; fi

echo "2) S3 buckets"
for b in claims-incoming claims-processed; do
  aws_l s3api head-bucket --bucket "$b" >/dev/null 2>&1 && ok "$b" || bad "$b missing (run: python -m app.setup_resources)"
done

echo "3) SQS queues"
for q in claims-queue claims-dlq; do
  url=$(aws_l sqs get-queue-url --queue-name "$q" --query QueueUrl --output text 2>/dev/null)
  if [ -n "$url" ]; then
    n=$(aws_l sqs get-queue-attributes --queue-url "$url" \
          --attribute-names ApproximateNumberOfMessages \
          --query 'Attributes.ApproximateNumberOfMessages' --output text)
    ok "$q (waiting=$n)"
    if [ "$q" = "claims-dlq" ] && [ "${n:-0}" -gt 0 ]; then
      printf "  [WARN] %s messages in DLQ -> python -m app.status --dlq\n" "$n"
    fi
  else
    bad "$q missing"
  fi
done

echo "4) DynamoDB table"
aws_l dynamodb describe-table --table-name claims-status >/dev/null 2>&1 && ok "claims-status" || bad "claims-status missing"

echo
[ $FAIL -eq 0 ] && echo "HEALTHY" || echo "UNHEALTHY"
exit $FAIL
