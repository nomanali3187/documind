import sys
import os
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


MOCK_TEXTRACT_RESPONSE = {
    "Blocks": [
        {"Id": "b1", "BlockType": "LINE", "Text": "Invoice #12345", "Page": 1},
        {"Id": "b2", "BlockType": "LINE", "Text": "Total: $1,500.00", "Page": 1},
        {"Id": "key1", "BlockType": "KEY_VALUE_SET", "EntityTypes": ["KEY"],
         "Relationships": [{"Type": "VALUE", "Ids": ["val1"]}, {"Type": "CHILD", "Ids": ["w1"]}]},
        {"Id": "val1", "BlockType": "KEY_VALUE_SET", "EntityTypes": ["VALUE"],
         "Relationships": [{"Type": "CHILD", "Ids": ["w2"]}]},
        {"Id": "w1", "BlockType": "WORD", "Text": "Total"},
        {"Id": "w2", "BlockType": "WORD", "Text": "$1,500.00"},
    ]
}


@mock_aws
def test_handler_returns_raw_text_and_key_values(base_event):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-documents",
        KeySchema=[{"AttributeName": "document_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "document_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamodb.Table("test-documents").put_item(Item={
        "document_id": base_event["document_id"], "status": "PENDING"
    })

    with patch("boto3.client") as mock_boto_client:
        mock_textract = MagicMock()
        mock_textract.analyze_document.return_value = MOCK_TEXTRACT_RESPONSE
        mock_boto_client.return_value = mock_textract

        from lambdas.text_extraction import handler as module
        module._textract = mock_textract

        result = module.handler(base_event, None)

    assert "raw_text" in result
    assert "Invoice #12345" in result["raw_text"]
    assert "Total: $1,500.00" in result["raw_text"]
    assert "key_values" in result
    assert result["page_count"] == 1


@mock_aws
def test_handler_sets_extracting_status(base_event):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    dynamodb.create_table(
        TableName="test-documents",
        KeySchema=[{"AttributeName": "document_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "document_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamodb.Table("test-documents").put_item(Item={
        "document_id": base_event["document_id"], "status": "PENDING"
    })

    with patch("boto3.client") as mock_boto_client:
        mock_textract = MagicMock()
        mock_textract.analyze_document.return_value = MOCK_TEXTRACT_RESPONSE
        mock_boto_client.return_value = mock_textract

        from lambdas.text_extraction import handler as module
        module._textract = mock_textract
        module.handler(base_event, None)

    item = dynamodb.Table("test-documents").get_item(
        Key={"document_id": base_event["document_id"]}
    )["Item"]
    assert item["status"] == "EXTRACTING"
