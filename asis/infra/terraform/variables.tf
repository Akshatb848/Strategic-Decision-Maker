variable "project_id" {
  description = "GCP project ID where all ASIS resources will be deployed."
  type        = string
}

variable "region" {
  description = "GCP region for all resource deployments."
  type        = string
  default     = "asia-south1"
}

variable "environment" {
  description = "Deployment environment. Controls HA settings, deletion protection, and tier selection."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "db_password" {
  description = "Password for the Cloud SQL 'asis' database user. Must be stored securely and never committed."
  type        = string
  sensitive   = true
}
