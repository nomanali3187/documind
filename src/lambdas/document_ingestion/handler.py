"""
Triggered by EventBridge when a file lands in the intake S3 bucket.
Creates a Document record and starts a Step Functions execution.
"""
import json
import os
import sys
import uuid

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from shared.config import config
from shared.logger import get_logger, set_correlation_id
from shared.models import Document, DocumentStatus

logger = get_logger(__name__)

_sfn = boto3.client("stepfunctions", region_name=config.aws_region)
_dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)


def handler(event: dict, context) -> dict:
    correlation_id = set_correlation_id()
    logger.info("Document ingestion triggered", raw_event=json.dumps(event))

    bucket, key = _parse_s3_coordinates(event)
    if not bucket or not key:
        logger.error("Could not resolve S3 bucket/key from event", event=json.dumps(event))
        raise ValueError("Missing S3 bucket or key in event")

    document_id = str(uuid.uuid4())
    document = Document(
        document_id=document_id,
        s3_bucket=bucket,
        s3_key=key,
        file_name=key.split("/")[-1],
        status=DocumentStatus.PENDING,
    )

    _dynamodb.Table(config.documents_table).put_item(Item=document.to_dynamo())
    logger.info("Document record created", document_id=document_id)

    execution = _sfn.start_execution(
        stateMachineArn=config.step_functions_arn,
        name=f"doc-{document_id}",
        input=json.dumps({
            "document_id": document_id,
            "s3_bucket": bucket,
            "s3_key": key,
            "file_name": document.file_name,
            "correlation_id": correlation_id,
        }),
    )

    logger.info(
        "Step Functions execution started",
        document_id=document_id,
        execution_arn=execution["executionArn"],
    )

    return {"document_id": document_id, "execution_arn": execution["executionArn"]}


def _parse_s3_coordinates(event: dict) -> tuple[str, str]:
    """Handles both EventBridge S3 notifications and direct S3 event records."""
    # EventBridge S3 notification format
    detail = event.get("detail", {})
    if detail:
        bucket = detail.get("bucket", {}).get("name", "")
        key = detail.get("object", {}).get("key", "")
        return bucket, key

    # Direct S3 trigger format (useful for local testing)
    records = event.get("Records", [])
    if records:
        s3 = records[0].get("s3", {})
        bucket = s3.get("bucket", {}).get("name", "")
        key = s3.get("object", {}).get("key", "")
        return bucket, key

    return "", ""
