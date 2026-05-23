import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";
import { App } from "@/App";
import { HomeIndex } from "@/routes/HomeIndex";
import {
  S3List,
  SqsList,
  DynamoList,
  LambdaList,
  GenericDetail,
} from "@/routes/aws/services";
import {
  ResourceGroupsList,
  StorageAccountsList,
} from "@/routes/azure/services";
import { StorageList, PubSubList } from "@/routes/gcp/services";

const rootRoute = createRootRoute({ component: App });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: HomeIndex,
});

const cloudLayout = (path: "aws" | "azure" | "gcp") =>
  createRoute({
    getParentRoute: () => rootRoute,
    path,
    component: () => <Outlet />,
  });

const awsRoute = cloudLayout("aws");
const azureRoute = cloudLayout("azure");
const gcpRoute = cloudLayout("gcp");

const awsIndex = createRoute({
  getParentRoute: () => awsRoute,
  path: "/",
  component: HomeIndex,
});
const azureIndex = createRoute({
  getParentRoute: () => azureRoute,
  path: "/",
  component: HomeIndex,
});
const gcpIndex = createRoute({
  getParentRoute: () => gcpRoute,
  path: "/",
  component: HomeIndex,
});

const s3 = createRoute({ getParentRoute: () => awsRoute, path: "s3", component: S3List });
const s3Detail = createRoute({
  getParentRoute: () => awsRoute,
  path: "s3/$bucket",
  component: () => <GenericDetail service="S3" paramKey="bucket" />,
});
const sqs = createRoute({ getParentRoute: () => awsRoute, path: "sqs", component: SqsList });
const sqsDetail = createRoute({
  getParentRoute: () => awsRoute,
  path: "sqs/$queue",
  component: () => <GenericDetail service="SQS" paramKey="queue" />,
});
const dynamo = createRoute({
  getParentRoute: () => awsRoute,
  path: "dynamodb",
  component: DynamoList,
});
const dynamoDetail = createRoute({
  getParentRoute: () => awsRoute,
  path: "dynamodb/$table",
  component: () => <GenericDetail service="DynamoDB" paramKey="table" />,
});
const lambda = createRoute({
  getParentRoute: () => awsRoute,
  path: "lambda",
  component: LambdaList,
});
const lambdaDetail = createRoute({
  getParentRoute: () => awsRoute,
  path: "lambda/$fn",
  component: () => <GenericDetail service="Lambda" paramKey="fn" />,
});

const azRgs = createRoute({
  getParentRoute: () => azureRoute,
  path: "resource-groups",
  component: ResourceGroupsList,
});
const azSa = createRoute({
  getParentRoute: () => azureRoute,
  path: "storage-accounts",
  component: StorageAccountsList,
});

const gcpStorage = createRoute({
  getParentRoute: () => gcpRoute,
  path: "storage",
  component: StorageList,
});
const gcpPubsub = createRoute({
  getParentRoute: () => gcpRoute,
  path: "pubsub",
  component: PubSubList,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  awsRoute.addChildren([
    awsIndex,
    s3,
    s3Detail,
    sqs,
    sqsDetail,
    dynamo,
    dynamoDetail,
    lambda,
    lambdaDetail,
  ]),
  azureRoute.addChildren([azureIndex, azRgs, azSa]),
  gcpRoute.addChildren([gcpIndex, gcpStorage, gcpPubsub]),
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
