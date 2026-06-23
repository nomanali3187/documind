from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentType(str, Enum):
    INVOICE = "INVOICE"
    CONTRACT = "CONTRACT"
    INSURANCE_FORM = "INSURANCE_FORM"
    GENERAL = "GENERAL"
    UNKNOWN = "UNKNOWN"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Document:
    document_id: str
    s3_bucket: str
    s3_key: str
    file_name: str = ""
    tenant_id: str = ""
    status: DocumentStatus = DocumentStatus.PENDING
    document_type: DocumentType = DocumentType.UNKNOWN
    uploaded_at: str = field(default_factory=_now_iso)

    def to_dynamo(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "s3_bucket": self.s3_bucket,
            "s3_key": self.s3_key,
            "file_name": self.file_name,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "document_type": self.document_type.value,
            "uploaded_at": self.uploaded_at,
        }


@dataclass
class AnalysisResult:
    document_id: str
    document_type: DocumentType
    extracted_fields: dict[str, Any]
    summary: str
    risk_flags: list[str]
    raw_text: str
    confidence_score: float
    analyzed_at: str = field(default_factory=_now_iso)

    def to_dynamo(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type.value,
            "extracted_fields": self.extracted_fields,
            "summary": self.summary,
            "risk_flags": self.risk_flags,
            "raw_text": self.raw_text,
            "confidence_score": str(self.confidence_score),  # DynamoDB decimal-safe
            "analyzed_at": self.analyzed_at,
        }
