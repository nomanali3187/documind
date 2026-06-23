resource "aws_dynamodb_table" "documents" {
  name         = "${var.name_prefix}-documents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "document_id"

  attribute {
    name = "document_id"
    type = "S"
  }

  # GSI for querying by tenant
  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "uploaded_at"
    type = "S"
  }

  global_secondary_index {
    name            = "tenant-uploaded-index"
    hash_key        = "tenant_id"
    range_key       = "uploaded_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery { enabled = true }
  deletion_protection_enabled = false
}

resource "aws_dynamodb_table" "results" {
  name         = "${var.name_prefix}-results"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "document_id"

  attribute {
    name = "document_id"
    type = "S"
  }

  # GSI for querying by document type
  attribute {
    name = "document_type"
    type = "S"
  }

  attribute {
    name = "analyzed_at"
    type = "S"
  }

  global_secondary_index {
    name            = "type-analyzed-index"
    hash_key        = "document_type"
    range_key       = "analyzed_at"
    projection_type = "ALL"
  }

  point_in_time_recovery { enabled = true }
  deletion_protection_enabled = false
}
