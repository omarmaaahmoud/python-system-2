# -*- coding: utf-8 -*-
"""
Configuration and constants for the School Security Management System.
"""
from pathlib import Path
import sys

# Base Paths - Supports both source script and PyInstaller frozen executable
if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).resolve().parent
    MEIPASS_DIR = Path(getattr(sys, '_MEIPASS', EXE_DIR))
    BASE_DIR = EXE_DIR
    BUNDLE_DATA_DIR = MEIPASS_DIR / "data"
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    BUNDLE_DATA_DIR = BASE_DIR / "data"

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Dedicated SQLite database for the School Security System
DB_FILE = DATA_DIR / "school_security.db"

# Core Educational Administrations in Alexandria
DEFAULT_ADMINISTRATIONS = [
    "إدارة المنتزه أول",
    "إدارة المنتزه ثان",
    "إدارة شرق التعليمية",
    "إدارة وسط التعليمية",
    "إدارة الجمرك التعليمية",
    "إدارة غرب التعليمية",
    "إدارة العجمي التعليمية",
    "إدارة العامرية التعليمية",
    "إدارة برج العرب التعليمية",
    "ديوان عام المديرية"
]

# Educational Affiliations
DEFAULT_AFFILIATIONS = [
    "رسمي عربي",
    "رسمي لغات",
    "خاص عربي",
    "خاص لغات",
    "معاهد قومية",
    "فني صناعي",
    "فني تجاري",
    "فني زراعي",
    "تعليم مجتمعي",
    "أخرى"
]
