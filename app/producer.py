"""Submit synthetic claims: upload JSON to S3, record status, enqueue a message.

All data is fake. Examples:
    python -m app.producer --count 20
    python -m app.producer --count 20 --bad 3
"""
import argparse
import json
import random
import uuid
from datetime import datetime, timezone

from app.common import (INCOMING_BUCKET, QUEUE_NAME, TABLE_NAME, client, get_logger,
                        queue_url)

log = get_logger("producer")

PROCEDURES = ["99213", "99214", "80053", "71046", "93000"]
DIAGNOSES = ["E11.9", "I10", "J06.9", "M54.5", "Z00.00"]


def make_claim(bad: bool) -> dict:
    claim = {
        "claim_id": f"CLM-{uuid.uuid4().hex[:8].upper()}",
        "member_id": f"MBR-{random.randint(100000, 999999)}",
        "procedure_code": random.choice(PROCEDURES),
        "diagnosis_code": random.choice(DIAGNOSES),
        "amount": round(random.uniform(50, 2500), 2),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    if bad:
        # Pick one realistic data-quality problem.
        problem = random.choice(["missing_member", "negative_amount", "over_limit"])
        if problem == "missing_member":
            claim.pop("member_id")
        elif problem == "negative_amount":
            claim["amount"] = -claim["amount"]
        else:
            claim["amount"] = 75000.00
    return claim


def submit(claim: dict, s3=None, sqs=None, ddb=None) -> None:
    s3 = s3 or client("s3")
    sqs = sqs or client("sqs")
    ddb = ddb or client("dynamodb")
    key = f"incoming/{claim['claim_id']}.json"
    s3.put_object(Bucket=INCOMING_BUCKET, Key=key, Body=json.dumps(claim).encode(),
                  ContentType="application/json")
    ddb.put_item(TableName=TABLE_NAME, Item={
        "claim_id": {"S": claim["claim_id"]},
        "status": {"S": "RECEIVED"},
        "updated_at": {"S": datetime.now(timezone.utc).isoformat()},
    })
    sqs.send_message(QueueUrl=queue_url(sqs, QUEUE_NAME), MessageBody=json.dumps(
        {"claim_id": claim["claim_id"], "bucket": INCOMING_BUCKET, "key": key}))
    log.info("submitted claim_id=%s key=%s", claim["claim_id"], key)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10, help="total claims to submit")
    parser.add_argument("--bad", type=int, default=0, help="how many of them are invalid")
    args = parser.parse_args()

    s3, sqs, ddb = client("s3"), client("sqs"), client("dynamodb")
    bad_slots = set(random.sample(range(args.count), min(args.bad, args.count)))
    for i in range(args.count):
        submit(make_claim(i in bad_slots), s3, sqs, ddb)
    log.info("done count=%d bad=%d", args.count, len(bad_slots))


if __name__ == "__main__":
    main()
