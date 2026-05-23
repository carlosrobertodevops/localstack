terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}

# google provider supports per-API endpoint overrides. We point every API
# we emulate at the LocalStack edge.
#
# Auth: set GOOGLE_OAUTH_ACCESS_TOKEN to any string (our gateway accepts
# any bearer). Avoid GOOGLE_APPLICATION_CREDENTIALS — that triggers a
# round-trip to oauth2.googleapis.com that we already shim.
#
#   export GOOGLE_OAUTH_ACCESS_TOKEN=dummy-token
#   export GOOGLE_PROJECT=localstack-project
provider "google" {
  project = "localstack-project"
  region  = "us-central1"
  zone    = "us-central1-a"

  storage_custom_endpoint                  = "http://localhost:4566/storage/v1/"
  pubsub_custom_endpoint                   = "http://localhost:4566/"
  firestore_custom_endpoint                = "http://localhost:4566/"
  cloud_functions_custom_endpoint          = "http://localhost:4566/"
  iam_custom_endpoint                      = "http://localhost:4566/"
  bigquery_custom_endpoint                 = "http://localhost:4566/bigquery/v2/"
  secret_manager_custom_endpoint           = "http://localhost:4566/"
  kms_custom_endpoint                      = "http://localhost:4566/"
  cloud_tasks_custom_endpoint              = "http://localhost:4566/"
  cloud_run_custom_endpoint                = "http://localhost:4566/"
  logging_custom_endpoint                  = "http://localhost:4566/"
  sql_custom_endpoint                      = "http://localhost:4566/sql/v1beta4/"
  cloud_scheduler_custom_endpoint          = "http://localhost:4566/"
  dns_custom_endpoint                      = "http://localhost:4566/dns/v1/"
  spanner_custom_endpoint                  = "http://localhost:4566/"
  redis_custom_endpoint                    = "http://localhost:4566/"
  cloud_resource_manager_custom_endpoint   = "http://localhost:4566/"
}

resource "google_storage_bucket" "demo" {
  name          = "tf-localstack-gcp-demo"
  location      = "US"
  force_destroy = true
}

resource "google_pubsub_topic" "demo" {
  name = "tf-localstack-topic"
}

resource "google_pubsub_subscription" "demo" {
  name  = "tf-localstack-sub"
  topic = google_pubsub_topic.demo.name
}

output "bucket"       { value = google_storage_bucket.demo.name }
output "topic"        { value = google_pubsub_topic.demo.name }
output "subscription" { value = google_pubsub_subscription.demo.name }
