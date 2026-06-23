locals {
  # Interpolate Lambda ARNs into the ASL template
  state_machine_definition = templatefile(
    "${path.root}/../statemachine/document_pipeline.asl.json",
    {
      extract_text_lambda_arn      = var.extract_text_lambda_arn
      analyze_document_lambda_arn  = var.analyze_document_lambda_arn
      store_results_lambda_arn     = var.store_results_lambda_arn
      send_notification_lambda_arn = var.send_notification_lambda_arn
      failure_handler_lambda_arn   = var.failure_handler_lambda_arn
    }
  )
}

resource "aws_sfn_state_machine" "document_pipeline" {
  name     = "${var.name_prefix}-document-pipeline"
  role_arn = data.aws_iam_role.step_functions.arn
  definition = local.state_machine_definition

  logging_configuration {
    level                  = "ERROR"
    include_execution_data = true
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
  }

  tracing_configuration {
    enabled = true
  }
}

resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/states/${var.name_prefix}-document-pipeline"
  retention_in_days = 14
}

resource "aws_sns_topic" "notifications" {
  name = "${var.name_prefix}-notifications"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.notifications.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

data "aws_iam_role" "step_functions" {
  name = "${var.name_prefix}-sfn-role"
}
