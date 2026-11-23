"""Shared config, logging and the local-only safety guard."""
import logging
import os
import sys
from urllib.parse import urlparse

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")

INCOMING_BUCKET = "claims-incoming"
PROCESSED_BUCKET = "claims-processed"
QUEUE_NAME = "claims-queue"
DLQ_NAME = "claims-dlq"
TABLE_NAME = "claims-status"

LOCAL_HOSTS = {"127.0.0.1", "localhost"}
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def get_logger(name: str) -> logging.Logger:
    """Log to stdout and to logs/<name>.log, one line per event."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-5s [%(name)s] %(message)s")
    for handler in (logging.StreamHandler(sys.stdout),
                    logging.FileHandler(os.path.join(LOG_DIR, f"{name}.log"))):
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


def guard() -> None:
    """Refuse to run unless every AWS call goes to a local endpoint.

    This protects real AWS accounts: if someone forgets to `source scripts/env.sh`,
    the SDK would fall back to real AWS. We stop before that can happen.
    """
    endpoint = os.environ.get("AWS_ENDPOINT_URL")
    if not endpoint:
        sys.exit("BLOCKED: AWS_ENDPOINT_URL is not set. Run: source scripts/env.sh")
    host = urlparse(endpoint).hostname
    if host not in LOCAL_HOSTS:
        sys.exit(f"BLOCKED: AWS_ENDPOINT_URL points to '{host}', not a local emulator.")


def client(service: str):
    guard()
    return boto3.client(service, region_name=REGION)


def queue_url(sqs, name: str) -> str:
    return sqs.get_queue_url(QueueName=name)["QueueUrl"]


