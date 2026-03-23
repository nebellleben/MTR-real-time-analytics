variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-east2"
}

variable "bigquery_dataset" {
  description = "BigQuery dataset name"
  type        = string
  default     = "mtr_analytics"
}

variable "storage_bucket" {
  description = "GCS bucket name for data lake"
  type        = string
  default     = "mtr-data-lake"
}
