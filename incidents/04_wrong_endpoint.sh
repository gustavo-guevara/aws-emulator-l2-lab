#!/usr/bin/env bash
# INC-04: someone runs the job in a shell that is not configured for the lab.
# The app must refuse to talk to real AWS. Runs in a subshell so your session is untouched.
cd "$(dirname "$0")/.."
echo "--- Case A: AWS_ENDPOINT_URL not set"
( unset AWS_ENDPOINT_URL; python -m app.producer --count 1 ) || true
echo "--- Case B: endpoint points to real AWS"
( export AWS_ENDPOINT_URL="https://s3.us-east-1.amazonaws.com"; python -m app.producer --count 1 ) || true
echo "Both runs should print BLOCKED. See RUNBOOK.md section INC-04."
