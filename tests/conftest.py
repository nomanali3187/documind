import os
import pytest

# Set all required env vars before any Lambda module is imported
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("DOCUMENTS_TABLE", "test-documents")
os.environ.setdefault("RESULTS_TABLE", "test-results")
os.environ.setdefault("STEP_FUNCTIONS_ARN", "arn:aws:states:us-east-1:123456789012:stateMachine:test")
os.environ.setdefault("NOTIFICATION_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:test-notifications")
os.environ.setdefault("ANTHROPIC_SECRET_NAME", "test/anthropic-api-key")
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture
def base_event():
    return {
        "document_id": "test-doc-001",
        "s3_bucket": "test-intake-bucket",
        "s3_key": "uploads/invoice.pdf",
        "file_name": "invoice.pdf",
        "correlation_id": "corr-test-001",
    }


@pytest.fixture
def analysis_event(base_event):
    return {
        **base_event,
        "raw_text": "Invoice #12345\nDate: 2024-01-15\nTotal: $1,500.00\nVendor: Acme Corp",
        "key_values": {"Invoice Number": "12345", "Total Amount": "$1,500.00", "Date": "2024-01-15"},
        "page_count": 1,
        "analysis": {
            "document_type": "INVOICE",
            "extracted_fields": {
                "invoice_number": "12345",
                "total_amount": "$1,500.00",
                "date": "2024-01-15",
                "vendor": "Acme Corp",
            },
            "summary": "This is an invoice from Acme Corp for $1,500.00 dated January 15, 2024.",
            "risk_flags": [],
            "confidence_score": 0.95,
        },
    }
