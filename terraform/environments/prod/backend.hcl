# Run: terraform init -backend-config=backend.hcl
bucket         = "documind-terraform-state-prod"
key            = "documind/prod/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "documind-terraform-locks"
