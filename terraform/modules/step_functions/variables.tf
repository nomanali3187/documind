variable "name_prefix"                  { type = string }
variable "alert_email"                  { type = string; default = "" }
variable "aws_region"                   { type = string }
variable "aws_account_id"               { type = string }
variable "extract_text_lambda_arn"      { type = string }
variable "analyze_document_lambda_arn"  { type = string }
variable "store_results_lambda_arn"     { type = string }
variable "send_notification_lambda_arn" { type = string }
variable "failure_handler_lambda_arn"   { type = string }
