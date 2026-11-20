"""
GitHub Releases API Client.
Fetches release metadata, verifies release authenticity, ignores drafts/prereleases,
and resolves download assets and SHA-256 digests.
"""
import json
import logging
import re
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple
from updater.config import (
    GITHUB_API_URL,
    NETWORK_TIMEOUT_SECONDS,
    UPDATE_ASSET_PATTERNS,
    CHECKSUM_FILE_NAME,
)
from updater.version import parse_version, is_newer_version
from config import APP_VERSION

logger = logging.getLogger(__name__)


class GitHubReleaseClient:
    """Client for querying the GitHub Releases API."""

    def __init__(self, api_url: str = GITHUB_API_URL):
        self.api_url = api_url

    def fetch_latest_release(self) -> Dict[str, Any]:
        """Fetches and parses the latest stable release from GitHub.
        
        Returns a dictionary with:
        {
            "tag_name": str,
            "version": str,
            "title": str,
            "release_notes": str,
            "published_at": str,
            "html_url": str,
            "asset_name": str,
            "asset_url": str,
            "asset_size": int,
            "sha256": Optional[str],
            "is_newer": bool,
        }
        
        Raises:
            urllib.error.HTTPError, urllib.error.URLError, ValueError
        """
        req = urllib.request.Request(
            self.api_url,
            headers={
                "User-Agent": f"ExclusionsAndPrisonersSystem-Updater/{APP_VERSION}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

        with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise ValueError(f"استجابة غير متوقعة من خادم التحديث: رمز الحالة {response.status}")
            data = json.loads(response.read().decode("utf-8"))

        # Verify not a draft or prerelease
        if data.get("draft", False):
            raise ValueError("الإصدار الأخير هو مسودة (Draft) وليس إصداراً رسمياً.")

        if data.get("prerelease", False):
            raise ValueError("الإصدار الأخير هو إصدار تجريبي (Pre-release) تم تجاهله.")

        tag_name = data.get("tag_name", "")
        version_str = tag_name.lstrip("vV")
        release_notes = data.get("body", "") or "لا توجد ملاحظات إصدار مرفقة."
        title = data.get("name") or f"الإصدار {version_str}"
        published_at = data.get("published_at", "")
        html_url = data.get("html_url", "")
        assets = data.get("assets", [])

        # Find target update package asset
        target_asset = self._select_update_asset(assets)
        if not target_asset:
            raise ValueError("لم يتم العثور على ملف تحديث مضغوط (.zip) مرفق مع هذا الإصدار.")

        asset_name = target_asset.get("name", "")
        asset_url = target_asset.get("browser_download_url", "")
        asset_size = target_asset.get("size", 0)

        # Validate download URL is HTTPS
        if not asset_url.startswith("https://"):
            raise ValueError(f"رابط التحميل غير آمن: {asset_url}")

        # Resolve SHA-256 digest
        sha256_hash = self._resolve_sha256(assets, asset_name, release_notes)

        return {
            "tag_name": tag_name,
            "version": version_str,
            "title": title,
            "release_notes": release_notes,
            "published_at": published_at,
            "html_url": html_url,
            "asset_name": asset_name,
            "asset_url": asset_url,
            "asset_size": asset_size,
            "sha256": sha256_hash,
            "is_newer": is_newer_version(version_str, APP_VERSION),
        }

    def _select_update_asset(self, assets: list) -> Optional[Dict[str, Any]]:
        """Selects the most suitable update asset based on configured patterns."""
        if not assets:
            return None

        # Try matching each pattern in order of preference
        for pattern in UPDATE_ASSET_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE)
            for asset in assets:
                name = asset.get("name", "")
                if regex.search(name) and not name.endswith(".sha256") and not name.endswith(".txt"):
                    return asset

        # Fallback to any .zip file
        for asset in assets:
            if asset.get("name", "").lower().endswith(".zip"):
                return asset

        return None

    def _resolve_sha256(self, assets: list, target_asset_name: str, release_notes: str) -> Optional[str]:
        """Resolves the expected SHA-256 digest from release assets or release notes."""
        # 1. Check for dedicated checksums asset
        for asset in assets:
            name = asset.get("name", "").lower()
            if name == CHECKSUM_FILE_NAME.lower() or name.endswith(".sha256") or "checksum" in name:
                try:
                    chk_url = asset.get("browser_download_url", "")
                    if chk_url.startswith("https://"):
                        req = urllib.request.Request(
                            chk_url,
                            headers={"User-Agent": f"ExclusionsAndPrisonersSystem-Updater/{APP_VERSION}"}
                        )
                        with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT_SECONDS) as chk_res:
                            chk_text = chk_res.read().decode("utf-8", errors="replace")
                            parsed_hash = self._parse_checksum_text(chk_text, target_asset_name)
                            if parsed_hash:
                                return parsed_hash.lower()
                except Exception as e:
                    logger.warning("Could not download checksum file %s: %s", name, e)

        # 2. Check in release notes body (e.g. 'SHA256: 3a7b...' or '3a7b...  file.zip')
        if release_notes:
            # Pattern 1: SHA256: [64 hex characters]
            m1 = re.search(r"sha[-_]?256\s*[:=]\s*([a-fA-F0-9]{64})", release_notes, re.IGNORECASE)
            if m1:
                return m1.group(1).lower()

            # Pattern 2: [64 hex characters]  target_asset_name
            escaped_name = re.escape(target_asset_name)
            m2 = re.search(r"([a-fA-F0-9]{64})\s+.*?" + escaped_name, release_notes, re.IGNORECASE)
            if m2:
                return m2.group(1).lower()

            # Pattern 3: Any 64 hex characters on a standalone line
            m3 = re.search(r"^[ \t]*([a-fA-F0-9]{64})[ \t]*$", release_notes, re.MULTILINE)
            if m3:
                return m3.group(1).lower()

        return None

    @staticmethod
    def _parse_checksum_text(text: str, target_asset_name: str) -> Optional[str]:
        """Parses standard sha256sum format: '<hash>  <filename>' or raw '<hash>'."""
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                hash_cand, filename = parts[0], parts[-1]
                if len(hash_cand) == 64 and (target_asset_name in filename or filename in target_asset_name):
                    return hash_cand.lower()
            elif len(parts) == 1 and len(parts[0]) == 64:
                return parts[0].lower()
        return None
