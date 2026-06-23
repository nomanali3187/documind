data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# CloudWatch Logs
resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# X-Ray tracing
resource "aws_iam_role_policy_attachment" "xray" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Inline policy: DynamoDB, S3, Textract, SNS, Step Functions, Secrets Manager
data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid     = "DynamoDB"
    actions = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"]
    resources = [
      var.documents_table_arn,
      "${var.documents_table_arn}/index/*",
      var.results_table_arn,
      "${var.results_table_arn}/index/*",
    ]
  }

  statement {
    sid       = "S3Read"
    actions   = ["s3:GetObject"]
    resources = ["${var.intake_bucket_arn}/*"]
  }

  statement {
    sid       = "Textract"
    actions   = ["textract:AnalyzeDocument", "textract:DetectDocumentText"]
    resources = ["*"]
  }

  statement {
    sid       = "SNSPublish"
    actions   = ["sns:Publish"]
    resources = ["arn:aws:sns:${var.aws_region}:${var.aws_account_id}:${var.name_prefix}-*"]
  }

  statement {
    sid       = "StepFunctions"
    actions   = ["states:StartExecution"]
    resources = ["arn:aws:states:${var.aws_region}:${var.aws_account_id}:stateMachine:${var.name_prefix}-*"]
  }

  statement {
    sid       = "SecretsManager"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.anthropic_secret_name}*"]
  }
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name   = "${var.name_prefix}-lambda-permissions"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

# Step Functions execution role
data "aws_iam_policy_document" "sfn_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "step_functions" {
  name               = "${var.name_prefix}-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume_role.json
}

data "aws_iam_policy_document" "sfn_permissions" {
  statement {
    sid       = "InvokeLambdas"
    actions   = ["lambda:InvokeFunction"]
    resources = ["arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.name_prefix}-*"]
  }

  statement {
    sid       = "CloudWatchLogs"
    actions   = ["logs:CreateLogDelivery", "logs:GetLogDelivery", "logs:UpdateLogDelivery",
                 "logs:DeleteLogDelivery", "logs:ListLogDeliveries", "logs:PutLogEvents",
                 "logs:PutResourcePolicy", "logs:DescribeResourcePolicies", "logs:DescribeLogGroups"]
    resources = ["*"]
  }

  statement {
    sid       = "XRay"
    actions   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules",
                 "xray:GetSamplingTargets"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn_permissions" {
  name   = "${var.name_prefix}-sfn-permissions"
  role   = aws_iam_role.step_functions.id
  policy = data.aws_iam_policy_document.sfn_permissions.json
}
