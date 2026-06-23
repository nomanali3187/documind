resource "aws_s3_bucket" "intake" {
  bucket = "${var.name_prefix}-intake-${random_id.suffix.hex}"
}

resource "aws_s3_bucket" "results" {
  bucket = "${var.name_prefix}-results-${random_id.suffix.hex}"
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_versioning" "intake" {
  bucket = aws_s3_bucket.intake.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "intake" {
  bucket = aws_s3_bucket.intake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "results" {
  bucket = aws_s3_bucket.results.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "intake" {
  bucket                  = aws_s3_bucket.intake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "results" {
  bucket                  = aws_s3_bucket.results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable EventBridge notifications so S3 Object Created events flow to EventBridge
resource "aws_s3_bucket_notification" "intake_eventbridge" {
  bucket      = aws_s3_bucket.intake.id
  eventbridge = true
}
