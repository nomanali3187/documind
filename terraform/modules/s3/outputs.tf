output "intake_bucket_name" { value = aws_s3_bucket.intake.bucket }
output "intake_bucket_arn"  { value = aws_s3_bucket.intake.arn }
output "results_bucket_name" { value = aws_s3_bucket.results.bucket }
output "results_bucket_arn"  { value = aws_s3_bucket.results.arn }
