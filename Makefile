.PHONY: install test lint build clean deploy-dev deploy-prod

PYTHON      := python3
PIP         := pip3
DIST_DIR    := dist
SRC_DIR     := src
LAMBDAS     := document_ingestion text_extraction ai_analysis result_storage notification failure_handler

install:
	$(PIP) install -r requirements/dev.txt

test:
	PYTHONPATH=$(SRC_DIR) pytest tests/unit -v --cov=$(SRC_DIR) --cov-report=term-missing

test-integration:
	PYTHONPATH=$(SRC_DIR) pytest tests/integration -v

lint:
	ruff check $(SRC_DIR) tests

# Build each Lambda into dist/<name>.zip
# Each zip contains: handler.py + shared/ + pip-installed deps
build:
	@rm -rf $(DIST_DIR) && mkdir -p $(DIST_DIR)
	@for lambda in $(LAMBDAS); do \
		echo "Building $$lambda..."; \
		tmpdir=$$(mktemp -d); \
		cp $(SRC_DIR)/lambdas/$$lambda/handler.py $$tmpdir/; \
		cp -r $(SRC_DIR)/shared $$tmpdir/; \
		if [ "$$lambda" = "ai_analysis" ]; then \
			$(PIP) install -r requirements/ai_analysis.txt -t $$tmpdir --quiet; \
		else \
			$(PIP) install -r requirements/base.txt -t $$tmpdir --quiet; \
		fi; \
		(cd $$tmpdir && zip -r $(CURDIR)/$(DIST_DIR)/$$lambda.zip . -x "*.pyc" -x "__pycache__/*") > /dev/null; \
		rm -rf $$tmpdir; \
		echo "  -> $(DIST_DIR)/$$lambda.zip"; \
	done

clean:
	rm -rf $(DIST_DIR) .pytest_cache **/__pycache__ **/*.pyc .coverage

# Terraform helpers
tf-init-dev:
	cd terraform/environments/dev && terraform init

tf-plan-dev: build
	cd terraform/environments/dev && terraform plan

deploy-dev: build
	cd terraform/environments/dev && terraform apply -auto-approve

tf-init-prod:
	cd terraform/environments/prod && terraform init

deploy-prod: build
	cd terraform/environments/prod && terraform plan
	@echo "Review the plan above. Run 'cd terraform/environments/prod && terraform apply' to confirm."
