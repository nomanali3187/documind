import os
from dataclasses import dataclass, field


@dataclass
class Config:
    aws_region: str = field(default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1"))
    documents_table: str = field(default_factory=lambda: os.environ.get("DOCUMENTS_TABLE", "documind-documents"))
    results_table: str = field(default_factory=lambda: os.environ.get("RESULTS_TABLE", "documind-results"))
    notification_topic_arn: str = field(default_factory=lambda: os.environ.get("NOTIFICATION_TOPIC_ARN", ""))
    step_functions_arn: str = field(default_factory=lambda: os.environ.get("STEP_FUNCTIONS_ARN", ""))
    # Secrets Manager secret name that holds the Anthropic API key
    anthropic_secret_name: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_SECRET_NAME", "documind/anthropic-api-key"))
    claude_model_id: str = field(default_factory=lambda: os.environ.get("CLAUDE_MODEL_ID", "claude-sonnet-4-6"))
    environment: str = field(default_factory=lambda: os.environ.get("ENVIRONMENT", "dev"))


config = Config()
