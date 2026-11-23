# AWS Emulator L2 Support Lab

A hands-on production-support lab: a small claims-processing pipeline running on
**AWS Emulator** (AWS's official local emulator of its APIs) inside a **Multipass** Ubuntu VM.
No AWS account, no cloud bill, nothing that can touch real infrastructure.

You run the pipeline, inject realistic incidents, and solve them with a runbook,
the same way an L2 support engineer would on call.

> All data is synthetic. Claim, member and diagnosis values are randomly generated.

## Architecture

```
 producer ──► S3 claims-incoming ──┐
     │                             │
     ├──► DynamoDB claims-status   │
     │         ▲                   │
     └──► SQS claims-queue ──► worker ──► S3 claims-processed   (valid)
                                   │
                                   └────► SQS claims-dlq        (rejected / error)
```

| Piece | What it does |
|---|---|
| `app/producer.py` | Generates claims, uploads JSON to S3, writes `RECEIVED`, enqueues a message |
| `app/worker.py` | Reads the queue, validates, writes `PROCESSED` / `REJECTED` / `ERROR`, sends failures to the DLQ |
| `app/status.py` | Triage view: summary, a single claim, or DLQ contents |
| `app/redrive.py` | Moves DLQ messages back to the main queue after a fix |
| `scripts/healthcheck.sh` | Checks the emulator and every resource; exit code 0/1 |
| `incidents/` | Scripts that break things on purpose |
| `RUNBOOK.md` | How to diagnose and fix each incident |

The app refuses to run unless `AWS_ENDPOINT_URL` points to `127.0.0.1` or `localhost`,
so a misconfigured shell can never reach a real AWS account.

## Setup

**1. Create the VM** (on your Mac or PC, from this folder):

```bash
multipass launch 24.04 --name aws-lab --cpus 2 --memory 4G --disk 15G \
  --cloud-init multipass/cloud-init.yaml
multipass mount "$PWD" aws-lab:/home/ubuntu/lab
```

**2. Install the emulator, AWS CLI v2 and Python deps** (inside the VM):

```bash
multipass shell aws-lab
cd ~/lab && ./scripts/install.sh
```

**3. Run it.** Use two terminals (`multipass shell aws-lab` in each).

Terminal 1, the emulator (serves HTTPS on `127.0.0.1:9297`):

```bash
aws-emulator
```

Terminal 2, the lab:

```bash
cd ~/lab
source ~/.venv-lab/bin/activate
source scripts/env.sh
aws sts get-caller-identity          # answered by the emulator, not AWS
python -m app.setup_resources
./scripts/healthcheck.sh
```

## Happy path

```bash
python -m app.producer --count 20 --bad 3
python -m app.worker --once
python -m app.status --summary
python -m app.status --dlq
```

## Incidents

| ID | Inject with | Ticket says |
|---|---|---|
| INC-01 | `./incidents/01_corrupt_file.sh` | "Claim stuck, member says it was submitted" |
| INC-02 | `./incidents/02_missing_object.sh` | "Claim shows ERROR in the portal" |
| INC-03 | `./incidents/03_backlog.sh` (worker stopped) | "Nothing processed since last night" |
| INC-04 | `./incidents/04_wrong_endpoint.sh` | "Job fails with BLOCKED" |
| INC-05 | see `incidents/05_emulator_restart.md` | "Pipeline down after maintenance" |

Inject one, run `python -m app.worker --once` where it applies, then work it
using [RUNBOOK.md](RUNBOOK.md) without reading the fix first.

## What this demonstrates

- Structured triage: platform → queues → item → logs
- Dead-letter queues, redrive, and when **not** to redrive (bad data vs technical errors)
- Telling business-rule failures apart from technical failures
- Backlog detection from queue depth and log silence
- Environment safety: guarding against running against the wrong account
- Stateless vs stateful components, and rebuilding infrastructure from code
- Writing runbooks and closing tickets with root cause and prevention

## Notes

- AWS Emulator keeps everything in memory. Stopping it deletes all resources and the files
  in `~/.aws/emulator/9297/`, so run `source scripts/env.sh` and `setup_resources` after every restart.
- The emulator matches real AWS most closely for create/describe/update/delete calls;
  fidelity varies by service. It is for learning and testing, not for validating IAM permissions.
- Docs: https://docs.aws.amazon.com/emulator/
