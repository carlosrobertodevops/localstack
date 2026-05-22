from localstack.tooling.packages import Package, package


@package(name="opensearch")
def opensearch_package() -> Package:
    from localstack.aws.services.opensearch.packages import opensearch_package

    return opensearch_package
