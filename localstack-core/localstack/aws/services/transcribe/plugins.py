from localstack.tooling.packages import Package, package
from localstack.tooling.packages.core import PythonPackageInstaller


@package(name="vosk")
def vosk_package() -> Package[PythonPackageInstaller]:
    from localstack.aws.services.transcribe.packages import vosk_package

    return vosk_package
