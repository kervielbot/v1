resource "google_workbench_instance" "user_notebooks" {
  for_each = toset(var.emails)

  name     = "notebook-${replace(split("@", each.value)[0], ".", "-")}"
  location = "europe-west4-a"
  project  = var.project_id

  instance_owners      = ["principal://iam.googleapis.com/locations/global/workforcePools/sandbox-p/subject/${each.value}"]
  disable_proxy_access = true

  gce_setup {
    machine_type = "e2-standard-4"
  }

  depends_on = [
    google_project_service.services,
    google_project_service_identity.services,
    google_service_account_iam_binding.compute_sa_user,
  ]
}
