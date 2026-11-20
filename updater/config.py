"""
Configuration settings for the GitHub Auto-Update System.
"""
import os
import tempfile
from pathlib import Path
from config import APP_VERSION, APP_NAME

# GitHub Repository Configuration
GITHUB_OWNER = "omarmaaahmoud"
GITHUB_REPO = "python-system-2"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Expected Release Asset Naming Patterns (case-insensitive)
# Prefer specific update archive over full installer if both exist
UPDATE_ASSET_PATTERNS = [
    r"ExclusionsAndPrisonersSystem.*Update.*\.zip",
    r"ExclusionsAndPrisonersSystem.*\.zip",
    r"update.*\.zip",
    r".*\.zip",
]

# Checksum file name
CHECKSUM_FILE_NAME = "checksums.sha256"

# Dedicated Temporary Directory for Updates
UPDATE_TEMP_DIR = Path(tempfile.gettempdir()) / "ExclusionsAndPrisonersSystem_Updates"
UPDATE_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Network Timeouts
NETWORK_TIMEOUT_SECONDS = 15
DOWNLOAD_CHUNK_SIZE = 64 * 1024  # 64 KB chunks for smooth streaming and progress calculation

# Rate limiting / cache interval for automated startup checks
STARTUP_CHECK_DELAY_MS = 2500  # Delay startup check by 2.5s so GUI loads instantly
CACHE_CHECK_FILE = UPDATE_TEMP_DIR / "last_check.json"
