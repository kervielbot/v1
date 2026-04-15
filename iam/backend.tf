terraform {
  backend "gcs" {
    bucket = "rogue-trader-wednesday" # Update this when the 1-day sandbox expires
    prefix = "iam"
  }
}
