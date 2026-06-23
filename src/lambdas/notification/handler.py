"""
Step 4 of the pipeline: publish a completion notification to SNS.
Downstream consumers (email, webhook, Slack) subscribe to the topic.
"""
import json
import os
import sys

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from shared.config import config
from shared.logger import get_logger, set_correlation_id

logger = get_logger(__name__)

_sns = boto3.client("sns", region_name=config.aws_region)


def handler(event: dict, context) -> dict:
    set_correlation_id(event.get("correlation_id"))
    document_id = event["document_id"]
    result_summary = event.get("result_summary", {})

    payload = {
        "document_id": document_id,
        "file_name": event.get("file_name", ""),
        "status": event.get("status", "COMPLETED"),
        "document_type": result_summary.get("document_type", "UNKNOWN"),
        "confidence_score": result_summary.get("confidence_score", 0.0),
        "risk_flags_found": result_summary.get("risk_flag_count", 0),
        "summary": result_summary.get("summary", ""),
        "s3_key": event.get("s3_key", ""),
        "completed_at": event.get("completed_at", ""),
    }

    if not config.notification_topic_arn:
        logger.warning("NOTIFICATION_TOPIC_ARN not set — skipping SNS publish")
        return {"document_id": document_id, "notification_sent": False}

    _sns.publish(
        TopicArn=config.notification_topic_arn,
        Subject=f"DocuMind: {payload['document_type']} processed — {payload['file_name']}",
        Message=json.dumps(payload, indent=2),
        MessageAttributes={
            "document_type": {"DataType": "String", "StringValue": payload["document_type"]},
            "environment": {"DataType": "String", "StringValue": config.environment},
        },
    )

    logger.info("SNS notification published", document_id=document_id, topic=config.notification_topic_arn)
    return {"document_id": document_id, "notification_sent": True}
