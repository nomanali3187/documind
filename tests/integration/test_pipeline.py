"""
Integration tests — require real AWS credentials and a deployed dev environment.
Run with: pytest tests/integration -v -m integration

Set env vars:
  INTEGRATION_INTAKE_BUCKET=documind-dev-intake-xxxx
  INTEGRATION_DOCUMENTS_TABLE=documind-dev-documents
  INTEGRATION_RESULTS_TABLE=documind-dev-results
"""
import os
import time
import uuid

import boto3
import pytest

INTAKE_BUCKET = os.environ.get("INTEGRATION_INTAKE_BUCKET")
DOCUMENTS_TABLE = os.environ.get("INTEGRATION_DOCUMENTS_TABLE", "documind-dev-documents")
RESULTS_TABLE = os.environ.get("INTEGRATION_RESULTS_TABLE", "documind-dev-results")


@pytest.mark.integration
@pytest.mark.skipif(not INTAKE_BUCKET, reason="INTEGRATION_INTAKE_BUCKET not set")
def test_full_pipeline_invoice():
    s3 = boto3.client("s3")
    dynamodb = boto3.resource("dynamodb")

    key = f"integration-tests/{uuid.uuid4()}/sample_invoice.txt"
    body = (
        "INVOICE\n"
        "Invoice Number: INV-9999\n"
        "Date: 2024-06-01\n"
        "Bill To: Test Client Inc\n"
        "Description: Software Development Services\n"
        "Amount: $5,000.00\n"
        "Due Date: 2024-06-30\n"
    )

    s3.put_object(Bucket=INTAKE_BUCKET, Key=key, Body=body.encode())

    # Poll for completion — pipeline typically takes 10-30 seconds
    documents_table = dynamodb.Table(DOCUMENTS_TABLE)
    completed = False
    for _ in range(24):  # 2 minute timeout
        time.sleep(5)
        items = documents_table.scan(
            FilterExpression="s3_key = :k",
            ExpressionAttributeValues={":k": key},
        )["Items"]
        if items and items[0]["status"] in ("COMPLETED", "FAILED"):
            completed = True
            doc = items[0]
            break

    assert completed, "Pipeline did not complete within 2 minutes"
    assert doc["status"] == "COMPLETED", f"Pipeline failed: {doc.get('failure_reason')}"
    assert doc["document_type"] == "INVOICE"

    results = dynamodb.Table(RESULTS_TABLE)
    result = results.get_item(Key={"document_id": doc["document_id"]})["Item"]
    assert result["confidence_score"] is not None
    assert "invoice" in result["summary"].lower() or "INV" in str(result["extracted_fields"])
