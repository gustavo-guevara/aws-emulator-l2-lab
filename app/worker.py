"""Process claims from the queue.

Valid claims    -> copied to the processed bucket, status PROCESSED
Invalid claims  -> status REJECTED, message sent to the DLQ with the reason
Technical error -> status ERROR,    message sent to the DLQ with the reason

    python -m app.worker            # run until Ctrl+C
    python -m app.worker --once     # drain the queue, then exit
    python -m app.worker --delay 2  # simulate a slow downstream system
"""
import argparse
import json
import time
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from app.common import (DLQ_NAME, PROCESSED_BUCKET, QUEUE_NAME, TABLE_NAME, client,
                        get_logger, queue_url)

log = get_logger("worker")

REQUIRED = ["claim_id", "member_id", "procedure_code", "diagnosis_code", "amount"]
MAX_AMOUNT = 50000


class Rejected(Exception):
    """Business rule failure: the data is wrong, retrying won't help."""


def validate(claim: dict) -> None:
    missing = [f for f in REQUIRED if f not in claim]
    if missing:
        raise Rejected(f"missing fields: {','.join(missing)}")
    if not isinstance(claim["amount"], (int, float)) or claim["amount"] <= 0:
        raise Rejected(f"invalid amount: {claim['amount']}")
    if claim["amount"] > MAX_AMOUNT:
        raise Rejected(f"amount {claim['amount']} over limit {MAX_AMOUNT}")


def set_status(ddb, claim_id: str, status: str, reason: str = "") -> None:
    item = {
        "claim_id": {"S": claim_id},
        "status": {"S": status},
        "updated_at": {"S": datetime.now(timezone.utc).isoformat()},
    }
    if reason:
        item["reason"] = {"S": reason}
    ddb.put_item(TableName=TABLE_NAME, Item=item)


def handle(body: str, s3, ddb) -> tuple[str, str]:
    """Return (status, reason) for one message body."""
    try:
        msg = json.loads(body)
        claim_id, bucket, key = msg["claim_id"], msg["bucket"], msg["key"]
    except (json.JSONDecodeError, KeyError) as e:
        return "ERROR", f"bad message envelope: {e}"

    try:
        raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    except ClientError as e:
        return "ERROR", f"s3 get_object failed: {e.response['Error']['Code']} {bucket}/{key}"

    try:
        claim = json.loads(raw)
    except json.JSONDecodeError as e:
        return "ERROR", f"claim file is not valid JSON: {e}"

    try:
        validate(claim)
    except Rejected as e:
        return "REJECTED", str(e)

    s3.put_object(Bucket=PROCESSED_BUCKET, Key=key.replace("incoming/", "processed/"),
                  Body=json.dumps({**claim, "processed_at":
                                   datetime.now(timezone.utc).isoformat()}).encode())
    return "PROCESSED", ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="exit when the queue is empty")
    parser.add_argument("--delay", type=float, default=0, help="seconds to sleep per claim")
    args = parser.parse_args()

    s3, sqs, ddb = client("s3"), client("sqs"), client("dynamodb")
    q_url, dlq_url = queue_url(sqs, QUEUE_NAME), queue_url(sqs, DLQ_NAME)
    totals = {"PROCESSED": 0, "REJECTED": 0, "ERROR": 0}
    log.info("worker started queue=%s once=%s delay=%s", QUEUE_NAME, args.once, args.delay)

    try:
        while True:
            resp = sqs.receive_message(QueueUrl=q_url, MaxNumberOfMessages=10,
                                       WaitTimeSeconds=2 if args.once else 10)
            messages = resp.get("Messages", [])
            if not messages and args.once:
                break
            for m in messages:
                started = time.monotonic()
                status, reason = handle(m["Body"], s3, ddb)
                claim_id = _claim_id(m["Body"])
                if claim_id:
                    set_status(ddb, claim_id, status, reason)
                if status != "PROCESSED":
                    sqs.send_message(QueueUrl=dlq_url, MessageBody=m["Body"],
                                     MessageAttributes={
                                         "status": {"DataType": "String", "StringValue": status},
                                         "reason": {"DataType": "String", "StringValue": reason}})
                sqs.delete_message(QueueUrl=q_url, ReceiptHandle=m["ReceiptHandle"])
                totals[status] += 1
                level = log.info if status == "PROCESSED" else log.warning
                level("claim_id=%s status=%s ms=%d%s", claim_id or "?", status,
                      (time.monotonic() - started) * 1000,
                      f" reason=\"{reason}\"" if reason else "")
                if args.delay:
                    time.sleep(args.delay)
    except KeyboardInterrupt:
        log.info("stopping on Ctrl+C")
    log.info("worker finished processed=%d rejected=%d error=%d",
             totals["PROCESSED"], totals["REJECTED"], totals["ERROR"])


def _claim_id(body: str) -> str:
    try:
        return json.loads(body).get("claim_id", "")
    except (json.JSONDecodeError, AttributeError):
        return ""


if __name__ == "__main__":
    main()
