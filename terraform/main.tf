locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# ── S3 ──────────────────────────────────────────────────────────────────────
module "s3" {
  source      = "./modules/s3"
  name_prefix = local.name_prefix
}

# ── DynamoDB ─────────────────────────────────────────────────────────────────
module "dynamodb" {
  source      = "./modules/dynamodb"
  name_prefix = local.name_prefix
}

# ── IAM ──────────────────────────────────────────────────────────────────────
module "iam" {
  source                = "./modules/iam"
  name_prefix           = local.name_prefix
  aws_region            = var.aws_region
  aws_account_id        = data.aws_caller_identity.current.account_id
  intake_bucket_arn     = module.s3.intake_bucket_arn
  documents_table_arn   = module.dynamodb.documents_table_arn
  results_table_arn     = module.dynamodb.results_table_arn
  anthropic_secret_name = var.anthropic_secret_name
}

# ── Lambda ───────────────────────────────────────────────────────────────────
module "lambda_document_ingestion" {
  source            = "./modules/lambda"
  function_name     = "${local.name_prefix}-document-ingestion"
  zip_path          = "${var.dist_dir}/document_ingestion.zip"
  handler           = "handler.handler"
  role_arn          = module.iam.lambda_role_arn
  log_retention     = var.lambda_log_retention_days
  environment_vars  = {
    ENVIRONMENT        = var.environment
    DOCUMENTS_TABLE    = module.dynamodb.documents_table_name
    STEP_FUNCTIONS_ARN = module.step_functions.state_machine_arn
  }
}

module "lambda_text_extraction" {
  source            = "./modules/lambda"
  function_name     = "${local.name_prefix}-text-extraction"
  zip_path          = "${var.dist_dir}/text_extraction.zip"
  handler           = "handler.handler"
  role_arn          = module.iam.lambda_role_arn
  log_retention     = var.lambda_log_retention_days
  environment_vars  = {
    ENVIRONMENT     = var.environment
    DOCUMENTS_TABLE = module.dynamodb.documents_table_name
  }
}

module "lambda_ai_analysis" {
  source            = "./modules/lambda"
  function_name     = "${local.name_prefix}-ai-analysis"
  zip_path          = "${var.dist_dir}/ai_analysis.zip"
  handler           = "handler.handler"
  role_arn          = module.iam.lambda_role_arn
  timeout           = 120
  memory_mb         = 512
  log_retention     = var.lambda_log_retention_days
  environment_vars  = {
    ENVIRONMENT           = var.environment
    DOCUMENTS_TABLE       = module.dynamodb.documents_table_name
    ANTHROPIC_SECRET_NAME = var.anthropic_secret_name
    CLAUDE_MODEL_ID       = "claude-sonnet-4-6"
  }
}

module "lambda_result_storage" {
  source            = "./modules/lambda"
  function_name     = "${local.name_prefix}-result-storage"
  zip_path          = "${var.dist_dir}/result_storage.zip"
  handler           = "handler.handler"
  role_arn          = module.iam.lambda_role_arn
  log_retention     = var.lambda_log_retention_days
  environment_vars  = {
    ENVIRONMENT     = var.environment
    DOCUMENTS_TABLE = module.dynamodb.documents_table_name
    RESULTS_TABLE   = module.dynamodb.results_table_name
  }
}

module "lambda_notification" {
  source            = "./modules/lambda"
  function_name     = "${local.name_prefix}-notification"
  zip_path          = "${var.dist_dir}/notification.zip"
  handler           = "handler.handler"
  role_arn          = module.iam.lambda_role_arn
  log_retention     = var.lambda_log_retention_days
  environment_vars  = {
    ENVIRONMENT            = var.environment
    NOTIFICATION_TOPIC_ARN = module.step_functions.notification_topic_arn
  }
}

module "lambda_failure_handler" {
  source            = "./modules/lambda"
  function_name     = "${local.name_prefix}-failure-handler"
  zip_path          = "${var.dist_dir}/failure_handler.zip"
  handler           = "handler.handler"
  role_arn          = module.iam.lambda_role_arn
  log_retention     = var.lambda_log_retention_days
  environment_vars  = {
    ENVIRONMENT            = var.environment
    DOCUMENTS_TABLE        = module.dynamodb.documents_table_name
    NOTIFICATION_TOPIC_ARN = module.step_functions.notification_topic_arn
  }
}

# ── Step Functions ───────────────────────────────────────────────────────────
module "step_functions" {
  source      = "./modules/step_functions"
  name_prefix = local.name_prefix
  alert_email = var.alert_email
  aws_region  = var.aws_region
  aws_account_id = data.aws_caller_identity.current.account_id

  extract_text_lambda_arn      = module.lambda_text_extraction.function_arn
  analyze_document_lambda_arn  = module.lambda_ai_analysis.function_arn
  store_results_lambda_arn     = module.lambda_result_storage.function_arn
  send_notification_lambda_arn = module.lambda_notification.function_arn
  failure_handler_lambda_arn   = module.lambda_failure_handler.function_arn
}

# ── EventBridge rule — S3 upload → ingestion Lambda ─────────────────────────
resource "aws_cloudwatch_event_rule" "s3_upload" {
  name        = "${local.name_prefix}-s3-upload"
  description = "Fires when an object is created in the intake bucket"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = { name = [module.s3.intake_bucket_name] }
    }
  })
}

resource "aws_cloudwatch_event_target" "ingestion_lambda" {
  rule = aws_cloudwatch_event_rule.s3_upload.name
  arn  = module.lambda_document_ingestion.function_arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_document_ingestion.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_upload.arn
}

# ── Data sources ─────────────────────────────────────────────────────────────
data "aws_caller_identity" "current" {}
