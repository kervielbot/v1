terraform {
  backend "gcs" {
    bucket = "rogue-trader-friday" # Update this when the 1-day sandbox expires
    prefix = "iam"
  }
}
