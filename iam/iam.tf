locals {
  principals = [
    for email in var.emails : "principal://iam.googleapis.com/locations/global/workforcePools/sandbox-p/subject/${email}"
  ]
}

resource "google_project_iam_binding" "bindings" {
  for_each = toset(var.roles)

  project = var.project_id
  role    = each.value
  members = local.principals
}
