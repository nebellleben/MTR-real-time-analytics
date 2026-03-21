terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "gcs" {
    bucket = "mtr-analytics-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_service_account" "mtr_sa" {
  account_id   = "mtr-analytics-sa"
  display_name = "MTR Analytics Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "mtr_sa_roles" {
  for_each = toset([
    "roles/bigquery.dataEditor",
    "roles/storage.objectAdmin",
    "roles/pubsub.admin",
    "roles/dataflow.admin",
    "roles/dataflow.worker",
    "roles/logging.logWriter",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.mtr_sa.email}"
}

resource "google_storage_bucket" "data_lake" {
  name          = "${var.project_id}-mtr-data-lake"
  location      = var.region
  project       = var.project_id
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket" "dataflow_staging" {
  name          = "${var.project_id}-dataflow-staging"
  location      = var.region
  project       = var.project_id
  force_destroy = true

  uniform_bucket_level_access = true
}

resource "google_bigquery_dataset" "dataset" {
  dataset_id  = "mtr_analytics"
  project     = var.project_id
  location    = var.region

  delete_contents_on_destroy = true

  labels = {
    managed_by = "terraform"
  }
}

resource "google_bigquery_table" "raw_arrivals" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = "raw_arrivals"
  project    = var.project_id

  time_partitioning {
    field = "ingestion_date"
    type  = "DAY"
  }

  clustering = ["line_code", "station_code"]

  schema = <<EOF
[
  {"name": "arrival_id", "type": "STRING", "mode": "NULLABLE"},
  {"name": "line_code", "type": "STRING", "mode": "NULLABLE"},
  {"name": "station_code", "type": "STRING", "mode": "NULLABLE"},
  {"name": "station_name", "type": "STRING", "mode": "NULLABLE"},
  {"name": "dest_station", "type": "STRING", "mode": "NULLABLE"},
  {"name": "arrival_time", "type": "TIMESTAMP", "mode": "NULLABLE"},
  {"name": "time_remaining", "type": "INT64", "mode": "NULLABLE"},
  {"name": "platform", "type": "STRING", "mode": "NULLABLE"},
  {"name": "sequence", "type": "INT64", "mode": "NULLABLE"},
  {"name": "is_delayed", "type": "BOOLEAN", "mode": "NULLABLE"},
  {"name": "delay_seconds", "type": "INT64", "mode": "NULLABLE"},
  {"name": "ingestion_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "ingestion_date", "type": "DATE", "mode": "REQUIRED"}
]
EOF
}

resource "google_bigquery_table" "dim_lines" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = "dim_lines"
  project    = var.project_id

  schema = <<EOF
[
  {"name": "line_code", "type": "STRING", "mode": "REQUIRED"},
  {"name": "line_name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "line_color", "type": "STRING", "mode": "NULLABLE"},
  {"name": "is_urban", "type": "BOOLEAN", "mode": "NULLABLE"}
]
EOF
}

resource "google_bigquery_table" "dim_stations" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = "dim_stations"
  project    = var.project_id
  schema = <<EOF
[
  {"name": "station_code", "type": "STRING", "mode": "REQUIRED"},
  {"name": "station_name", "type": "STRING", "mode": "REQUIRED"},
  {"name": "line_code", "type": "STRING", "mode": "REQUIRED"},
  {"name": "district", "type": "STRING", "mode": "NULLABLE"},
  {"name": "latitude", "type": "FLOAT64", "mode": "NULLABLE"},
  {"name": "longitude", "type": "FLOAT64", "mode": "NULLABLE"}
]
EOF
}

resource "google_pubsub_topic" "mtr_arrivals" {
  name    = "mtr-arrivals"
  project = var.project_id

  message_retention_duration = "86400s"
}

resource "google_pubsub_subscription" "dataflow_sub" {
  name    = "mtr-arrivals-dataflow"
  project = var.project_id
  topic   = google_pubsub_topic.mtr_arrivals.name

  ack_deadline_seconds = 60
  message_retention_duration = "604800s"
}

resource "google_dataflow_flex_template_job" "streaming_job" {
  provider                = google-beta
  name                    = "mtr-streaming-pipeline"
  project                 = var.project_id
  region                  = var.region
  container_spec_gcs_path = "gs://${google_storage_bucket.dataflow_staging.name}/templates/streaming_template.json"

  parameters = {
    inputSubscription = google_pubsub_subscription.dataflow_sub.id
    outputTable       = "${var.project_id}:${google_bigquery_dataset.dataset.dataset_id}.${google_bigquery_table.raw_arrivals.table_id}"
    tempLocation      = "gs://${google_storage_bucket.dataflow_staging.name}/temp"
  }

  on_delete = "cancel"
}

resource "google_cloud_run_service" "producer" {
  name     = "mtr-producer"
  location = var.region
  project  = var.project_id

  template {
    spec {
      service_account_name = google_service_account.mtr_sa.email
      containers {
        image = "gcr.io/${var.project_id}/mtr-producer:latest"
        env {
          name  = "PUBSUB_TOPIC"
          value = google_pubsub_topic.mtr_arrivals.name
        }
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "producer_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloud_run_service.producer.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.mtr_sa.email}"
}

resource "google_cloud_scheduler_job" "producer_trigger" {
  name             = "mtr-producer-trigger"
  project          = var.project_id
  region           = var.region
  schedule         = "*/1 * * * *"
  time_zone        = "Asia/Hong_Kong"
  attempt_deadline = "600s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.producer.status[0].url}/poll"
    oidc_token {
      service_account_email = google_service_account.mtr_sa.email
    }
  }
}

output "project_id" {
  value = var.project_id
}

output "region" {
  value = var.region
}

output "pubsub_topic" {
  value = google_pubsub_topic.mtr_arrivals.name
}

output "bucket_name" {
  value = google_storage_bucket.data_lake.name
}

output "dataset_id" {
  value = google_bigquery_dataset.dataset.dataset_id
}

output "cloud_run_url" {
  value = google_cloud_run_service.producer.status[0].url
}
