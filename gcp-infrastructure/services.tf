locals {
  services = [
    "notebooks.googleapis.com",
    "aiplatform.googleapis.com",
    "compute.googleapis.com",
    "storage.googleapis.com",
  ]
}

resource "google_project_service" "services" {
  for_each = toset(local.services)

  service            = each.value
  disable_on_destroy = false
}

resource "google_project_service_identity" "services" {
  provider = google-beta
  for_each = toset(local.services)

  service = each.value

  depends_on = [google_project_service.services]
}
