"""
Step 1 of the pipeline: extract raw text and key-value pairs from the document using AWS Textract.
Supports PDFs and images. Uses synchronous analyze_document for files ≤5 MB (swap to
start_document_analysis for larger files in production).
"""
import os
import sys

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from shared.config import config
from shared.logger import get_logger, set_correlation_id
from shared.models import DocumentStatus

logger = get_logger(__name__)

_textract = boto3.client("textract", region_name=config.aws_region)
_dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)


def handler(event: dict, context) -> dict:
    set_correlation_id(event.get("correlation_id"))
    document_id = event["document_id"]
    s3_bucket = event["s3_bucket"]
    s3_key = event["s3_key"]

    logger.info("Starting text extraction", document_id=document_id, s3_key=s3_key)
    _set_status(document_id, DocumentStatus.EXTRACTING)

    response = _textract.analyze_document(
        Document={"S3Object": {"Bucket": s3_bucket, "Name": s3_key}},
        FeatureTypes=["FORMS", "TABLES"],
    )

    raw_text = _collect_lines(response)
    key_values = _collect_key_value_pairs(response)
    page_count = len({b.get("Page", 1) for b in response["Blocks"]})

    logger.info(
        "Text extraction complete",
        document_id=document_id,
        pages=page_count,
        chars=len(raw_text),
        kv_pairs=len(key_values),
    )

    return {
        **event,
        "raw_text": raw_text,
        "key_values": key_values,
        "page_count": page_count,
    }


# ---------------------------------------------------------------------------
# Textract response parsing helpers
# ---------------------------------------------------------------------------

def _collect_lines(response: dict) -> str:
    return "\n".join(
        b["Text"] for b in response["Blocks"] if b["BlockType"] == "LINE"
    )


def _collect_key_value_pairs(response: dict) -> dict[str, str]:
    blocks = {b["Id"]: b for b in response["Blocks"]}
    key_blocks = {
        b["Id"]: b
        for b in response["Blocks"]
        if b["BlockType"] == "KEY_VALUE_SET" and "KEY" in b.get("EntityTypes", [])
    }
    value_blocks = {
        b["Id"]: b
        for b in response["Blocks"]
        if b["BlockType"] == "KEY_VALUE_SET" and "VALUE" in b.get("EntityTypes", [])
    }

    result: dict[str, str] = {}
    for key_block in key_blocks.values():
        key_text = _words_from_block(key_block, blocks)
        value_text = ""
        for rel in key_block.get("Relationships", []):
            if rel["Type"] == "VALUE":
                for vid in rel["Ids"]:
                    if vid in value_blocks:
                        value_text = _words_from_block(value_blocks[vid], blocks)
        if key_text:
            result[key_text] = value_text

    return result


def _words_from_block(block: dict, blocks_map: dict) -> str:
    words: list[str] = []
    for rel in block.get("Relationships", []):
        if rel["Type"] == "CHILD":
            for cid in rel["Ids"]:
                child = blocks_map.get(cid, {})
                if child.get("BlockType") == "WORD":
                    words.append(child.get("Text", ""))
    return " ".join(words).strip()


def _set_status(document_id: str, status: DocumentStatus) -> None:
    _dynamodb.Table(config.documents_table).update_item(
        Key={"document_id": document_id},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": status.value},
    )
