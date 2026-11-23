# Runbook: Claims Pipeline (L2 Production Support)

Triage order for any ticket: **check the platform, then the queues, then the item, then the logs.**

```bash
./scripts/healthcheck.sh              # 1. platform: emulator, buckets, queues, table
python -m app.status --summary        # 2. counts by status + queue depth
python -m app.status <CLAIM_ID>       # 3. the specific claim from the ticket
grep <CLAIM_ID> logs/*.log            # 4. full history of that claim
python -m app.status --dlq            # what failed and why
```

Status meanings:

| Status | Meaning | Who fixes it |
|---|---|---|
| RECEIVED | Queued, not processed yet | Nobody, unless it stays there (see INC-03) |
| PROCESSED | Done | n/a |
| REJECTED | Business rule failed (bad data) | Data owner / submitter. **Don't redrive as-is.** |
| ERROR | Technical failure | L2, then redrive after the fix |

---

## INC-01: corrupt claim file

**Symptom:** claim in `ERROR`, reason `claim file is not valid JSON`.

```bash
python -m app.status CLM-CORRUPT01
aws s3 cp s3://claims-incoming/incoming/CLM-CORRUPT01.json - | head -c 300
```

**Root cause:** the upstream system sent a truncated file.
**Fix:** ask upstream to resend, or upload the corrected file to the same key, then redrive:

```bash
python -m app.redrive --dry-run
python -m app.redrive
python -m app.worker --once
```

**Prevent:** have upstream validate before sending, and alert on the ERROR count.

## INC-02: message without a file

**Symptom:** `ERROR`, reason `s3 get_object failed: NoSuchKey`.

```bash
aws s3 ls s3://claims-incoming/incoming/ | grep CLM-MISSING01   # empty = never uploaded
```

**Root cause:** the message was sent before the upload finished (or the file was deleted).
Redriving won't help until the file exists. Escalate to the producer team with the claim ID and timestamp from `logs/worker.log`.

## INC-03: backlog

**Symptom:** many claims stuck in `RECEIVED`, `claims-queue waiting` is high, no new lines in `logs/worker.log`.

```bash
python -m app.status --summary
tail -n 5 logs/worker.log          # when did the worker last do anything?
pgrep -af app.worker || echo "worker is not running"
```

**Fix:** start the worker and watch the queue drain:

```bash
python -m app.worker &             # or in its own terminal
watch -n 2 python -m app.status --summary
```

**Prevent:** alert on queue depth and on the age of the oldest message, and run the worker as a service that restarts on its own.

## INC-04: job pointed at the wrong environment

**Symptom:** the job prints `BLOCKED: AWS_ENDPOINT_URL ...`.

This is the guard working: the shell was not configured for the lab, so the SDK would have used real AWS.
**Fix:** `source scripts/env.sh` and confirm with `aws sts get-caller-identity`.
**Lesson:** always confirm which account and endpoint you are on before running anything in production.

## INC-05: emulator restarted, everything gone

**Symptom:** healthcheck step 1 fails (emulator down). After restarting it, step 1 passes but buckets, queues and table are missing.

**Root cause:** AWS Emulator keeps state in memory only and wipes it on stop.
**Fix:**

```bash
aws-emulator                       # Terminal 1
source scripts/env.sh              # Terminal 2 (the CA file is regenerated)
python -m app.setup_resources
./scripts/healthcheck.sh
```

**Lesson:** know which components are stateless. In real AWS the equivalent is infrastructure as code: rebuild in one command, don't fix by hand.

---

## Closing a ticket

Write down: impact (how many claims, how long), root cause, fix, what prevents it next time.
