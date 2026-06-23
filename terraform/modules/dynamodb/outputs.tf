output "documents_table_name" { value = aws_dynamodb_table.documents.name }
output "documents_table_arn"  { value = aws_dynamodb_table.documents.arn }
output "results_table_name"   { value = aws_dynamodb_table.results.name }
output "results_table_arn"    { value = aws_dynamodb_table.results.arn }
