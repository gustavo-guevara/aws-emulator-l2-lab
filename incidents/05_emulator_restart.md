# INC-05: emulator restart (manual)

No script for this one; you cause it yourself.

1. With claims in the pipeline, go to Terminal 1 and press **Ctrl+C** to stop `aws-emulator`.
2. Run `./scripts/healthcheck.sh`. It fails at step 1 (connection refused).
3. Start `aws-emulator` again and re-run the healthcheck. The emulator answers,
   but every bucket, queue and table is gone.

Ticket: *"After the maintenance window, the whole claims pipeline is failing."*

Follow RUNBOOK.md section INC-05.
