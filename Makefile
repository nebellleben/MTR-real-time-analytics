.PHONY: help infra-init infra-plan infra-apply infra-destroy \
         docker-build docker-push deploy-producer deploy-job schedule-job \
         dbt-run dbt-test dbt-docs local-up local-down clean

         run-producer stop-producer streamlit-run unschedule-job delete-job

SHELL := /bin/bash
PROJECT_ID ?= $(shell gcloud config get-value project 2>/dev/null || echo "your-project-id")
REGION ?= asia-east2
IMAGE_REGISTRY ?= gcr.io/$(PROJECT_ID)
SCHEDULER_SA ?= $(PROJECT_ID)@appspot.gserviceaccount.com

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
	@echo "  make deploy-producer   Build, push, and deploy producer as Cloud Run Job"
	@echo "  make deploy-job        Deploy Cloud Run Job only (no build/push)"
	@echo "  make schedule-job      Create Cloud Scheduler to run job every minute"
	@echo "  make unschedule-job    Delete the Cloud Scheduler job"
	@echo "  make delete-job        Delete the Cloud Run Job"
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

deploy-producer: docker-build docker-push deploy-job schedule-job

deploy-job:
	@echo "Deploying producer as Cloud Run Job..."
	@gcloud run jobs create mtr-producer-job \
		--image=$(IMAGE_REGISTRY)/mtr-producer:latest \
		--region $(REGION) \
		--memory 512Mi \
		--task-timeout 600s \
		--max-retries 1 \
		--set-env-vars PROJECT_ID=$(PROJECT_ID),BIGQUERY_DATASET=mtr_analytics,BIGQUERY_TABLE=raw_arrivals \
		--service-account=$(SCHEDULER_SA) \
		2>/dev/null || gcloud run jobs update mtr-producer-job \
		--image=$(IMAGE_REGISTRY)/mtr-producer:latest \
		--region $(REGION) \
		--memory 512Mi \
		--task-timeout 600s \
		--max-retries 1 \
		--set-env-vars PROJECT_ID=$(PROJECT_ID),BIGQUERY_DATASET=mtr_analytics,BIGQUERY_TABLE=raw_arrivals

schedule-job:
	@echo "Granting run.invoker to $(SCHEDULER_SA)..."
	@gcloud projects add-iam-policy-binding $(PROJECT_ID) \
		--member="serviceAccount:$(SCHEDULER_SA)" \
		--role="roles/run.invoker" --quiet 2>/dev/null || true
	@echo "Creating Cloud Scheduler job (every minute)..."
	@gcloud scheduler jobs create http mtr-producer-schedule \
		--location $(REGION) \
		--schedule "*/1 * * * *" \
		--time-zone "Asia/Hong_Kong" \
		--uri "https://$(REGION)-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$(PROJECT_ID)/jobs/mtr-producer-job:run" \
		--http-method POST \
		--oidc-service-account-email=$(SCHEDULER_SA) \
		2>/dev/null || gcloud scheduler jobs update http mtr-producer-schedule \
		--location $(REGION) \
		--schedule "*/1 * * * *" \
		--time-zone "Asia/Hong_Kong" \
		--uri "https://$(REGION)-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$(PROJECT_ID)/jobs/mtr-producer-job:run" \
		--http-method POST \
		--oidc-service-account-email=$(SCHEDULER_SA)

unschedule-job:
	@echo "Deleting Cloud Scheduler job..."
	gcloud scheduler jobs delete mtr-producer-schedule --location $(REGION) --quiet || true

delete-job:
	@echo "Deleting Cloud Run Job..."
	gcloud run jobs delete mtr-producer-job --region $(REGION) --quiet || true

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
