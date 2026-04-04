# ── ASIS Secret Manager Resources ─────────────────────────────────────────────
# Declares all application secrets as google_secret_manager_secret resources.
# Secret *values* are managed separately (e.g., via gcloud CLI or CI/CD pipeline)
# and are never stored in Terraform state or source control.

locals {
  secret_names = [
    "ANTHROPIC_API_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET",
    "TAVILY_API_KEY",
    "FMP_API_KEY",
    "NEWSAPI_KEY",
    "LITELLM_MASTER_KEY",
    "N8N_WEBHOOK_SECRET",
    "LANGFUSE_SECRET_KEY",
    "MEM0_API_KEY",
  ]
}

resource "google_secret_manager_secret" "anthropic_api_key" {
  secret_id = "ANTHROPIC_API_KEY"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "DATABASE_URL"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "REDIS_URL"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "JWT_SECRET"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "tavily_api_key" {
  secret_id = "TAVILY_API_KEY"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "fmp_api_key" {
  secret_id = "FMP_API_KEY"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "newsapi_key" {
  secret_id = "NEWSAPI_KEY"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "litellm_master_key" {
  secret_id = "LITELLM_MASTER_KEY"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "n8n_webhook_secret" {
  secret_id = "N8N_WEBHOOK_SECRET"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "langfuse_secret_key" {
  secret_id = "LANGFUSE_SECRET_KEY"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}

resource "google_secret_manager_secret" "mem0_api_key" {
  secret_id = "MEM0_API_KEY"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    service     = "asis"
  }
}
