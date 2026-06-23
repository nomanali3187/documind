"""
Step 2 of the pipeline: pass extracted text and key-value pairs to Claude.
Claude classifies the document, extracts structured fields, produces a plain-language
summary, and flags any anomalies or missing data.
"""
import json
import os
import sys

import boto3
import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from shared.config import config
from shared.logger import get_logger, set_correlation_id
from shared.models import DocumentStatus

logger = get_logger(__name__)

_dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
_secrets = boto3.client("secretsmanager", region_name=config.aws_region)

_anthropic_client: anthropic.Anthropic | None = None

_PROMPT = """\
You are an expert document analyst. Analyze the document text and OCR-extracted key-value pairs below.

Return a single JSON object with EXACTLY these fields:
- "document_type": one of "INVOICE", "CONTRACT", "INSURANCE_FORM", "GENERAL", "UNKNOWN"
- "extracted_fields": object with the most important structured fields (dates, amounts, names, IDs)
- "summary": 2-3 sentence plain-language description of the document
- "risk_flags": array of strings — concerns, missing required fields, or anomalies (empty array if none)
- "confidence_score": float 0.0–1.0 reflecting your extraction confidence

Document text:
{raw_text}

OCR key-value pairs:
{key_values}

Respond with valid JSON only. No markdown code fences, no prose outside the JSON."""


def handler(event: dict, context) -> dict:
    set_correlation_id(event.get("correlation_id"))
    document_id = event["document_id"]
    raw_text: str = event.get("raw_text", "")
    key_values: dict = event.get("key_values", {})

    logger.info("Starting AI analysis", document_id=document_id, text_chars=len(raw_text))
    _set_status(document_id, DocumentStatus.ANALYZING)

    client = _get_anthropic_client()

    prompt = _PROMPT.format(
        raw_text=raw_text[:8_000],
        key_values=json.dumps(key_values, indent=2)[:2_000],
    )

    message = client.messages.create(
        model=config.claude_model_id,
        max_tokens=2_048,
        messages=[{"role": "user", "content": prompt}],
    )

    analysis: dict = json.loads(message.content[0].text)

    logger.info(
        "AI analysis complete",
        document_id=document_id,
        document_type=analysis.get("document_type"),
        confidence=analysis.get("confidence_score"),
        risk_flags=len(analysis.get("risk_flags", [])),
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
    )

    return {
        **event,
        "analysis": analysis,
        "token_usage": {
            "input": message.usage.input_tokens,
            "output": message.usage.output_tokens,
        },
    }


def _get_anthropic_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        secret = _secrets.get_secret_value(SecretId=config.anthropic_secret_name)
        api_key = json.loads(secret["SecretString"])["api_key"]
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def _set_status(document_id: str, status: DocumentStatus) -> None:
    _dynamodb.Table(config.documents_table).update_item(
        Key={"document_id": document_id},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": status.value},
    )
