resource "aws_lambda_function" "this" {
  function_name = var.function_name
  filename      = var.zip_path
  handler       = var.handler
  runtime       = "python3.12"
  role          = var.role_arn
  timeout       = var.timeout
  memory_size   = var.memory_mb

  source_code_hash = filebase64sha256(var.zip_path)

  environment {
    variables = var.environment_vars
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [aws_cloudwatch_log_group.this]
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention
}
