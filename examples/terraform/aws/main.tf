terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# AWS provider pointed at LocalStack.
# All commands use http://localhost:4566 instead of real AWS APIs.
provider "aws" {
  access_key                  = "test"
  secret_key                  = "test"
  region                      = "us-east-1"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3             = "http://localhost:4566"
    sqs            = "http://localhost:4566"
    sns            = "http://localhost:4566"
    dynamodb       = "http://localhost:4566"
    lambda         = "http://localhost:4566"
    iam            = "http://localhost:4566"
    sts            = "http://localhost:4566"
    cloudwatch     = "http://localhost:4566"
    cloudwatchlogs = "http://localhost:4566"
    secretsmanager = "http://localhost:4566"
    ssm            = "http://localhost:4566"
    kms            = "http://localhost:4566"
    apigateway     = "http://localhost:4566"
    events         = "http://localhost:4566"
    kinesis        = "http://localhost:4566"
    firehose       = "http://localhost:4566"
    stepfunctions  = "http://localhost:4566"
    ec2            = "http://localhost:4566"
    route53        = "http://localhost:4566"
    cloudformation = "http://localhost:4566"
  }
}

resource "aws_s3_bucket" "demo" {
  bucket = "tf-localstack-aws-demo"
}

resource "aws_sqs_queue" "demo" {
  name = "tf-localstack-queue"
}

resource "aws_dynamodb_table" "demo" {
  name         = "tf-localstack-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

output "bucket"  { value = aws_s3_bucket.demo.bucket }
output "queue"   { value = aws_sqs_queue.demo.url }
output "table"   { value = aws_dynamodb_table.demo.name }
