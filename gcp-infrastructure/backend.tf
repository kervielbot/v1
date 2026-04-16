terraform {
  backend "gcs" {
    bucket = "rogue-trader-thursday" # Update this when the 1-day sandbox expires
    prefix = "iam"
  }
}
