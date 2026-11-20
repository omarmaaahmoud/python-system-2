# -*- coding: utf-8 -*-
"""
Database Manager for School Security Management System.
Completely isolated SQLite database with WAL mode and foreign key constraints.
"""
import re
import time
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


def tokenize_name(text: Any) -> List[str]:
    """Tokenizes Arabic or English name into clean tokens, collapsing compound prefixes (عبد, ابو, ام)."""
    if not text:
        return []
    norm = normalize_arabic(text)
    raw_tokens = norm.split()
    tokens: List[str] = []
    i = 0
    while i < len(raw_tokens):
        w = raw_tokens[i]
        if w in ("عبد", "ابو", "ام") and i + 1 < len(raw_tokens):
            tokens.append(w + raw_tokens[i + 1])
            i += 2
        else:
            tokens.append(w)
            i += 1
    return tokens


def match_name_sequential(stored_name: Any, query: Any) -> bool:
    """Matches stored_name against query word by word in exact sequential order starting from word 1."""
    if not query:
        return True
    q_str = str(query).strip()
    if not q_str:
        return True
    if not stored_name:
        return False
    n_str = str(stored_name).strip()
    if not n_str:
        return False

    q_tokens = tokenize_name(q_str)
    n_tokens = tokenize_name(n_str)

    if not q_tokens:
        return True
    if len(n_tokens) < len(q_tokens):
        return False

    has_trailing_space = str(query).endswith(" ")

    for idx, q_tok in enumerate(q_tokens):
        n_tok = n_tokens[idx]
        is_last = (idx == len(q_tokens) - 1)

        def tokens_match(n: str, q: str, prefix_ok: bool) -> bool:
            if n == q:
                return True
            if prefix_ok and n.startswith(q):
                return True
            if n.startswith("ال") and len(n) > 3:
                n_no_al = n[2:]
                if n_no_al == q or (prefix_ok and n_no_al.startswith(q)):
                    return True
            if q.startswith("ال") and len(q) > 3:
                q_no_al = q[2:]
                if n == q_no_al or (prefix_ok and n.startswith(q_no_al)):
                    return True
            return False

        allow_prefix = is_last and not has_trailing_space
        if not tokens_match(n_tok, q_tok, allow_prefix):
            return False

    return True


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
        conn.create_function("MATCH_NAME_SEQUENTIAL", 2, match_name_sequential)
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            yield conn
        finally:
            conn.close()

    def safe_checkpoint_and_close(self, max_retries: int = 3, retry_delay: float = 0.5) -> bool:
        """Safely checkpoints all WAL frames to the main database file and verifies integrity.
        Uses PRAGMA wal_checkpoint(TRUNCATE) to merge all journal frames into the database
        and truncate the WAL file to 0 bytes.
        """
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                try:
                    cur = conn.cursor()
                    cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                    row = cur.fetchone()
                    if row:
                        busy, log, checkpointed = row[0], row[1], row[2]
                        if busy != 0:
                            logger.warning("SchoolSecurity WAL checkpoint busy (attempt %d/%d). Retrying...", attempt + 1, max_retries)
                            time.sleep(retry_delay)
                            continue

                    cur.execute("PRAGMA integrity_check;")
                    check_result = cur.fetchone()[0]
                    if check_result != "ok":
                        logger.error("SchoolSecurity database integrity check failed: %s", check_result)
                        return False

                    logger.info("SchoolSecurity WAL checkpoint (TRUNCATE) and integrity check succeeded on %s.", self.db_path)
                    return True
                finally:
                    conn.close()
            except Exception as e:
                logger.error("Error during SchoolSecurity WAL checkpoint on %s: %s", self.db_path, e)
                time.sleep(retry_delay)

        return False

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

    def clear_all_security_data(self):
        """Safely clears all schools, guards, assignments, and audit logs."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM school_guard_assignments;")
            cur.execute("DELETE FROM guards;")
            cur.execute("DELETE FROM schools;")
            cur.execute("DELETE FROM import_history;")
            cur.execute("DELETE FROM audit_logs;")
            try:
                cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('schools', 'guards', 'school_guard_assignments', 'import_history', 'audit_logs');")
            except Exception:
                pass
            conn.commit()
        logger.info("All school security data safely wiped for fresh import.")


