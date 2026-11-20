import os
import sys
from pathlib import Path

# Base Paths - Supports both source script and PyInstaller frozen executable
if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).resolve().parent
    MEIPASS_DIR = Path(getattr(sys, '_MEIPASS', EXE_DIR))
    BASE_DIR = EXE_DIR
    ASSETS_DIR = MEIPASS_DIR / "assets"
    if not ASSETS_DIR.exists():
        ASSETS_DIR = EXE_DIR / "assets"
else:
    BASE_DIR = Path(__file__).resolve().parent
    ASSETS_DIR = BASE_DIR / "assets"

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
LOGO_PATH = ASSETS_DIR / "logo.png"

# Read the bundled seed separately from the writable database directory when frozen.
if getattr(sys, 'frozen', False):
    BUNDLE_DATA_DIR = MEIPASS_DIR / "data"
else:
    BUNDLE_DATA_DIR = DATA_DIR

# Database Configuration
DB_FILE = DATA_DIR / "exclusions_prisoners.db"

# Auto-seed initial database if running for the first time on a new computer
if getattr(sys, 'frozen', False) and not DB_FILE.exists():
    try:
        bundled_db = MEIPASS_DIR / "data" / "exclusions_prisoners.db"
        if bundled_db.exists():
            import shutil
            shutil.copy2(bundled_db, DB_FILE)
    except Exception:
        pass

# Application Metadata
APP_NAME = "نظام بيانات المستبعدين والمسجونين"
APP_SUBTITLE = "مديرية التربية والتعليم بالإسكندرية"
APP_VERSION = "2.2.1"
APP_AUTHOR = "إدارة نظم المعلومات والتحول الرقمي"

# UI Theme & Colors (Modern Executive Dark/Light Blue Palette)
PALETTE = {
    "primary": "#1E40AF",          # Deep Royal Blue
    "primary_dark": "#1E293B",     # Deep Slate / Navy
    "primary_light": "#3B82F6",    # Bright Accent Blue
    "primary_hover": "#1D4ED8",
    "secondary": "#0F172A",        # Midnight Slate
    "accent_cyan": "#0284C7",      # Cyan Blue
    "accent_teal": "#0D9488",      # Teal
    "background": "#F1F5F9",       # Clean Slate 100
    "surface": "#FFFFFF",          # Pure White
    "surface_alt": "#F8FAFC",      # Slate 50
    "border": "#CBD5E1",           # Slate 300
    "border_light": "#E2E8F0",     # Slate 200
    "text_main": "#0F172A",        # Slate 900
    "text_muted": "#64748B",       # Slate 500
    "text_light": "#94A3B8",       # Slate 400
    "danger": "#DC2626",           # Crimson Red
    "danger_bg": "#FEF2F2",
    "warning": "#D97706",          # Amber
    "warning_bg": "#FFFBEB",
    "success": "#16A34A",          # Emerald Green
    "success_bg": "#F0FDF4",
    "info": "#2563EB",
    "info_bg": "#EFF6FF",
}

# Default Administrations in Alexandria Educational Directorate
DEFAULT_ADMINISTRATIONS = [
    "المنتزه أول",
    "المنتزه ثان",
    "المنتزه",
    "شرق",
    "وسط",
    "غرب",
    "الجمرك",
    "العجمي",
    "العامرية",
    "برج العرب",
    "المديرية"
]

# Common Case Types (from actual data)
DEFAULT_CASE_TYPES = [
    "انضمام لجماعة إرهابية",
    "قتل",
    "إتجار بالمخدرات",
    "جنحة",
    "هتك عرض",
    "توظيف اموال",
    "تزوير وتهريب وهجرة",
    "نصب",
    "اختلاس",
    "زنا",
    "تبديد شيكات",
    "صرف راتب بدون وجه حق",
    "قضايا أسرة",
    "سرقة",
    "جنائى",
    "تحرش",
    "تزوير فى محرر رسمى",
    "قيد الحرية",
    "منتقبة",
    "ملتحى",
    "دخول محافظة",
    "إستبعاد ترشيح",
    "نقل بين الإدارات",
    "مخالفات مالية",
    "مسابقة 2024",
    "شيك بدون رصيد",
    "إيقاف تنفيذ للتصالح",
    "سرقة مدرسة ارض العوايد"
]

# Prisoner Statuses
PRISONER_STATUSES = [
    "محبوس احتياطياً",
    "تنفيذ حكم (يقضي العقوبة)",
    "مفرج عنه (شرطي)",
    "مفرج عنه (نهائي / براءة)",
    "إخلاء سبيل بتدابير احترازية",
    "عفو رئاسي",
    "قيد المحاكمة"
]
