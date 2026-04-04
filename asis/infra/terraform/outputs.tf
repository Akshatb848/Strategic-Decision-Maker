output "backend_url" {
  description = "Public URL of the ASIS backend Cloud Run service."
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "Public URL of the ASIS frontend Cloud Run service."
  value       = google_cloud_run_v2_service.frontend.uri
}

output "database_instance" {
  description = "Connection name of the Cloud SQL PostgreSQL instance (project:region:instance)."
  value       = google_sql_database_instance.asis_primary.connection_name
}

output "redis_host" {
  description = "Private IP address of the Memorystore Redis instance."
  value       = google_redis_instance.asis_cache.host
}
