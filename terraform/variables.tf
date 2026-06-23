variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev | staging | prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Base name for all resources"
  type        = string
  default     = "documind"
}

variable "anthropic_secret_name" {
  description = "Secrets Manager secret holding the Anthropic API key JSON: {\"api_key\": \"sk-...\"}"
  type        = string
  default     = "documind/anthropic-api-key"
}

variable "alert_email" {
  description = "Email address that subscribes to the SNS notification topic"
  type        = string
}

variable "lambda_log_retention_days" {
  description = "CloudWatch log group retention in days"
  type        = number
  default     = 14
}

variable "dist_dir" {
  description = "Path to the built Lambda zip files (relative to terraform root)"
  type        = string
  default     = "../dist"
}
