import sys
import os

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


def _setup_tables(dynamodb):
    for name in ("test-documents", "test-results"):
        dynamodb.create_table(
            TableName=name,
            KeySchema=[{"AttributeName": "document_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "document_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )


@mock_aws
def test_handler_stores_result_and_marks_completed(analysis_event):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    _setup_tables(dynamodb)
    dynamodb.Table("test-documents").put_item(Item={
        "document_id": analysis_event["document_id"], "status": "ANALYZING"
    })

    from lambdas.result_storage.handler import handler
    result = handler(analysis_event, None)

    assert result["status"] == "COMPLETED"
    assert "completed_at" in result
    assert result["result_summary"]["document_type"] == "INVOICE"
    assert result["result_summary"]["confidence_score"] == 0.95

    doc = dynamodb.Table("test-documents").get_item(
        Key={"document_id": analysis_event["document_id"]}
    )["Item"]
    assert doc["status"] == "COMPLETED"
    assert doc["document_type"] == "INVOICE"

    stored = dynamodb.Table("test-results").get_item(
        Key={"document_id": analysis_event["document_id"]}
    )["Item"]
    assert stored["document_type"] == "INVOICE"
    assert stored["summary"] != ""


@mock_aws
def test_handler_handles_unknown_document_type(analysis_event):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    _setup_tables(dynamodb)
    dynamodb.Table("test-documents").put_item(Item={
        "document_id": analysis_event["document_id"], "status": "ANALYZING"
    })

    event = {**analysis_event, "analysis": {**analysis_event["analysis"], "document_type": "RECEIPT"}}

    from lambdas.result_storage.handler import handler
    result = handler(event, None)

    assert result["result_summary"]["document_type"] == "UNKNOWN"
