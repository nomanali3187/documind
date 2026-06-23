# DocuMind — Intelligent Document Processor

Drop any document (invoice, contract, insurance form) into S3. An event-driven serverless pipeline
extracts text via AWS Textract, classifies and structures the data with Claude AI, stores results in
DynamoDB, and notifies you when done. Zero servers. Full audit trail. Scales to zero.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DocuMind Pipeline                              │
│                                                                         │
│  User/App                                                               │
│     │                                                                   │
│     ▼                                                                   │
│  S3 Intake Bucket ──(Object Created)──► EventBridge Rule               │
│                                               │                        │
│                                               ▼                        │
│                                    Lambda: document-ingestion          │
│                                    • Creates DynamoDB record           │
│                                    • Starts Step Functions execution   │
│                                               │                        │
│                          ┌────────────────────┘                        │
│                          ▼                                              │
│                ┌─── Step Functions ───────────────────┐               │
│                │                                       │               │
│                │  ┌─────────────────┐                  │               │
│                │  │ 1. ExtractText  │                  │               │
│                │  │   (Textract)    │                  │               │
│                │  │  raw_text +     │                  │               │
│                │  │  key_values     │                  │               │
│                │  └────────┬────────┘                  │               │
│                │           │ on error ──► HandleFailure│               │
│                │  ┌────────▼────────┐                  │               │
│                │  │ 2. AnalyzeDoc   │                  │               │
│                │  │  (Claude AI)    │                  │               │
│                │  │  document_type  │                  │               │
│                │  │  extracted_fields│                 │               │
│                │  │  risk_flags     │                  │               │
│                │  └────────┬────────┘                  │               │
│                │           │ on error ──► HandleFailure│               │
│                │  ┌────────▼────────┐                  │               │
│                │  │ 3. StoreResults │                  │               │
│                │  │  (DynamoDB)     │                  │               │
│                │  └────────┬────────┘                  │               │
│                │  ┌────────▼────────┐                  │               │
│                │  │ 4. Notify (SNS) │                  │               │
│                │  └─────────────────┘                  │               │
│                └───────────────────────────────────────┘               │
│                                                                         │
│  DynamoDB Tables          SNS Topic             CloudWatch Logs        │
│  ├── documents            └── email/webhook     └── structured JSON    │
│  └── results                  subscribers           with corr. IDs     │
└─────────────────────────────────────────────────────────────────────────┘
```

## What Claude AI Returns

For every document, the AI analysis Lambda produces:

```json
{
  "document_type": "INVOICE",
  "extracted_fields": {
    "invoice_number": "INV-12345",
    "vendor": "Acme Corp",
    "total_amount": "$1,500.00",
    "due_date": "2024-06-30"
  },
  "summary": "Invoice from Acme Corp for software services totaling $1,500, due June 30.",
  "risk_flags": ["Due date is within 7 days"],
  "confidence_score": 0.94
}
```

Supported document types: `INVOICE`, `CONTRACT`, `INSURANCE_FORM`, `GENERAL`, `UNKNOWN`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| AI | Anthropic Claude (claude-sonnet-4-6) |
| OCR | AWS Textract (FORMS + TABLES features) |
| Orchestration | AWS Step Functions (ASL state machine) |
| Compute | AWS Lambda (6 functions) |
| Storage | DynamoDB (2 tables with GSIs) |
| Eventing | EventBridge (S3 → pipeline trigger) |
| Notifications | SNS (completion + failure alerts) |
| Secrets | AWS Secrets Manager |
| IaC | Terraform (5 modules) |
| CI/CD | GitHub Actions (OIDC auth, zero long-lived keys) |
| Observability | CloudWatch structured logs, X-Ray tracing |

## Project Structure

```
documind/
├── src/
│   ├── lambdas/
│   │   ├── document_ingestion/   # EventBridge trigger → starts SFN
│   │   ├── text_extraction/      # Textract OCR
│   │   ├── ai_analysis/          # Claude AI classification
│   │   ├── result_storage/       # DynamoDB persistence
│   │   ├── notification/         # SNS publish
│   │   └── failure_handler/      # Error + FAILED status
│   └── shared/
│       ├── config.py             # Env-var driven config
│       ├── logger.py             # Structured JSON logger w/ correlation IDs
│       └── models.py             # Document + AnalysisResult dataclasses
├── statemachine/
│   └── document_pipeline.asl.json  # Step Functions state machine
├── terraform/
│   ├── main.tf                   # Root module wiring
│   ├── modules/
│   │   ├── s3/                   # Intake + results buckets
│   │   ├── lambda/               # Reusable Lambda module
│   │   ├── step_functions/       # State machine + SNS topic
│   │   ├── dynamodb/             # documents + results tables
│   │   └── iam/                  # Least-privilege roles
│   └── environments/
│       ├── dev/                  # Dev tfvars + backend config
│       └── prod/                 # Prod tfvars + backend config
├── tests/
│   ├── unit/                     # pytest + moto (no real AWS needed)
│   └── integration/              # Real AWS, requires deployed env
├── requirements/
│   ├── base.txt                  # boto3
│   ├── ai_analysis.txt           # + anthropic SDK
│   └── dev.txt                   # + pytest, moto, ruff
└── Makefile                      # install / test / build / deploy-dev
```

## Getting Started

### Prerequisites

- Python 3.12+
- Terraform >= 1.7
- AWS CLI configured (`aws configure`)
- Anthropic API key

### 1. Install dependencies

```bash
make install
```

### 2. Run unit tests (no AWS account needed)

```bash
make test
```

### 3. Store your Anthropic API key in Secrets Manager

```bash
aws secretsmanager create-secret \
  --name "documind/anthropic-api-key" \
  --secret-string '{"api_key": "sk-ant-YOUR-KEY-HERE"}'
```

### 4. Create Terraform state bucket

```bash
aws s3 mb s3://documind-terraform-state-dev --region us-east-1
aws dynamodb create-table \
  --table-name documind-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 5. Deploy to dev

```bash
make build
make deploy-dev
```

### 6. Upload a test document

```bash
# Get the intake bucket name from Terraform output
BUCKET=$(cd terraform/environments/dev && terraform output -raw intake_bucket_name)

aws s3 cp your-invoice.pdf s3://$BUCKET/uploads/
```

Watch the Step Functions console — the execution should complete in ~15 seconds.

## Architecture Patterns Demonstrated

- **Event-Driven Architecture** — S3 → EventBridge → Lambda → Step Functions. No polling, no cron.
- **Serverless Pipeline** — Zero servers, zero idle cost. Scales to zero when not in use.
- **Step Functions Orchestration** — Each step has retry logic and a Catch that routes failures to `HandleFailure`. No silent failures.
- **Structured Logging with Correlation IDs** — Every log entry across all 6 Lambdas carries the same `correlation_id`, making distributed traces trivial to reconstruct in CloudWatch Insights.
- **Least-Privilege IAM** — One role per concern (Lambda role, Step Functions role). Each policy is scoped to exact resource ARN patterns.
- **Secret Management** — API key never in env vars or code. Fetched from Secrets Manager at cold start and cached for the Lambda lifetime.
- **Terraform Modules** — Infrastructure is composable. Each module (`s3`, `lambda`, `dynamodb`, etc.) is independently versioned and reusable.

## CI/CD

| Trigger | Job |
|---------|-----|
| Pull Request | Unit tests, lint, `terraform validate` |
| Push to `main` | Full deploy to `dev` via OIDC (no long-lived AWS keys) |
| Manual trigger | Deploy to `dev` or `prod` with environment approval gate |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCUMENTS_TABLE` | DynamoDB table for document state | `documind-documents` |
| `RESULTS_TABLE` | DynamoDB table for analysis results | `documind-results` |
| `STEP_FUNCTIONS_ARN` | State machine ARN | — |
| `NOTIFICATION_TOPIC_ARN` | SNS topic ARN | — |
| `ANTHROPIC_SECRET_NAME` | Secrets Manager secret name | `documind/anthropic-api-key` |
| `CLAUDE_MODEL_ID` | Claude model to use | `claude-sonnet-4-6` |
| `ENVIRONMENT` | Deployment environment | `dev` |
