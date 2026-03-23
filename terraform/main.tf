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
  {"name": "line_name", "type": "STRING", "mode": "NULLABLE"},
  {"name": "station_code", "type": "STRING", "mode": "NULLABLE"},
  {"name": "dest_station", "type": "STRING", "mode": "NULLABLE"},
  {"name": "platform", "type": "STRING", "mode": "NULLABLE"},
  {"name": "sequence", "type": "INT64", "mode": "NULLABLE"},
  {"name": "arrival_time", "type": "TIMESTAMP", "mode": "NULLABLE"},
  {"name": "time_remaining", "type": "INT64", "mode": "NULLABLE"},
  {"name": "direction", "type": "STRING", "mode": "NULLABLE"},
  {"name": "ingestion_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
  {"name": "ingestion_date", "type": "DATE", "mode": "REQUIRED"}
]
EOF
}
