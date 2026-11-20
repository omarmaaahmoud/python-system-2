"""
PySide6 Update Notification and Download Dialog.
Matches application visual identity, RTL Arabic interface, Segoe UI typography.
Handles real-time progress streaming, SHA-256 verification display, and clean process handoff.
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextBrowser, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont, QPixmap

from config import APP_VERSION, APP_NAME, LOGO_PATH, BASE_DIR
from updater.downloader import UpdateDownloadWorker
from updater.config import UPDATE_TEMP_DIR


class UpdateDialog(QDialog):
    """Modern Arabic RTL Dialog for Update Notification and Download."""

    def __init__(self, release_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.release_info = release_info
        self.downloader: Optional[UpdateDownloadWorker] = None
        self.downloaded_package_path: Optional[str] = None

        self.setWindowTitle(f"تحديث جديد متوفر — {APP_NAME}")
        self.setMinimumSize(540, 520)
        self.resize(560, 560)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Banner
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0F172A, stop:1 #1E3A8A);
                border-bottom: 2px solid #2563EB;
                padding: 16px 20px;
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(14)

        if LOGO_PATH.exists():
            emblem = QLabel()
            pix = QPixmap(str(LOGO_PATH)).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            emblem.setPixmap(pix)
            h_layout.addWidget(emblem)

        title_v = QVBoxLayout()
        title_v.setSpacing(3)
        h_title = QLabel("🚀  يتوفر إصدار جديد من البرنامج")
        h_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        title_v.addWidget(h_title)

        latest_ver = self.release_info.get("version", "جديد")
        h_sub = QLabel(f"الإصدار الحالي: v{APP_VERSION}  ➔  الإصدار الجديد: v{latest_ver}")
        h_sub.setStyleSheet("font-size: 12px; font-weight: bold; color: #93C5FD;")
        title_v.addWidget(h_sub)
        h_layout.addLayout(title_v, 1)

        main_layout.addWidget(header)

        # 2. Content Body
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 16, 20, 16)
        body_layout.setSpacing(12)

        # Metadata Card (Size & Release Date)
        meta_frame = QFrame()
        meta_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        meta_layout = QHBoxLayout(meta_frame)
        meta_layout.setContentsMargins(0, 0, 0, 0)

        size_bytes = self.release_info.get("asset_size", 0)
        size_str = f"{size_bytes / (1024*1024):.1f} ميجابايت" if size_bytes else "غير محدد"
        size_lbl = QLabel(f"📦 حجم التحديث: <b>{size_str}</b>")
        size_lbl.setStyleSheet("font-size: 12px; color: #334155;")
        meta_layout.addWidget(size_lbl)

        meta_layout.addStretch()

        pub_date = self.release_info.get("published_at", "")[:10]
        date_lbl = QLabel(f"📅 تاريخ النشر: <b>{pub_date}</b>" if pub_date else "")
        date_lbl.setStyleSheet("font-size: 12px; color: #334155;")
        meta_layout.addWidget(date_lbl)

        body_layout.addWidget(meta_frame)

        # Release Notes Section
        notes_hdr = QLabel("📝  ملاحظات الإصدار والتحسينات الجديدة:")
        notes_hdr.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        body_layout.addWidget(notes_hdr)

        self.notes_browser = QTextBrowser()
        self.notes_browser.setOpenExternalLinks(True)
        raw_notes = self.release_info.get("release_notes", "").strip()
        self.notes_browser.setMarkdown(raw_notes or "تحسينات عامة في الأداء وتصحيحات للنظام.")
        self.notes_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
                color: #0F172A;
                line-height: 1.5;
            }
        """)
        body_layout.addWidget(self.notes_browser, 1)

        # 3. Download Progress Container (initially hidden)
        self.progress_container = QFrame()
        self.progress_container.setVisible(False)
        self.progress_container.setStyleSheet("""
            QFrame {
                background-color: #EFF6FF;
                border: 1px solid #BFDBFE;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        prog_layout = QVBoxLayout(self.progress_container)
        prog_layout.setContentsMargins(4, 4, 4, 4)
        prog_layout.setSpacing(6)

        self.progress_status_lbl = QLabel("جاري الاتصال والتحميل...")
        self.progress_status_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #1E40AF;")
        prog_layout.addWidget(self.progress_status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                text-align: center;
                background-color: #FFFFFF;
                color: #0F172A;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 5px;
            }
        """)
        prog_layout.addWidget(self.progress_bar)

        self.progress_details_lbl = QLabel("")
        self.progress_details_lbl.setStyleSheet("font-size: 11px; color: #475569;")
        prog_layout.addWidget(self.progress_details_lbl)

        body_layout.addWidget(self.progress_container)
        main_layout.addWidget(body, 1)

        # 4. Action Buttons Footer
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border-top: 1px solid #E2E8F0;
                padding: 12px 20px;
            }
        """)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(0, 0, 0, 0)
        f_layout.setSpacing(10)

        self.btn_later = QPushButton("تذكيري لاحقاً")
        self.btn_later.setMinimumHeight(40)
        self.btn_later.setStyleSheet("""
            QPushButton {
                background-color: #E2E8F0; color: #334155;
                border: 1px solid #CBD5E1; border-radius: 6px;
                font-size: 13px; font-weight: bold; padding: 6px 18px;
            }
            QPushButton:hover { background-color: #CBD5E1; color: #0F172A; }
        """)
        self.btn_later.clicked.connect(self.reject)
        f_layout.addWidget(self.btn_later)

        f_layout.addStretch()

        self.btn_cancel_download = QPushButton("إلغاء التحميل")
        self.btn_cancel_download.setVisible(False)
        self.btn_cancel_download.setMinimumHeight(40)
        self.btn_cancel_download.setStyleSheet("""
            QPushButton {
                background-color: #FEE2E2; color: #DC2626;
                border: 1px solid #FCA5A5; border-radius: 6px;
                font-size: 13px; font-weight: bold; padding: 6px 18px;
            }
            QPushButton:hover { background-color: #FECACA; }
        """)
        self.btn_cancel_download.clicked.connect(self.cancel_download)
        f_layout.addWidget(self.btn_cancel_download)

        self.btn_update_now = QPushButton("🚀  تحميل وتثبيت التحديث الآن")
        self.btn_update_now.setMinimumHeight(40)
        self.btn_update_now.setStyleSheet("""
            QPushButton {
                background-color: #1E40AF; color: #FFFFFF;
                border: none; border-radius: 6px;
                font-size: 13px; font-weight: bold; padding: 6px 22px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton:pressed { background-color: #1E3A8A; }
            QPushButton:disabled { background-color: #94A3B8; }
        """)
        self.btn_update_now.clicked.connect(self.start_download)
        f_layout.addWidget(self.btn_update_now)

        main_layout.addWidget(footer)

    def start_download(self):
        """Starts streaming the update package in the background."""
        url = self.release_info.get("asset_url")
        filename = self.release_info.get("asset_name", "update.zip")
        expected_sha256 = self.release_info.get("sha256")

        if not url:
            QMessageBox.critical(self, "خطأ", "لم يتم العثور على رابط صالح لملف التحديث.")
            return

        # Switch to downloading UI state
        self.btn_update_now.setVisible(False)
        self.btn_later.setVisible(False)
        self.btn_cancel_download.setVisible(True)
        self.progress_container.setVisible(True)
        self.progress_status_lbl.setText("جاري تحميل التحديث والتحقق من بصمة الأمان...")

        self.downloader = UpdateDownloadWorker(
            download_url=url,
            filename=filename,
            expected_sha256=expected_sha256,
            parent=self
        )
        self.downloader.progress.connect(self.on_download_progress)
        self.downloader.download_finished.connect(self.on_download_finished)
        self.downloader.download_error.connect(self.on_download_error)
        self.downloader.cancelled.connect(self.on_download_cancelled)
        self.downloader.start()

    def on_download_progress(self, percent: int, received: int, total: int, speed_kbps: float):
        self.progress_bar.setValue(percent)
        rec_mb = received / (1024 * 1024)
        tot_mb = total / (1024 * 1024) if total else 0
        speed_mb = speed_kbps / 1024.0

        if total > 0:
            details = f"تم تحميل {rec_mb:.1f} MB من {tot_mb:.1f} MB ({percent}%) — السرعة: {speed_mb:.1f} MB/s"
        else:
            details = f"تم تحميل {rec_mb:.1f} MB — السرعة: {speed_mb:.1f} MB/s"

        self.progress_details_lbl.setText(details)

    def on_download_finished(self, package_path: str, computed_sha256: str):
        self.downloaded_package_path = package_path
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar::chunk { background-color: #16A34A; }
        """)
        self.progress_status_lbl.setText("✅ تم اكتمال التحميل والتحقق بنجاح (SHA-256 Verified)!")
        self.progress_details_lbl.setText(f"البصمة: {computed_sha256[:16]}...{computed_sha256[-8:]}")
        self.btn_cancel_download.setVisible(False)

        # Prompt for immediate restart to apply
        QTimer.singleShot(800, self.apply_update_and_restart)

    def on_download_error(self, error_message: str):
        self.progress_container.setVisible(False)
        self.btn_cancel_download.setVisible(False)
        self.btn_update_now.setVisible(True)
        self.btn_later.setVisible(True)
        QMessageBox.critical(self, "خطأ في تحميل التحديث", error_message)

    def on_download_cancelled(self):
        self.progress_container.setVisible(False)
        self.btn_cancel_download.setVisible(False)
        self.btn_update_now.setVisible(True)
        self.btn_later.setVisible(True)

    def cancel_download(self):
        if self.downloader and self.downloader.isRunning():
            self.downloader.cancel()

    def apply_update_and_restart(self):
        """Prepares databases, spawns UpdateHelper, and exits the application cleanly."""
        if not self.downloaded_package_path or not os.path.exists(self.downloaded_package_path):
            QMessageBox.critical(self, "خطأ", "ملف التحديث غير موجود على القرص.")
            return

        # Notify user
        reply = QMessageBox.question(
            self,
            "تثبيت التحديث",
            "اكتمل تجهيز التحديث بنجاح!\n\n"
            "سيتم الآن إغلاق البرنامج وتشغيل مساعد التحديث التلقائي.\n"
            "سيتم الحفاظ الكامل على كافة قواعد البيانات وسجلات المستبعدين والمسجونين.\n\n"
            "هل ترغب في المتابعة وإعادة التشغيل الآن؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        # 1. Clean shutdown of databases: checkpoint WAL mode with TRUNCATE and check integrity
        try:
            main_win = self.parent()
            if main_win and hasattr(main_win, "db"):
                main_win.db.safe_checkpoint_and_close()
            if main_win and hasattr(main_win, "school_security_db"):
                main_win.school_security_db.safe_checkpoint_and_close()
        except Exception:
            pass

        # 2. Locate UpdateHelper executable or script
        # Check in current directory, frozen dir, or updater package
        if getattr(sys, "frozen", False):
            install_dir = Path(sys.executable).resolve().parent
            helper_exe = install_dir / "UpdateHelper.exe"
            target_exe_name = Path(sys.executable).name
            if not helper_exe.exists():
                helper_exe = install_dir / "_internal" / "UpdateHelper.exe"
        else:
            install_dir = BASE_DIR
            helper_exe = BASE_DIR / "updater" / "update_helper.py"
            target_exe_name = "ExclusionsAndPrisonersSystem.exe"

        current_pid = os.getpid()

        # Ensure UpdateHelper itself runs outside any directory that is being replaced
        import shutil
        external_helper = UPDATE_TEMP_DIR / helper_exe.name
        try:
            shutil.copy2(helper_exe, external_helper)
            helper_to_run = external_helper
        except Exception:
            helper_to_run = helper_exe

        # Build command to invoke UpdateHelper
        if str(helper_to_run).endswith(".py"):
            cmd = [
                sys.executable,
                str(helper_to_run),
                "--pid", str(current_pid),
                "--package", str(self.downloaded_package_path),
                "--target-dir", str(install_dir),
                "--executable", target_exe_name,
            ]
        else:
            cmd = [
                str(helper_to_run),
                "--pid", str(current_pid),
                "--package", str(self.downloaded_package_path),
                "--target-dir", str(install_dir),
                "--executable", target_exe_name,
            ]

        # 3. Spawn detached helper process from temp directory
        try:
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(cmd, cwd=str(UPDATE_TEMP_DIR), **kwargs)
        except Exception as e:
            QMessageBox.critical(self, "خطأ في تشغيل مساعد التحديث", f"تعذر إطلاق معالج التحديث:\n{e}")
            return

        # 4. Exit main application cleanly
        QApplication.instance().quit()
        QTimer.singleShot(1500, lambda: os._exit(0))
