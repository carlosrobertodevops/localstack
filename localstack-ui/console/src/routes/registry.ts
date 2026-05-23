import type { CloudName } from "@/lib/skins";

export interface ServiceMeta {
  id: string;          // matches /_localstack/clouds/{cloud}/health service key
  label: string;
  path: string;        // route path
}

export const SERVICES_BY_CLOUD: Record<CloudName, ServiceMeta[]> = {
  aws: [
    { id: "s3", label: "S3", path: "/aws/s3" },
    { id: "sqs", label: "SQS", path: "/aws/sqs" },
    { id: "dynamodb", label: "DynamoDB", path: "/aws/dynamodb" },
    { id: "lambda", label: "Lambda", path: "/aws/lambda" },
  ],
  azure: [
    { id: "Microsoft.Resources", label: "Resource Groups", path: "/azure/resource-groups" },
    { id: "Microsoft.Storage", label: "Storage Accounts", path: "/azure/storage-accounts" },
  ],
  gcp: [
    { id: "storage", label: "Cloud Storage", path: "/gcp/storage" },
    { id: "pubsub", label: "Pub/Sub", path: "/gcp/pubsub" },
  ],
};
