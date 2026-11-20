"""
Updater Package for Exclusions and Prisoners System.
Handles GitHub Releases API integration, background checking, chunked streaming download,
SHA-256 verification, and external process handoff.
"""

from updater.config import (
    GITHUB_OWNER,
    GITHUB_REPO,
    GITHUB_API_URL,
    UPDATE_TEMP_DIR,
)
from updater.version import parse_version, is_newer_version
from updater.github_client import GitHubReleaseClient
from updater.checker import UpdateCheckWorker
from updater.downloader import UpdateDownloadWorker

__all__ = [
    "GITHUB_OWNER",
    "GITHUB_REPO",
    "GITHUB_API_URL",
    "UPDATE_TEMP_DIR",
    "parse_version",
    "is_newer_version",
    "GitHubReleaseClient",
    "UpdateCheckWorker",
    "UpdateDownloadWorker",
]
