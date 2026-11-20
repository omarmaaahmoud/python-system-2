"""
Chunked Streaming Update Downloader.
Streams large update packages with real-time speed and progress calculation,
computes SHA-256 digest on the fly, and validates integrity before finishing.
"""
import hashlib
import logging
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QThread, Signal
from updater.config import (
    UPDATE_TEMP_DIR,
    DOWNLOAD_CHUNK_SIZE,
    NETWORK_TIMEOUT_SECONDS,
)
from config import APP_VERSION

logger = logging.getLogger(__name__)


class UpdateDownloadWorker(QThread):
    """Asynchronous background worker for streaming file downloads with verification."""

    # Signals
    # progress: (percent, bytes_received, total_bytes, speed_kbps)
    progress = Signal(int, int, int, float)
    download_finished = Signal(str, str)   # (target_file_path, computed_sha256)
    download_error = Signal(str)           # (error_message)
    cancelled = Signal()

    def __init__(self, download_url: str, filename: str, expected_sha256: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.filename = filename
        self.expected_sha256 = expected_sha256.strip().lower() if expected_sha256 else None
        self._is_cancelled = False
        self.output_path = UPDATE_TEMP_DIR / filename

    def cancel(self):
        """Requests cancellation of the ongoing download."""
        self._is_cancelled = True

    def run(self):
        if not self.download_url.startswith("https://"):
            self.download_error.emit("رابط التحميل غير آمن: يجب أن يبدأ بـ HTTPS حصراً.")
            return

        if not self.expected_sha256:
            self.download_error.emit(
                "لم يتم العثور على بصمة أمان معتمدة (SHA-256) لهذا الإصدار.\n"
                "حفاظاً على أمان واستقرار النظام، يُمنع منعاً باتاً تثبيت ملفات غير موثقة رقمياً."
            )
            return

        UPDATE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        part_path = self.output_path.with_suffix(self.output_path.suffix + ".part")

        # Clean any stale previous partial file
        if part_path.exists():
            try:
                part_path.unlink()
            except Exception:
                pass

        hasher = hashlib.sha256()
        bytes_received = 0
        total_bytes = 0
        start_time = time.time()
        last_progress_time = start_time
        last_bytes = 0

        req = urllib.request.Request(
            self.download_url,
            headers={"User-Agent": f"ExclusionsAndPrisonersSystem-Updater/{APP_VERSION}"}
        )

        try:
            with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT_SECONDS) as response:
                content_length = response.headers.get("Content-Length")
                if content_length:
                    total_bytes = int(content_length)

                with open(part_path, "wb") as f_out:
                    while True:
                        if self._is_cancelled:
                            f_out.close()
                            if part_path.exists():
                                part_path.unlink()
                            self.cancelled.emit()
                            return

                        chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                        if not chunk:
                            break

                        f_out.write(chunk)
                        hasher.update(chunk)
                        bytes_received += len(chunk)

                        # Calculate progress and speed every 0.15s to throttle GUI signal updates
                        now = time.time()
                        delta_t = now - last_progress_time
                        if delta_t >= 0.15 or (total_bytes and bytes_received == total_bytes):
                            speed_kbps = ((bytes_received - last_bytes) / 1024.0) / max(delta_t, 0.001)
                            percent = int((bytes_received / total_bytes) * 100) if total_bytes else 0
                            self.progress.emit(percent, bytes_received, total_bytes, speed_kbps)
                            last_progress_time = now
                            last_bytes = bytes_received

            # Verify byte count completeness
            if total_bytes > 0 and bytes_received != total_bytes:
                if part_path.exists():
                    part_path.unlink()
                err_msg = (
                    f"الملف المحمّل غير مكتمل!\n"
                    f"الحجم المستلم ({bytes_received:,} بايت) لا يطابق الحجم الكلي المعلن ({total_bytes:,} بايت).\n"
                    f"تم إلغاء التثبيت لحماية النظام."
                )
                self.download_error.emit(err_msg)
                return

            computed_sha256 = hasher.hexdigest().lower()

            # Strictly verify SHA-256 integrity against expected hash
            if computed_sha256 != self.expected_sha256:
                if part_path.exists():
                    part_path.unlink()
                err_msg = (
                    f"فشل التحقق الأمني من سلامة ملف التحديث!\n"
                    f"بصمة التجزئة المحسوبة (SHA-256) لا تطابق البصمة المعتمدة للإصدار.\n\n"
                    f"البصمة المتوقعة:\n{self.expected_sha256}\n\n"
                    f"البصمة المستلمة:\n{computed_sha256}\n\n"
                    f"تم حذف الملف التالف فوراً لحماية أمان وبيانات النظام."
                )
                self.download_error.emit(err_msg)
                return

            # Rename .part to final target
            if self.output_path.exists():
                try:
                    self.output_path.unlink()
                except Exception:
                    pass
            part_path.rename(self.output_path)

            logger.info("Download completed and verified: %s (SHA256: %s)", self.output_path, computed_sha256)
            self.download_finished.emit(str(self.output_path), computed_sha256)

        except urllib.error.URLError as e:
            if part_path.exists():
                try:
                    part_path.unlink()
                except Exception:
                    pass
            self.download_error.emit(f"خطأ في الاتصال بالشبكة أثناء التحميل:\n{str(e)}")

        except Exception as e:
            if part_path.exists():
                try:
                    part_path.unlink()
                except Exception:
                    pass
            self.download_error.emit(f"حدث خطأ غير متوقع أثناء التحميل:\n{str(e)}")
