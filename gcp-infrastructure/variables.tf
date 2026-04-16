variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "roles" {
  description = "List of IAM roles to assign to all users"
  type        = list(string)
  default     = []
}

variable "emails" {
  description = "List of email addresses to grant roles to"
  type        = list(string)
  default     = []
}
