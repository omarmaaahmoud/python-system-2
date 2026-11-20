"""
Background Update Checker Thread.
Runs asynchronously without blocking the PySide6 UI.
Supports silent startup check and explicit user-initiated check.
"""
import json
import time
import logging
from typing import Optional
from PySide6.QtCore import QThread, Signal
from updater.github_client import GitHubReleaseClient
from updater.config import CACHE_CHECK_FILE
from config import APP_VERSION

logger = logging.getLogger(__name__)


class UpdateCheckWorker(QThread):
    """Asynchronous background worker for checking updates on GitHub."""

    update_available = Signal(dict)   # Emits release info dict when a newer version exists
    up_to_date = Signal(str)          # Emits message when current version is latest
    check_failed = Signal(str)        # Emits error string if network/api check fails

    def __init__(self, is_manual: bool = False, parent=None):
        super().__init__(parent)
        self.is_manual = is_manual
        self.client = GitHubReleaseClient()

    def run(self):
        # In non-manual (startup) mode, check cache to avoid repeated requests within 2 hours
        if not self.is_manual and self._is_cached_recent(interval_seconds=7200):
            logger.info("Startup update check skipped: recently checked.")
            return

        try:
            release_info = self.client.fetch_latest_release()
            self._save_cache_timestamp()

            if release_info.get("is_newer", False):
                self.update_available.emit(release_info)
            else:
                msg = f"أنت تستخدم أحدث إصدار بالفعل (الإصدار {APP_VERSION})."
                self.up_to_date.emit(msg)

        except Exception as e:
            err_msg = str(e)
            logger.warning("Update check failed: %s", err_msg)
            # Friendly Arabic error translation
            if "HTTP Error 404" in err_msg:
                friendly_err = "لا توجد إصدارات منشورة على المستودع حالياً."
            elif "HTTP Error 403" in err_msg:
                friendly_err = "تم الوصول إلى الحد الأقصى لطلبات GitHub مؤقتاً. يرجى المحاولة لاحقاً."
            elif "timed out" in err_msg or "Timeout" in err_msg:
                friendly_err = "انتهت مهلة الاتصال بخادم التحديث. يرجى التحقق من اتصال الإنترنت."
            elif "getaddrinfo failed" in err_msg or "URLError" in err_msg:
                friendly_err = "تعذر الاتصال بالإنترنت أو تعذر الوصول إلى خوادم GitHub."
            else:
                friendly_err = f"تعذر التحقق من وجود تحديثات:\n{err_msg}"

            self.check_failed.emit(friendly_err)

    def _is_cached_recent(self, interval_seconds: int = 7200) -> bool:
        """Checks if the last update check occurred within interval_seconds."""
        try:
            if CACHE_CHECK_FILE.exists():
                data = json.loads(CACHE_CHECK_FILE.read_text(encoding="utf-8"))
                last_time = data.get("timestamp", 0)
                if (time.time() - last_time) < interval_seconds:
                    return True
        except Exception:
            pass
        return False

    def _save_cache_timestamp(self):
        """Saves current timestamp to cache file."""
        try:
            CACHE_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_CHECK_FILE.write_text(json.dumps({"timestamp": time.time()}), encoding="utf-8")
        except Exception:
            pass
