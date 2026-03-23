.PHONY: help infra-init infra-plan infra-apply infra-destroy \
         docker-build docker-push deploy-producer \
         dbt-run dbt-test dbt-docs local-up local-down clean

         run-producer stop-producer streamlit-run

SHELL := /bin/bash
PROJECT_ID ?= $(shell gcloud config get-value project 2>/dev/null || echo "your-project-id")
REGION ?= asia-east2
IMAGE_REGISTRY ?= gcr.io/$(PROJECT_ID)

help:
	@echo "MTR Real-Time Analytics - Available Commands"
	@echo "============================================="
	@echo ""
	@echo "Infrastructure (Terraform):"
	@echo "  make infra-init        Initialize Terraform"
	@echo "  make infra-plan        Plan Terraform changes"
	@echo "  make infra-apply       Apply Terraform changes"
	@echo "  make infra-destroy     Destroy all infrastructure"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build      Build producer Docker image"
	@echo "  make docker-push       Push images to GCR"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-producer   Deploy producer to Cloud Run"
	@echo "  make run-producer      Run producer locally"
	@echo "  make stop-producer     Stop local producer"
	@echo ""
	@echo "dbt:"
	@echo "  make dbt-run           Run dbt models"
	@echo "  make dbt-test          Run dbt tests"
	@echo "  make dbt-docs          Generate dbt documentation"
	@echo ""
	@echo "Dashboard:"
	@echo "  make streamlit-run    Run Streamlit dashboard locally"
	@echo ""
	@echo "Local Development:"
	@echo "  make local-up          Start local development environment"
	@echo "  make local-down        Stop local development environment"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove generated files"

infra-init:
	@echo "Initializing Terraform..."
	cd terraform && terraform init -upgrade

infra-plan:
	@echo "Planning Terraform changes..."
	cd terraform && terraform plan -var="project_id=$(PROJECT_ID)" -var="region=$(REGION)"

infra-apply:
	@echo "Applying Terraform changes..."
	cd terraform && terraform apply -var="project_id=$(PROJECT_ID)" -var="region=$(REGION)" -auto-approve

infra-destroy:
	@echo "Destroying infrastructure..."
	cd terraform && terraform destroy -var="project_id=$(PROJECT_ID)" -var="region=$(REGION)" -auto-approve

docker-build:
	@echo "Building producer Docker image..."
	docker build -t $(IMAGE_REGISTRY)/mtr-producer:latest ./producer

docker-push:
	@echo "Pushing images to GCR..."
	gcloud auth configure-docker gcr.io --quiet
	docker push $(IMAGE_REGISTRY)/mtr-producer:latest

deploy-producer: docker-build docker-push
	@echo "Deploying producer to Cloud Run..."
	gcloud run deploy mtr-producer \
		--image=$(IMAGE_REGISTRY)/mtr-producer:latest \
		--platform managed \
		--region $(REGION) \
		--memory 512Mi \
		--set-env-vars PROJECT_ID=$(PROJECT_ID),BIGQUERY_DATASET=mtr_analytics,BIGQUERY_TABLE=raw_arrivals \
		--allow-unauthenticated

run-producer:
	@echo "Running producer locally..."
	cd producer && python src/main.py

stop-producer:
	@echo "Stopping local producer..."
	pkill -f "python src/main.py" 2>/dev/null || true

streamlit-run:
	@echo "Running Streamlit dashboard..."
	cd dashboard && streamlit run app.py

dbt-run:
	@echo "Running dbt models..."
	cd dbt_project && BIGQUERY_PROJECT=$(PROJECT_ID) dbt run

dbt-test:
	@echo "Running dbt tests..."
	cd dbt_project && BIGQUERY_PROJECT=$(PROJECT_ID) dbt test

dbt-docs:
	@echo "Generating dbt documentation..."
	cd dbt_project && BIGQUERY_PROJECT=$(PROJECT_ID) dbt docs generate && dbt docs serve

local-up:
	@echo "Starting local development environment..."
	docker-compose up -d
	@echo "Local environment ready!"

local-down:
	@echo "Stopping local development environment..."
	docker-compose down -v

clean:
	@echo "Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".terraform.lock.hcl" -delete 2>/dev/null || true
	rm -rf terraform/terraform.tfstate* 2>/dev/null || true
