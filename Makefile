.PHONY: help infra-init infra-plan infra-apply infra-destroy \
        docker-build docker-push deploy-producer deploy-dataflow \
        dbt-run dbt-test dbt-docs local-up local-down clean

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
	@echo "  make docker-build      Build all Docker images"
	@echo "  make docker-push       Push images to GCR"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-producer   Deploy producer to Cloud Run"
	@echo "  make deploy-dataflow   Deploy Dataflow streaming job"
	@echo "  make deploy-all        Deploy all services"
	@echo ""
	@echo "dbt:"
	@echo "  make dbt-run           Run dbt models"
	@echo "  make dbt-test          Run dbt tests"
	@echo "  make dbt-docs          Generate dbt documentation"
	@echo ""
	@echo "Local Development:"
	@echo "  make local-up          Start local environment"
	@echo "  make local-down        Stop local environment"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean             Clean generated files"

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
	@echo "Building Docker images..."
	docker build -t $(IMAGE_REGISTRY)/mtr-producer:latest ./producer
	docker build -t $(IMAGE_REGISTRY)/mtr-dataflow:latest ./consumer

docker-push:
	@echo "Pushing images to GCR..."
	gcloud auth configure-docker gcr.io --quiet
	docker push $(IMAGE_REGISTRY)/mtr-producer:latest
	docker push $(IMAGE_REGISTRY)/mtr-dataflow:latest

deploy-producer: docker-build docker-push
	@echo "Deploying producer to Cloud Run..."
	cd terraform && terraform apply -var="project_id=$(PROJECT_ID)" -var="region=$(REGION)" -target=google_cloud_run_service.producer -auto-approve

deploy-dataflow: docker-build docker-push
	@echo "Deploying Dataflow streaming job..."
	python consumer/src/main.py \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--temp_location=gs://$(PROJECT_ID)-mtr-data-lake/temp \
		--staging_location=gs://$(PROJECT_ID)-mtr-data-lake/staging \
		--runner=DataflowRunner \
		--streaming \
		--job_name=mtr-arrivals-streaming

deploy-all: infra-apply deploy-dataflow
	@echo "All services deployed!"

dbt-run:
	@echo "Running dbt models..."
	cd dbt_project && dbt run

dbt-test:
	@echo "Running dbt tests..."
	cd dbt_project && dbt test

dbt-docs:
	@echo "Generating dbt documentation..."
	cd dbt_project && dbt docs generate && dbt docs serve

local-up:
	@echo "Starting local development environment..."
	docker-compose up -d
	@echo "Local environment ready!"
	@echo "Pub/Sub emulator: localhost:8085"
	@echo "BigQuery emulator: localhost:9050"

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
