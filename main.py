import sys
import os
from pathlib import Path

# Fix stdout encoding for Windows console if needed
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from config import APP_NAME, APP_SUBTITLE, LOGO_PATH, BASE_DIR
from database import DatabaseManager
from ui.styles import MAIN_STYLESHEET
from ui.main_window import MainWindow

def handle_exception(exc_type, exc_value, exc_traceback):
    """Crash-handler to log errors and show friendly dialog instead of closing abruptly."""
    import traceback
    err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        err_log = BASE_DIR / "error_log.txt"
        err_log.write_text(err_str, encoding="utf-8")
    except Exception:
        pass
    print("CRITICAL ERROR:\n", err_str)
    try:
        QMessageBox.critical(
            None, "تنبيه خطأ", 
            f"حدث خطأ غير متوقع أثناء التشغيل:\n{str(exc_value)}\n\nتم حفظ التفاصيل في ملف error_log.txt"
        )
    except Exception:
        pass

sys.excepthook = handle_exception

def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Alexandria Educational Directorate")

    # Set Official Egyptian Government Emblem Icon
    if LOGO_PATH.exists():
        app.setWindowIcon(QIcon(str(LOGO_PATH)))

    # Set seamless Right-to-Left (RTL) Layout for Arabic
    app.setLayoutDirection(Qt.RightToLeft)

    # Apply Executive Theme Stylesheet
    app.setStyleSheet(MAIN_STYLESHEET)

    # Set Global Arabic Font
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    # Initialize SQLite Database & Relational Schema
    db_manager = DatabaseManager()

    # Launch Main Dashboard Window
    window = MainWindow(db_manager)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
