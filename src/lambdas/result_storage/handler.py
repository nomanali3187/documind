"""
Step 3 of the pipeline: persist the analysis result to DynamoDB and mark the document COMPLETED.
"""
import os
import sys
from datetime import datetime, timezone

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from shared.config import config
from shared.logger import get_logger, set_correlation_id
from shared.models import AnalysisResult, DocumentStatus, DocumentType

logger = get_logger(__name__)

_dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)


def handler(event: dict, context) -> dict:
    set_correlation_id(event.get("correlation_id"))
    document_id = event["document_id"]
    analysis: dict = event["analysis"]

    doc_type_raw = analysis.get("document_type", "UNKNOWN")
    try:
        doc_type = DocumentType(doc_type_raw)
    except ValueError:
        doc_type = DocumentType.UNKNOWN

    result = AnalysisResult(
        document_id=document_id,
        document_type=doc_type,
        extracted_fields=analysis.get("extracted_fields", {}),
        summary=analysis.get("summary", ""),
        risk_flags=analysis.get("risk_flags", []),
        raw_text=event.get("raw_text", ""),
        confidence_score=float(analysis.get("confidence_score", 0.0)),
    )

    _dynamodb.Table(config.results_table).put_item(Item=result.to_dynamo())

    completed_at = datetime.now(timezone.utc).isoformat()
    _dynamodb.Table(config.documents_table).update_item(
        Key={"document_id": document_id},
        UpdateExpression="SET #s = :s, document_type = :dt, completed_at = :ca",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": DocumentStatus.COMPLETED.value,
            ":dt": result.document_type.value,
            ":ca": completed_at,
        },
    )

    logger.info(
        "Results stored",
        document_id=document_id,
        document_type=result.document_type.value,
        confidence=result.confidence_score,
        risk_flag_count=len(result.risk_flags),
    )

    return {
        **event,
        "status": DocumentStatus.COMPLETED.value,
        "completed_at": completed_at,
        "result_summary": {
            "document_type": result.document_type.value,
            "confidence_score": result.confidence_score,
            "risk_flag_count": len(result.risk_flags),
            "summary": result.summary,
        },
    }
