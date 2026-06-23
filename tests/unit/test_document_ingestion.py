import json
import sys
import os

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


def _create_documents_table(dynamodb):
    dynamodb.create_table(
        TableName="test-documents",
        KeySchema=[{"AttributeName": "document_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "document_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


@mock_aws
def test_handler_creates_document_record_and_starts_sfn():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    _create_documents_table(dynamodb)

    sfn = boto3.client("stepfunctions", region_name="us-east-1")
    iam = boto3.client("iam", region_name="us-east-1")
    role = iam.create_role(
        RoleName="test-sfn-role",
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "states.amazonaws.com"}, "Action": "sts:AssumeRole"}],
        }),
    )
    state_machine = sfn.create_state_machine(
        name="test-pipeline",
        definition=json.dumps({"Comment": "test", "StartAt": "Done", "States": {"Done": {"Type": "Succeed"}}}),
        roleArn=role["Role"]["Arn"],
    )
    os.environ["STEP_FUNCTIONS_ARN"] = state_machine["stateMachineArn"]

    from lambdas.document_ingestion.handler import handler

    event = {
        "detail": {
            "bucket": {"name": "test-bucket"},
            "object": {"key": "uploads/invoice.pdf"},
        }
    }

    result = handler(event, None)

    assert "document_id" in result
    assert "execution_arn" in result

    table = dynamodb.Table("test-documents")
    item = table.get_item(Key={"document_id": result["document_id"]})["Item"]
    assert item["s3_bucket"] == "test-bucket"
    assert item["s3_key"] == "uploads/invoice.pdf"
    assert item["status"] == "PENDING"
    assert item["file_name"] == "invoice.pdf"


@mock_aws
def test_handler_raises_on_missing_s3_coordinates():
    from lambdas.document_ingestion.handler import handler

    with pytest.raises(ValueError, match="Missing S3"):
        handler({"detail": {}}, None)


@mock_aws
def test_handler_parses_direct_s3_record_format():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    _create_documents_table(dynamodb)

    sfn = boto3.client("stepfunctions", region_name="us-east-1")
    iam = boto3.client("iam", region_name="us-east-1")
    role = iam.create_role(
        RoleName="test-sfn-role-2",
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "states.amazonaws.com"}, "Action": "sts:AssumeRole"}],
        }),
    )
    state_machine = sfn.create_state_machine(
        name="test-pipeline-2",
        definition=json.dumps({"Comment": "test", "StartAt": "Done", "States": {"Done": {"Type": "Succeed"}}}),
        roleArn=role["Role"]["Arn"],
    )
    os.environ["STEP_FUNCTIONS_ARN"] = state_machine["stateMachineArn"]

    from lambdas.document_ingestion.handler import handler

    event = {
        "Records": [{"s3": {"bucket": {"name": "direct-bucket"}, "object": {"key": "contracts/nda.pdf"}}}]
    }

    result = handler(event, None)
    assert "document_id" in result
