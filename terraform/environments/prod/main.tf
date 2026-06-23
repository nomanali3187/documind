module "documind" {
  source = "../../"

  environment   = "prod"
  aws_region    = var.aws_region
  project_name  = "documind"
  alert_email   = var.alert_email

  anthropic_secret_name     = "documind/anthropic-api-key"
  lambda_log_retention_days = 30
  dist_dir                  = "../../../dist"
}

variable "aws_region"  { default = "us-east-1" }
variable "alert_email" {}
