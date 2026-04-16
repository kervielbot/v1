locals {
  principals = [
    for email in var.emails : "principal://iam.googleapis.com/locations/global/workforcePools/sandbox-p/subject/${email}"
  ]

  binding_members = {
    for role in var.roles : role => concat(
      local.principals,
      role == "roles/aiplatform.user" ? ["serviceAccount:${google_service_account.openalice_dev.email}"] : []
    )
  }
}

resource "google_service_account" "openalice_dev" {
  account_id   = "openalice-dev"
  display_name = "OpenAlice Local Dev"
  project      = var.project_id
}

resource "google_project_iam_binding" "bindings" {
  for_each = toset(var.roles)

  project = var.project_id
  role    = each.value
  members = local.binding_members[each.value]
}

data "google_compute_default_service_account" "default" {
  project = var.project_id
}

resource "google_service_account_iam_binding" "compute_sa_user" {
  service_account_id = data.google_compute_default_service_account.default.name
  role               = "roles/iam.serviceAccountUser"
  members            = local.principals
}
