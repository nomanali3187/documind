output "intake_bucket_name" {
  description = "Upload documents to this S3 bucket to trigger the pipeline"
  value       = module.s3.intake_bucket_name
}

output "results_bucket_name" {
  description = "Processed results archive bucket"
  value       = module.s3.results_bucket_name
}

output "documents_table_name" {
  description = "DynamoDB table tracking document processing state"
  value       = module.dynamodb.documents_table_name
}

output "results_table_name" {
  description = "DynamoDB table storing analysis results"
  value       = module.dynamodb.results_table_name
}

output "state_machine_arn" {
  description = "Step Functions state machine ARN"
  value       = module.step_functions.state_machine_arn
}

output "notification_topic_arn" {
  description = "SNS topic for completion/failure notifications"
  value       = module.step_functions.notification_topic_arn
}
