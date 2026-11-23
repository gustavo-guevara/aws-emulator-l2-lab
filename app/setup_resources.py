"""Create the buckets, queues and table. Safe to run more than once.

AWS Emulator keeps everything in memory, so after every restart you run this again.
"""
from botocore.exceptions import ClientError

from app.common import (DLQ_NAME, INCOMING_BUCKET, PROCESSED_BUCKET, QUEUE_NAME,
                        TABLE_NAME, client, get_logger)

log = get_logger("setup")


def main() -> None:
    s3 = client("s3")
    sqs = client("sqs")
    ddb = client("dynamodb")

    for bucket in (INCOMING_BUCKET, PROCESSED_BUCKET):
        try:
            s3.create_bucket(Bucket=bucket)
            log.info("created bucket=%s", bucket)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                log.info("exists bucket=%s", bucket)
            else:
                raise

    for queue in (QUEUE_NAME, DLQ_NAME):
        sqs.create_queue(QueueName=queue)  # idempotent with the same attributes
        log.info("ready queue=%s", queue)

    try:
        ddb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "claim_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "claim_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.get_waiter("table_exists").wait(TableName=TABLE_NAME)
        log.info("created table=%s", TABLE_NAME)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            log.info("exists table=%s", TABLE_NAME)
        else:
            raise

    log.info("setup complete")


if __name__ == "__main__":
    main()
