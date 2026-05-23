from localstack.tooling.packages import Package, package


@package(name="dynamodb-local")
def dynamodb_local_package() -> Package:
    from localstack.aws.services.dynamodb.packages import dynamodblocal_package

    return dynamodblocal_package
