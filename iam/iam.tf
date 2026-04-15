locals {
  bindings = flatten([
    for role in var.roles : [
      for email in var.emails : {
        role      = role
        email     = email
        principal = "principal://iam.googleapis.com/locations/global/workforcePools/sandbox-p/subject/${email}"
      }
    ]
  ])
}

resource "google_project_iam_member" "bindings" {
  for_each = { for b in local.bindings : "${b.role}-${b.email}" => b }

  project = var.project_id
  role    = each.value.role
  member  = each.value.principal
}
