"""
Catch-all failure handler invoked by Step Functions on unhandled errors in any pipeline state.
Marks the document as FAILED, logs the cause, and publishes an alert notification.
"""
import json
import os
import sys
from datetime import datetime, timezone

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from shared.config import config
from shared.logger import get_logger, set_correlation_id
from shared.models import DocumentStatus

logger = get_logger(__name__)

_dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
_sns = boto3.client("sns", region_name=config.aws_region)


def handler(event: dict, context) -> dict:
    set_correlation_id(event.get("correlation_id"))
    document_id = event.get("document_id", "unknown")
    error_info: dict = event.get("error", {})

    error_cause = error_info.get("Cause", "Unknown error")
    error_name = error_info.get("Error", "UnknownError")

    logger.error(
        "Pipeline failed",
        document_id=document_id,
        error_name=error_name,
        error_cause=error_cause,
    )

    failed_at = datetime.now(timezone.utc).isoformat()

    if document_id != "unknown":
        _dynamodb.Table(config.documents_table).update_item(
            Key={"document_id": document_id},
            UpdateExpression="SET #s = :s, failed_at = :fa, failure_reason = :fr",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": DocumentStatus.FAILED.value,
                ":fa": failed_at,
                ":fr": f"{error_name}: {error_cause[:500]}",
            },
        )

    if config.notification_topic_arn:
        _sns.publish(
            TopicArn=config.notification_topic_arn,
            Subject=f"DocuMind FAILURE: {document_id}",
            Message=json.dumps({
                "document_id": document_id,
                "file_name": event.get("file_name", ""),
                "status": "FAILED",
                "error_name": error_name,
                "error_cause": error_cause[:500],
                "failed_at": failed_at,
            }, indent=2),
            MessageAttributes={
                "document_type": {"DataType": "String", "StringValue": "FAILURE_ALERT"},
                "environment": {"DataType": "String", "StringValue": config.environment},
            },
        )

    return {"document_id": document_id, "status": "FAILED", "failed_at": failed_at}
