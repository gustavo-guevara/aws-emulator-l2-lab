"""Move messages from the DLQ back to the main queue after a fix.

    python -m app.redrive              # move everything
    python -m app.redrive --dry-run    # only show what would move
"""
import argparse

from app.common import DLQ_NAME, QUEUE_NAME, client, get_logger, queue_url

log = get_logger("redrive")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sqs = client("sqs")
    q_url, dlq_url = queue_url(sqs, QUEUE_NAME), queue_url(sqs, DLQ_NAME)
    moved = 0
    while True:
        msgs = sqs.receive_message(QueueUrl=dlq_url, MaxNumberOfMessages=10,
                                   WaitTimeSeconds=1,
                                   VisibilityTimeout=0 if args.dry_run else 30
                                   ).get("Messages", [])
        if not msgs:
            break
        for m in msgs:
            if args.dry_run:
                log.info("would redrive body=%s", m["Body"])
                continue
            sqs.send_message(QueueUrl=q_url, MessageBody=m["Body"])
            sqs.delete_message(QueueUrl=dlq_url, ReceiptHandle=m["ReceiptHandle"])
            moved += 1
        if args.dry_run:
            break
    log.info("redrive complete moved=%d dry_run=%s", moved, args.dry_run)


if __name__ == "__main__":
    main()
