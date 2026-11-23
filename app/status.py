"""L2 triage view: one claim, or a summary of the whole pipeline.

    python -m app.status --summary
    python -m app.status CLM-1A2B3C4D
    python -m app.status --dlq          # show what is in the dead-letter queue
"""
import argparse
import json
from collections import Counter

from app.common import DLQ_NAME, QUEUE_NAME, TABLE_NAME, client, queue_url


def depth(sqs, name: str) -> dict:
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url(sqs, name),
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    return {"waiting": int(attrs.get("ApproximateNumberOfMessages", 0)),
            "in_flight": int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0))}


def summary() -> None:
    sqs, ddb = client("sqs"), client("dynamodb")
    counts = Counter()
    for page in ddb.get_paginator("scan").paginate(TableName=TABLE_NAME):
        for item in page["Items"]:
            counts[item["status"]["S"]] += 1
    print("Claims by status:")
    for status in ("RECEIVED", "PROCESSED", "REJECTED", "ERROR"):
        print(f"  {status:<10} {counts.get(status, 0)}")
    print("Queues:")
    for name in (QUEUE_NAME, DLQ_NAME):
        d = depth(sqs, name)
        print(f"  {name:<14} waiting={d['waiting']} in_flight={d['in_flight']}")


def one(claim_id: str) -> None:
    ddb = client("dynamodb")
    item = ddb.get_item(TableName=TABLE_NAME, Key={"claim_id": {"S": claim_id}}).get("Item")
    if not item:
        print(f"{claim_id}: not found")
        return
    print(json.dumps({k: list(v.values())[0] for k, v in item.items()}, indent=2))


def show_dlq() -> None:
    """Peek at DLQ messages without removing them (visibility timeout 0)."""
    sqs = client("sqs")
    resp = sqs.receive_message(QueueUrl=queue_url(sqs, DLQ_NAME), MaxNumberOfMessages=10,
                               MessageAttributeNames=["All"], VisibilityTimeout=0)
    msgs = resp.get("Messages", [])
    if not msgs:
        print("DLQ is empty")
    for m in msgs:
        attrs = {k: v["StringValue"] for k, v in m.get("MessageAttributes", {}).items()}
        print(f"- {m['Body']}\n  status={attrs.get('status')} reason={attrs.get('reason')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claim_id", nargs="?")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--dlq", action="store_true")
    args = parser.parse_args()
    if args.dlq:
        show_dlq()
    elif args.claim_id:
        one(args.claim_id)
    else:
        summary()


if __name__ == "__main__":
    main()
