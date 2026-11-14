# -*- coding: utf-8 -*-
"""
Database Manager for School Security Management System.
Completely isolated SQLite database with WAL mode and foreign key constraints.
"""
import re
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

from .config import DB_FILE, DEFAULT_ADMINISTRATIONS

logger = logging.getLogger(__name__)


def normalize_arabic(text: Any) -> str:
    """Normalizes Arabic text variants for flexible searches (alefs, teh marbuta, yaa)."""
    if not text:
        return ""
    s = str(text).strip().lower()
    # Normalize Alef variants
    s = re.sub(r"[إأآا]", "ا", s)
    # Normalize Teh Marbuta / Heh
    s = re.sub(r"ة", "ه", s)
    # Normalize Yaa / Alef Maksura
    s = re.sub(r"[ىي]", "ي", s)
    # Remove Arabic diacritics (Tashkeel)
    s = re.sub(r"[\u064B-\u0652]", "", s)
    # Normalize spaces
    s = re.sub(r"\s+", " ", s)
    return s.strip()


class SchoolSecurityDatabaseManager:
    """Independent SQLite Database Manager for School Security."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_FILE)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.create_function("NORMALIZE_AR", 1, normalize_arabic)
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Creates tables, foreign keys, and indexes for School Security."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Schools Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schools (
                    school_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    administration TEXT NOT NULL,
                    school_name TEXT NOT NULL,
                    affiliation TEXT DEFAULT '',
                    manager_name TEXT DEFAULT '',
                    manager_phone TEXT DEFAULT '',
                    security_officer_name TEXT DEFAULT '',
                    security_officer_phone TEXT DEFAULT '',
                    classrooms_count TEXT DEFAULT '',
                    gates_count TEXT DEFAULT '',
                    fire_extinguishers_count TEXT DEFAULT '',
                    fire_extinguisher_type TEXT DEFAULT '',
                    fire_extinguisher_weight TEXT DEFAULT '',
                    activated_fire_lines TEXT DEFAULT '',
                    inactive_fire_lines TEXT DEFAULT '',
                    working_cameras TEXT DEFAULT '',
                    non_working_cameras TEXT DEFAULT '',
                    camera_maintenance_company TEXT DEFAULT '',
                    buckets_count TEXT DEFAULT '',
                    valid_fire_hoses TEXT DEFAULT '',
                    invalid_fire_hoses TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Security Guards Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guards (
                    guard_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guard_name TEXT NOT NULL,
                    national_id TEXT DEFAULT '0',
                    phone TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. School Guard Assignments Table (Many-to-Many / Linked table)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS school_guard_assignments (
                    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    school_id INTEGER NOT NULL,
                    guard_id INTEGER NOT NULL,
                    address TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
                    FOREIGN KEY (guard_id) REFERENCES guards(guard_id) ON DELETE CASCADE,
                    UNIQUE (school_id, guard_id)
                );
            """)

            # 4. Import History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS import_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    schools_count INTEGER DEFAULT 0,
                    guards_count INTEGER DEFAULT 0,
                    assignments_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'SUCCESS',
                    log_details TEXT DEFAULT ''
                );
            """)

            # 5. Audit Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER,
                    details TEXT DEFAULT '',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # High-performance indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_schools_name ON schools(school_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_schools_admin ON schools(administration);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_schools_affil ON schools(affiliation);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_guards_name ON guards(guard_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_guards_nid ON guards(national_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_guards_phone ON guards(phone);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignment_school ON school_guard_assignments(school_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignment_guard ON school_guard_assignments(guard_id);")

            conn.commit()

    def log_audit(self, action_type: str, entity_type: str, entity_id: Optional[int], details: str = ""):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO audit_logs (action_type, entity_type, entity_id, details) VALUES (?, ?, ?, ?);",
                    (action_type, entity_type, entity_id, details)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Audit log error: {e}")

