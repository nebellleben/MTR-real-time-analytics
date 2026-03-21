variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "region" {
  type        = string
  description = "GCP Region"
  default     = "asia-east2"
}

variable "zone" {
  type        = string
  description = "GCP Zone"
  default     = "asia-east2-a"
}

variable "gke_node_count" {
  type        = number
  description = "Number of GKE nodes"
  default     = 3
}

variable "gke_machine_type" {
  type        = string
  description = "GKE node machine type"
  default     = "e2-standard-4"
}

variable "kafka_replication_factor" {
  type        = number
  description = "Kafka replication factor"
  default     = 3
}

variable "kafka_partitions" {
  type        = number
  description = "Number of Kafka partitions"
  default     = 6
}

variable "kafka_topic" {
  type        = string
  description = "Kafka topic name"
  default     = "mtr-arrivals"
}
