from typing import TYPE_CHECKING

from localstack.tooling.packages.api import Package, package

if TYPE_CHECKING:
    from localstack.tooling.packages.ffmpeg import FfmpegPackageInstaller
    from localstack.tooling.packages.java import JavaPackageInstaller


@package(name="ffmpeg")
def ffmpeg_package() -> Package["FfmpegPackageInstaller"]:
    from localstack.tooling.packages.ffmpeg import ffmpeg_package

    return ffmpeg_package


@package(name="java")
def java_package() -> Package["JavaPackageInstaller"]:
    from localstack.tooling.packages.java import java_package

    return java_package
