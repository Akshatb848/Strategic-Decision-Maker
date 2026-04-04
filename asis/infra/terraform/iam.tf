# ── ASIS IAM — Service Accounts and Role Bindings ─────────────────────────────

# ── Backend Service Account ───────────────────────────────────────────────────

resource "google_service_account" "backend_sa" {
  account_id   = "asis-backend-sa"
  display_name = "ASIS Backend Service Account"
  description  = "Service account for the ASIS backend Cloud Run service."
  project      = var.project_id
}

# Invoke other Cloud Run services
resource "google_project_iam_member" "backend_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Connect to Cloud SQL
resource "google_project_iam_member" "backend_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Read secrets from Secret Manager
resource "google_project_iam_member" "backend_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# View Redis instance metadata
resource "google_project_iam_member" "backend_redis_viewer" {
  project = var.project_id
  role    = "roles/redis.viewer"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# Pull images from Artifact Registry
resource "google_project_iam_member" "backend_artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
}

# ── Frontend Service Account ──────────────────────────────────────────────────

resource "google_service_account" "frontend_sa" {
  account_id   = "asis-frontend-sa"
  display_name = "ASIS Frontend Service Account"
  description  = "Service account for the ASIS frontend Cloud Run service."
  project      = var.project_id
}

# Invoke the backend service
resource "google_project_iam_member" "frontend_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.frontend_sa.email}"
}

# Pull images from Artifact Registry
resource "google_project_iam_member" "frontend_artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.frontend_sa.email}"
}

# ── n8n Service Account ───────────────────────────────────────────────────────

resource "google_service_account" "n8n_sa" {
  account_id   = "asis-n8n-sa"
  display_name = "ASIS n8n Service Account"
  description  = "Service account for the ASIS n8n workflow automation service."
  project      = var.project_id
}

# Invoke the backend to trigger ASIS pipelines via webhooks
resource "google_project_iam_member" "n8n_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.n8n_sa.email}"
}

# Connect to Cloud SQL for n8n workflow persistence
resource "google_project_iam_member" "n8n_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.n8n_sa.email}"
}

# Read secrets (e.g., N8N_WEBHOOK_SECRET, database credentials)
resource "google_project_iam_member" "n8n_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.n8n_sa.email}"
}

# View Redis instance for queue configuration
resource "google_project_iam_member" "n8n_redis_viewer" {
  project = var.project_id
  role    = "roles/redis.viewer"
  member  = "serviceAccount:${google_service_account.n8n_sa.email}"
}

# Pull images from Artifact Registry
resource "google_project_iam_member" "n8n_artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.n8n_sa.email}"
}
