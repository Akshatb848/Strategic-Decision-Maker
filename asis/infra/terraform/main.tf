terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "asis-tf-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ── VPC ───────────────────────────────────────────────────────────────────────

resource "google_compute_network" "asis_vpc" {
  name                    = "asis-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "asis_subnet" {
  name          = "asis-subnet"
  ip_cidr_range = "10.0.0.0/20"
  region        = var.region
  network       = google_compute_network.asis_vpc.id

  private_ip_google_access = true
}

resource "google_vpc_access_connector" "serverless_connector" {
  name          = "asis-vpc-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.asis_vpc.name
  min_instances = 2
  max_instances = 10
}

# ── Cloud SQL (PostgreSQL 16) ─────────────────────────────────────────────────

resource "google_sql_database_instance" "asis_primary" {
  name             = "asis-primary"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-n1-standard-2"
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_size         = 50
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.asis_vpc.id
      require_ssl     = true
    }

    database_flags {
      name  = "max_connections"
      value = "200"
    }
  }

  deletion_protection = var.environment == "production"
}

resource "google_sql_database" "asis_main" {
  name     = "asis_main"
  instance = google_sql_database_instance.asis_primary.name
}

resource "google_sql_database" "langfuse_db" {
  name     = "langfuse_db"
  instance = google_sql_database_instance.asis_primary.name
}

resource "google_sql_database" "n8n_db" {
  name     = "n8n_db"
  instance = google_sql_database_instance.asis_primary.name
}

resource "google_sql_user" "asis_user" {
  name     = "asis"
  instance = google_sql_database_instance.asis_primary.name
  password = var.db_password
}

# ── Memorystore (Redis) ───────────────────────────────────────────────────────

resource "google_redis_instance" "asis_cache" {
  name           = "asis-cache"
  tier           = var.environment == "production" ? "STANDARD_HA" : "BASIC"
  memory_size_gb = 2
  region         = var.region

  authorized_network = google_compute_network.asis_vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version     = "REDIS_7_0"
  display_name      = "ASIS Redis Cache"
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }
}

# ── Cloud Run Services ────────────────────────────────────────────────────────

locals {
  image_base = "${var.region}-docker.pkg.dev/${var.project_id}/asis"
  common_env = [
    { name = "ENVIRONMENT", value = var.environment },
    { name = "GCP_PROJECT_ID", value = var.project_id },
    { name = "GCP_REGION", value = var.region },
  ]
}

resource "google_cloud_run_v2_service" "backend" {
  name     = "asis-backend-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.backend_sa.email

    vpc_access {
      connector = google_vpc_access_connector.serverless_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 20
    }

    containers {
      image = "${local.image_base}/backend:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      ports {
        container_port = 8000
      }

      dynamic "env" {
        for_each = local.common_env
        content {
          name  = env.value.name
          value = env.value.value
        }
      }

      # Secrets from Secret Manager
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.anthropic_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.redis_url.secret_id
            version = "latest"
          }
        }
      }

      liveness_probe {
        http_get {
          path = "/v1/health"
          port = 8000
        }
        initial_delay_seconds = 15
        period_seconds        = 30
        timeout_seconds       = 10
      }

      startup_probe {
        http_get {
          path = "/v1/health"
          port = 8000
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 10
      }
    }
  }
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = "asis-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.frontend_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = "${local.image_base}/frontend:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      ports {
        container_port = 3000
      }

      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
    }
  }
}

# Public access for frontend and backend
resource "google_cloud_run_service_iam_member" "backend_public" {
  location = google_cloud_run_v2_service.backend.location
  service  = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "frontend_public" {
  location = google_cloud_run_v2_service.frontend.location
  service  = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
