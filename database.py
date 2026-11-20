import re
import json
import time
import sqlite3
import logging
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from config import (
    DB_FILE, DEFAULT_ADMINISTRATIONS, DEFAULT_CASE_TYPES,
)

logger = logging.getLogger(__name__)

def normalize_arabic(text: Any) -> str:
    """Normalizes Arabic text for flexible search (hamzas, alefs, teh marbuta, yaa)."""
    if not text:
        return ""
    s = str(text).strip().lower()
    # Normalize alef variants
    s = re.sub(r"[إأآٱ]", "ا", s)
    # Normalize teh marbuta
    s = re.sub(r"ة", "ه", s)
    # Normalize yaa / alef maksura
    s = re.sub(r"[ىي]", "ي", s)
    # Remove Arabic diacritics (tashkeel)
    s = re.sub(r"[\u064B-\u065F\u0670]", "", s)
    # Remove tatweel
    s = re.sub(r"ـ", "", s)
    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s)
    return s


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
    """Matches stored_name against query word by word in exact sequential order starting from word 1.
    
    Ensures:
    1. Search tokens must match beginning name tokens sequentially (token 0 matches token 0, etc.).
    2. Words appearing in the middle or end are NOT matched.
    3. The final token supports prefix matching (e.g. typing partial word), unless query has trailing space.
    4. Handles Arabic normalization and 'ال' prefix variants.
    """
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


_IMPORT_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_PHONE_FIELDS = {"principal_phone", "security_officer_phone", "phone"}
_NATIONAL_ID_FIELDS = {"national_id"}
_NUMERIC_FIELDS = {
    "class_count", "gate_count", "extinguisher_count", "extinguisher_weight",
    "active_fire_lines", "inactive_fire_lines", "working_cameras", "broken_cameras",
    "bucket_count", "usable_hoses", "unusable_hoses",
}


def _normalize_import_value(column: str, value: Any) -> str:
    """Normalize imported values for duplicate detection without using row numbers/notes."""
    raw = str(value or "").strip().translate(_IMPORT_DIGIT_MAP)
    if not raw:
        return ""
    normalized = normalize_arabic(raw)

    if column in _PHONE_FIELDS | _NATIONAL_ID_FIELDS:
        digits = "".join(char for char in normalized if char.isdigit())
        if column in _PHONE_FIELDS:
            if len(digits) == 12 and digits.startswith("20"):
                digits = "0" + digits[2:]
            elif len(digits) == 10 and digits.startswith("1"):
                # Excel may drop the leading zero when a mobile number is stored as a number.
                digits = "0" + digits
        return digits

    if column in _NUMERIC_FIELDS:
        numeric_text = normalized.replace(",", "").replace("٬", "").replace("٫", ".")
        try:
            number = Decimal(numeric_text)
            if number.is_finite():
                return str(int(number)) if number == number.to_integral_value() else format(number.normalize(), "f")
        except InvalidOperation:
            pass

    # Ignore spaces and common punctuation in names, schools and addresses.
    return re.sub(r"[\W_]+", "", normalized, flags=re.UNICODE)


class DatabaseManager:
    """High-performance SQLite Relational Database Manager.
    Features:
    - Foreign keys enforcement
    - WAL (Write-Ahead Logging) mode for concurrent high-speed reads/writes
    - Parameterized queries to prevent SQL injection
    - Indexed lookups on national_id, names, and foreign keys
    """
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or DB_FILE)
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=20.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.create_function("NORMALIZE_AR", 1, normalize_arabic)
        conn.create_function("MATCH_NAME_SEQUENTIAL", 2, match_name_sequential)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def safe_checkpoint_and_close(self, max_retries: int = 3, retry_delay: float = 0.5) -> bool:
        """Safely checkpoints all WAL frames to the main database file and verifies integrity.
        Uses PRAGMA wal_checkpoint(TRUNCATE) to merge all journal frames into the database
        and truncate the WAL file to 0 bytes.
        
        Returns:
            bool: True if checkpoint succeeded and integrity check passed.
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
                            logger.warning("WAL checkpoint busy (attempt %d/%d). Retrying...", attempt + 1, max_retries)
                            time.sleep(retry_delay)
                            continue

                    cur.execute("PRAGMA integrity_check;")
                    check_result = cur.fetchone()[0]
                    if check_result != "ok":
                        logger.error("Database integrity check failed: %s", check_result)
                        return False

                    logger.info("WAL checkpoint (TRUNCATE) and integrity check succeeded on %s.", self.db_path)
                    return True
                finally:
                    conn.close()
            except Exception as e:
                logger.error("Error during WAL checkpoint on %s: %s", self.db_path, e)
                time.sleep(retry_delay)

        return False

    def init_database(self) -> None:
        """Initializes database schema with constraints, foreign keys, and indexes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Administrations Table (الإدارات التعليمية)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Administrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE
                );
            """)

            # 2. Case Types Table (أنواع القضايا)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS CaseTypes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE
                );
            """)

            # 3. Employees Table (الموظفون / المعلمون)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    national_id TEXT NOT NULL DEFAULT '0',
                    administration_id INTEGER,
                    school TEXT,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (administration_id) REFERENCES Administrations(id) ON DELETE SET NULL
                );
            """)

            # 4. Excluded Records Table (بيانات المستبعدين)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ExcludedRecords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_number INTEGER,
                    employee_id INTEGER NOT NULL,
                    case_type_id INTEGER,
                    current_job TEXT,
                    nominee_job TEXT,
                    exclusion_entity TEXT,
                    exclusion_date TEXT,
                    exclusion_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES Employees(id) ON DELETE CASCADE,
                    FOREIGN KEY (case_type_id) REFERENCES CaseTypes(id) ON DELETE SET NULL
                );
            """)

            # 5. Prisoner Records Table (بيانات المسجونين)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS PrisonerRecords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_number INTEGER,
                    employee_id INTEGER NOT NULL,
                    case_number TEXT,
                    case_type_id INTEGER,
                    court_ruling TEXT,
                    current_status TEXT,
                    release_date TEXT,
                    housing_location TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES Employees(id) ON DELETE CASCADE,
                    FOREIGN KEY (case_type_id) REFERENCES CaseTypes(id) ON DELETE SET NULL
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS AppSettings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL
                );
            """)

            cursor.execute("DROP TABLE IF EXISTS SchoolInsuranceRecords;")
            cursor.execute("DROP TABLE IF EXISTS GuardSecurityRecords;")

            # Automatic Schema Migration: ensure record_number exists
            try:
                cursor.execute("ALTER TABLE ExcludedRecords ADD COLUMN record_number INTEGER;")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE PrisonerRecords ADD COLUMN record_number INTEGER;")
            except Exception:
                pass

            # Automatic Schema Migration: ensure Employees allows duplicate '0' for national_id
            try:
                emp_ddl = cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Employees';").fetchone()
                if emp_ddl and "UNIQUE" in emp_ddl[0].upper():
                    cursor.execute("PRAGMA foreign_keys = OFF;")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS Employees_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            full_name TEXT NOT NULL,
                            national_id TEXT NOT NULL DEFAULT '0',
                            administration_id INTEGER,
                            school TEXT,
                            phone TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (administration_id) REFERENCES Administrations(id) ON DELETE SET NULL
                        );
                    """)
                    cursor.execute("""
                        INSERT INTO Employees_new (id, full_name, national_id, administration_id, school, phone, created_at)
                        SELECT id, full_name, 
                               CASE WHEN national_id LIKE '%مؤقت%' OR national_id = '' OR national_id IS NULL THEN '0' ELSE national_id END,
                               administration_id, school, phone, created_at
                        FROM Employees;
                    """)
                    cursor.execute("DROP TABLE Employees;")
                    cursor.execute("ALTER TABLE Employees_new RENAME TO Employees;")
                    cursor.execute("PRAGMA foreign_keys = ON;")
            except Exception as mig_err:
                logger.error(f"Migration error for Employees table: {mig_err}")

            # Performance Indexes & Uniqueness (Only non-zero national IDs are unique)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_national_id ON Employees(national_id);")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_emp_national_id_unique ON Employees(national_id) WHERE national_id IS NOT NULL AND national_id != '' AND national_id != '0';")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_full_name ON Employees(full_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_admin_id ON Employees(administration_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_excluded_emp ON ExcludedRecords(employee_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_excluded_case ON ExcludedRecords(case_type_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prisoner_emp ON PrisonerRecords(employee_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prisoner_case ON PrisonerRecords(case_type_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_prisoner_status ON PrisonerRecords(current_status);")
            conn.commit()

        # Seed defaults
        self._seed_default_data()

    def _seed_default_data(self) -> None:
        """Seed default Alexandria administrations and standard case categories."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for admin_name in DEFAULT_ADMINISTRATIONS:
                cursor.execute("INSERT OR IGNORE INTO Administrations (name) VALUES (?);", (admin_name.strip(),))
            for case_name in DEFAULT_CASE_TYPES:
                cursor.execute("INSERT OR IGNORE INTO CaseTypes (name) VALUES (?);", (case_name.strip(),))
            conn.commit()

    def clear_all_data(self) -> None:
        """Reset application records while preserving the schema and defaults."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ExcludedRecords;")
            cursor.execute("DELETE FROM PrisonerRecords;")
            cursor.execute("DROP TABLE IF EXISTS SchoolInsuranceRecords;")
            cursor.execute("DROP TABLE IF EXISTS GuardSecurityRecords;")
            cursor.execute("DELETE FROM Employees;")
            cursor.execute("DELETE FROM CaseTypes;")
            cursor.execute("DELETE FROM Administrations;")
            try:
                cursor.execute("DELETE FROM sqlite_sequence;")
            except Exception:
                pass
            conn.commit()
        # Re-seed defaults
        self._seed_default_data()

    def check_duplicate_employee(self, full_name: str = "", national_id: str = "0") -> List[Dict[str, Any]]:
        """Checks if a name or national ID already exists in the system and returns its existing records."""
        clean_name = str(full_name).strip() if full_name else ""
        clean_nid = str(national_id).strip() if national_id else "0"
        has_name = len(clean_name) >= 3
        has_nid = clean_nid and clean_nid != "0" and not clean_nid.startswith("مؤقت") and len(clean_nid) >= 6

        if not has_name and not has_nid:
            return []

        results = []
        with self.get_connection() as conn:
            cur = conn.cursor()
            if has_name and has_nid:
                cur.execute("""
                    SELECT e.id, e.full_name, e.national_id, a.name as administration_name, e.school
                    FROM Employees e
                    LEFT JOIN Administrations a ON e.administration_id = a.id
                    WHERE (e.national_id != '0' AND (e.national_id = ? OR (length(?) >= 8 AND e.national_id LIKE ? || '%')))
                       OR NORMALIZE_AR(e.full_name) = NORMALIZE_AR(?)
                       OR (length(?) >= 12 AND NORMALIZE_AR(e.full_name) LIKE NORMALIZE_AR(?) || '%');
                """, (clean_nid, clean_nid, clean_nid, clean_name, clean_name, clean_name))
            elif has_name:
                cur.execute("""
                    SELECT e.id, e.full_name, e.national_id, a.name as administration_name, e.school
                    FROM Employees e
                    LEFT JOIN Administrations a ON e.administration_id = a.id
                    WHERE NORMALIZE_AR(e.full_name) = NORMALIZE_AR(?)
                       OR (length(?) >= 12 AND NORMALIZE_AR(e.full_name) LIKE NORMALIZE_AR(?) || '%');
                """, (clean_name, clean_name, clean_name))
            else: # has_nid only
                cur.execute("""
                    SELECT e.id, e.full_name, e.national_id, a.name as administration_name, e.school
                    FROM Employees e
                    LEFT JOIN Administrations a ON e.administration_id = a.id
                    WHERE e.national_id != '0' AND (e.national_id = ? OR (length(?) >= 8 AND e.national_id LIKE ? || '%'));
                """, (clean_nid, clean_nid, clean_nid))

            emp_rows = cur.fetchall()
            for r in emp_rows:
                emp_id = r["id"]
                # Get exclusions
                cur.execute("""
                    SELECT ex.record_number, ct.name as case_name, ex.exclusion_date, ex.exclusion_entity
                    FROM ExcludedRecords ex
                    LEFT JOIN CaseTypes ct ON ex.case_type_id = ct.id
                    WHERE ex.employee_id = ?;
                """, (emp_id,))
                ex_records = cur.fetchall()

                # Get prisoners
                cur.execute("""
                    SELECT pr.record_number, ct.name as case_name, pr.case_number, pr.current_status
                    FROM PrisonerRecords pr
                    LEFT JOIN CaseTypes ct ON pr.case_type_id = ct.id
                    WHERE pr.employee_id = ?;
                """, (emp_id,))
                pr_records = cur.fetchall()

                results.append({
                    "id": emp_id,
                    "full_name": r["full_name"],
                    "national_id": r["national_id"],
                    "administration_name": r["administration_name"] or "غير محدد",
                    "school": r["school"] or "غير محدد",
                    "exclusions": [dict(x) for x in ex_records],
                    "prisoners": [dict(p) for p in pr_records],
                })
        return results

    # --- Lookup Helpers with In-Memory Caching Support ---
    def get_or_create_administration(self, name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        if not name or not str(name).strip():
            return None
        clean_name = str(name).strip()
        close_conn = False
        if conn is None:
            conn = self.get_connection()
            close_conn = True
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM Administrations WHERE name = ? COLLATE NOCASE;", (clean_name,))
            row = cur.fetchone()
            if row:
                return row["id"]
            cur.execute("INSERT INTO Administrations (name) VALUES (?);", (clean_name,))
            return cur.lastrowid
        finally:
            if close_conn:
                conn.commit()
                conn.close()

    def get_or_create_case_type(self, name: str, conn: Optional[sqlite3.Connection] = None) -> Optional[int]:
        if not name or not str(name).strip():
            return None
        clean_name = str(name).strip()
        close_conn = False
        if conn is None:
            conn = self.get_connection()
            close_conn = True
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM CaseTypes WHERE name = ? COLLATE NOCASE;", (clean_name,))
            row = cur.fetchone()
            if row:
                return row["id"]
            cur.execute("INSERT INTO CaseTypes (name) VALUES (?);", (clean_name,))
            return cur.lastrowid
        finally:
            if close_conn:
                conn.commit()
                conn.close()

    def get_or_create_employee(self, full_name: str, national_id: str, 
                               administration_id: Optional[int] = None, 
                               school: str = "", phone: str = "",
                               conn: Optional[sqlite3.Connection] = None) -> int:
        clean_nid = str(national_id).strip() if national_id else "0"
        if not clean_nid or clean_nid.lower() in ["nan", "none", "null", ""] or "مؤقت" in clean_nid or set(clean_nid) == {"0"}:
            clean_nid = "0"
        clean_name = str(full_name).strip()
        clean_school = str(school).strip() if school else ""
        clean_phone = str(phone).strip() if phone else ""

        close_conn = False
        if conn is None:
            conn = self.get_connection()
            close_conn = True

        try:
            cur = conn.cursor()
            row = None
            if clean_nid != "0":
                cur.execute("SELECT id, administration_id, school, phone FROM Employees WHERE national_id = ?;", (clean_nid,))
                row = cur.fetchone()

            if not row:
                if administration_id:
                    cur.execute("SELECT id, administration_id, school, phone FROM Employees WHERE full_name = ? AND administration_id = ?;", (clean_name, administration_id))
                else:
                    cur.execute("SELECT id, administration_id, school, phone FROM Employees WHERE full_name = ?;", (clean_name,))
                row = cur.fetchone()

            if row:
                emp_id = row["id"]
                # Update employee details if missing previously
                updates = []
                params = []
                if clean_name:
                    updates.append("full_name = ?")
                    params.append(clean_name)
                if clean_nid != "0":
                    updates.append("national_id = ?")
                    params.append(clean_nid)
                if administration_id and not row["administration_id"]:
                    updates.append("administration_id = ?")
                    params.append(administration_id)
                if clean_school and not row["school"]:
                    updates.append("school = ?")
                    params.append(clean_school)
                if clean_phone and not row["phone"]:
                    updates.append("phone = ?")
                    params.append(clean_phone)
                if updates:
                    params.append(emp_id)
                    cur.execute(f"UPDATE Employees SET {', '.join(updates)} WHERE id = ?;", params)
                return emp_id
            else:
                cur.execute("""
                    INSERT INTO Employees (full_name, national_id, administration_id, school, phone)
                    VALUES (?, ?, ?, ?, ?);
                """, (clean_name, clean_nid, administration_id, clean_school, clean_phone))
                return cur.lastrowid
        finally:
            if close_conn:
                conn.commit()
                conn.close()

    # --- Fetch List Options ---
    def get_administrations(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            if category == "excluded":
                cur.execute("""
                    SELECT DISTINCT adm.id, adm.name 
                    FROM Administrations adm
                    JOIN Employees e ON e.administration_id = adm.id
                    JOIN ExcludedRecords er ON er.employee_id = e.id
                    ORDER BY adm.name ASC;
                """)
            elif category == "prisoners":
                cur.execute("""
                    SELECT DISTINCT adm.id, adm.name 
                    FROM Administrations adm
                    JOIN Employees e ON e.administration_id = adm.id
                    JOIN PrisonerRecords pr ON pr.employee_id = e.id
                    ORDER BY adm.name ASC;
                """)
            else:
                cur.execute("SELECT id, name FROM Administrations ORDER BY name ASC;")
            return [dict(row) for row in cur.fetchall()]

    def get_case_types(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            if category == "excluded":
                cur.execute("""
                    SELECT DISTINCT ct.id, ct.name 
                    FROM CaseTypes ct
                    JOIN ExcludedRecords er ON er.case_type_id = ct.id
                    ORDER BY ct.name ASC;
                """)
            elif category == "prisoners":
                cur.execute("""
                    SELECT DISTINCT ct.id, ct.name 
                    FROM CaseTypes ct
                    JOIN PrisonerRecords pr ON pr.case_type_id = ct.id
                    ORDER BY ct.name ASC;
                """)
            else:
                cur.execute("SELECT id, name FROM CaseTypes ORDER BY name ASC;")
            return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def _build_search_clause(query: str, fields: List[str], name_fields: Optional[List[str]] = None) -> Tuple[str, List[Any]]:
        """Builds multi-word Arabic normalized search clause.
        
        Requirements:
        1. Name fields (e.g. e.full_name) match ONLY from the beginning of the full name in exact sequence (First Name Matching).
        2. Multi-word name queries match the beginning of the full name word by word in exact order.
        3. Other fields (national_id, school, administration, case_type, etc.) retain multi-word matching evaluated per-field
           to prevent cross-field false positive matches.
        4. Handles extra whitespace, Arabic normalization, 'ال' prefix variants, and compound names (عبد/ابو).
        """
        clean_q = " ".join(query.strip().split())
        if not clean_q:
            return "", []

        words = clean_q.split()
        if not words:
            return "", []

        # Identify name fields vs non-name fields
        if name_fields is not None:
            n_fields = list(name_fields)
            o_fields = [f for f in fields if f not in n_fields]
        else:
            n_fields = []
            o_fields = []
            for f in fields:
                f_lower = f.lower()
                if any(k in f_lower for k in ("full_name", "guard_name", "manager_name", "security_officer_name")):
                    n_fields.append(f)
                else:
                    o_fields.append(f)

        name_clause = ""
        name_params: List[Any] = []
        if n_fields:
            name_subclauses = []
            for nf in n_fields:
                raw_col = nf
                if raw_col.startswith("NORMALIZE_AR(") and raw_col.endswith(")"):
                    raw_col = raw_col[13:-1]
                name_subclauses.append(f"MATCH_NAME_SEQUENTIAL({raw_col}, ?)")
                name_params.append(clean_q)

            if name_subclauses:
                name_clause = f"({' OR '.join(name_subclauses)})"

        other_clause = ""
        other_params: List[Any] = []
        if o_fields:
            field_clauses = []
            for of in o_fields:
                of_sub = []
                for w in words:
                    norm_w = normalize_arabic(w)
                    w_vars = [norm_w]
                    if norm_w.startswith("ال") and len(norm_w) > 3:
                        w_vars.append(norm_w[2:])
                    elif not norm_w.startswith("ال") and len(norm_w) > 1:
                        w_vars.append("ال" + norm_w)

                    var_clauses = []
                    for v in w_vars:
                        if of.startswith("NORMALIZE_AR"):
                            var_clauses.append(f"{of} LIKE ?")
                            other_params.append(f"%{v}%")
                        else:
                            var_clauses.append(f"{of} LIKE ?")
                            other_params.append(f"%{w}%")
                    if var_clauses:
                        of_sub.append(f"({' OR '.join(var_clauses)})")
                if of_sub:
                    field_clauses.append(f"({' AND '.join(of_sub)})")

            if field_clauses:
                other_clause = f"({' OR '.join(field_clauses)})"

        if name_clause and other_clause:
            return f" AND ({name_clause} OR {other_clause})", name_params + other_params
        elif name_clause:
            return f" AND ({name_clause})", name_params
        elif other_clause:
            return f" AND ({other_clause})", other_params
        return "", []

    # --- Excluded Records Operations ---
    def search_excluded(self, query: str = "", admin_id: Optional[int] = None, 
                        case_type_id: Optional[int] = None, case_type_query: str = "",
                        limit: int = 500, offset: int = 0,
                        search_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            sql = """
                SELECT 
                    er.id,
                    er.record_number,
                    e.id AS employee_id,
                    e.full_name,
                    e.national_id,
                    e.school,
                    e.phone,
                    adm.id AS admin_id,
                    IFNULL(adm.name, 'غير محدد') AS administration_name,
                    ct.id AS case_type_id,
                    IFNULL(ct.name, 'غير محدد') AS case_type_name,
                    er.current_job,
                    er.nominee_job,
                    er.exclusion_entity,
                    er.exclusion_date,
                    er.exclusion_reason,
                    er.created_at
                FROM ExcludedRecords er
                JOIN Employees e ON er.employee_id = e.id
                LEFT JOIN Administrations adm ON e.administration_id = adm.id
                LEFT JOIN CaseTypes ct ON er.case_type_id = ct.id
                WHERE 1=1
            """
            params: List[Any] = []
            if query:
                fields = search_fields or [
                    "NORMALIZE_AR(e.full_name)",
                    "e.national_id",
                    "NORMALIZE_AR(e.school)",
                    "NORMALIZE_AR(adm.name)",
                    "NORMALIZE_AR(ct.name)",
                    "NORMALIZE_AR(er.nominee_job)",
                    "NORMALIZE_AR(er.current_job)",
                    "NORMALIZE_AR(er.exclusion_entity)",
                    "NORMALIZE_AR(er.exclusion_reason)",
                    "CAST(er.record_number AS TEXT)"
                ]
                clause, c_params = self._build_search_clause(query, fields)
                sql += clause
                params.extend(c_params)
            if admin_id:
                sql += " AND e.administration_id = ?"
                params.append(admin_id)
            if case_type_id:
                sql += " AND er.case_type_id = ?"
                params.append(case_type_id)
            elif case_type_query and case_type_query.strip():
                c_clause, c_params = self._build_search_clause(case_type_query, ["NORMALIZE_AR(ct.name)"])
                sql += c_clause
                params.extend(c_params)

            sql += " ORDER BY COALESCE(er.record_number, er.id) ASC LIMIT ? OFFSET ?;"
            params.extend([limit, offset])

            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def count_excluded(self, query: str = "", admin_id: Optional[int] = None, 
                       case_type_id: Optional[int] = None, case_type_query: str = "",
                       search_fields: Optional[List[str]] = None) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            sql = """
                SELECT COUNT(*) as cnt
                FROM ExcludedRecords er
                JOIN Employees e ON er.employee_id = e.id
                LEFT JOIN Administrations adm ON e.administration_id = adm.id
                LEFT JOIN CaseTypes ct ON er.case_type_id = ct.id
                WHERE 1=1
            """
            params: List[Any] = []
            if query:
                fields = search_fields or [
                    "NORMALIZE_AR(e.full_name)",
                    "e.national_id",
                    "NORMALIZE_AR(e.school)",
                    "NORMALIZE_AR(adm.name)",
                    "NORMALIZE_AR(ct.name)",
                    "NORMALIZE_AR(er.nominee_job)",
                    "NORMALIZE_AR(er.current_job)",
                    "NORMALIZE_AR(er.exclusion_entity)",
                    "NORMALIZE_AR(er.exclusion_reason)",
                    "CAST(er.record_number AS TEXT)"
                ]
                clause, c_params = self._build_search_clause(query, fields)
                sql += clause
                params.extend(c_params)
            if admin_id:
                sql += " AND e.administration_id = ?"
                params.append(admin_id)
            if case_type_id:
                sql += " AND er.case_type_id = ?"
                params.append(case_type_id)
            elif case_type_query and case_type_query.strip():
                c_clause, c_params = self._build_search_clause(case_type_query, ["NORMALIZE_AR(ct.name)"])
                sql += c_clause
                params.extend(c_params)
            cur.execute(sql, params)
            return cur.fetchone()["cnt"]

    # --- Prisoner Records Operations ---
    def search_prisoners(self, query: str = "", admin_id: Optional[int] = None, 
                         case_type_id: Optional[int] = None, case_type_query: str = "",
                         status: Optional[str] = None,
                         limit: int = 500, offset: int = 0,
                         search_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            sql = """
                SELECT 
                    pr.id,
                    pr.record_number,
                    e.id AS employee_id,
                    e.full_name,
                    e.national_id,
                    e.school,
                    e.phone,
                    adm.id AS admin_id,
                    IFNULL(adm.name, 'غير محدد') AS administration_name,
                    ct.id AS case_type_id,
                    IFNULL(ct.name, 'غير محدد') AS case_type_name,
                    pr.case_number,
                    pr.court_ruling,
                    pr.current_status,
                    pr.release_date,
                    pr.housing_location,
                    pr.created_at
                FROM PrisonerRecords pr
                JOIN Employees e ON pr.employee_id = e.id
                LEFT JOIN Administrations adm ON e.administration_id = adm.id
                LEFT JOIN CaseTypes ct ON pr.case_type_id = ct.id
                WHERE 1=1
            """
            params: List[Any] = []
            if query:
                fields = search_fields or [
                    "NORMALIZE_AR(e.full_name)",
                    "e.national_id",
                    "NORMALIZE_AR(e.school)",
                    "NORMALIZE_AR(adm.name)",
                    "NORMALIZE_AR(ct.name)",
                    "NORMALIZE_AR(pr.case_number)",
                    "NORMALIZE_AR(pr.court_ruling)",
                    "NORMALIZE_AR(pr.current_status)",
                    "NORMALIZE_AR(pr.housing_location)",
                    "CAST(pr.record_number AS TEXT)"
                ]
                clause, c_params = self._build_search_clause(query, fields)
                sql += clause
                params.extend(c_params)
            if admin_id:
                sql += " AND e.administration_id = ?"
                params.append(admin_id)
            if case_type_id:
                sql += " AND pr.case_type_id = ?"
                params.append(case_type_id)
            elif case_type_query and case_type_query.strip():
                c_clause, c_params = self._build_search_clause(case_type_query, ["NORMALIZE_AR(ct.name)"])
                sql += c_clause
                params.extend(c_params)
            if status:
                sql += " AND pr.current_status = ?"
                params.append(status)

            sql += " ORDER BY COALESCE(pr.record_number, pr.id) ASC LIMIT ? OFFSET ?;"
            params.extend([limit, offset])

            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def count_prisoners(self, query: str = "", admin_id: Optional[int] = None, 
                        case_type_id: Optional[int] = None, case_type_query: str = "", status: Optional[str] = None,
                        search_fields: Optional[List[str]] = None) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            sql = """
                SELECT COUNT(*) as cnt
                FROM PrisonerRecords pr
                JOIN Employees e ON pr.employee_id = e.id
                LEFT JOIN Administrations adm ON e.administration_id = adm.id
                LEFT JOIN CaseTypes ct ON pr.case_type_id = ct.id
                WHERE 1=1
            """
            params: List[Any] = []
            if query:
                fields = search_fields or [
                    "NORMALIZE_AR(e.full_name)",
                    "e.national_id",
                    "NORMALIZE_AR(e.school)",
                    "NORMALIZE_AR(adm.name)",
                    "NORMALIZE_AR(ct.name)",
                    "NORMALIZE_AR(pr.case_number)",
                    "NORMALIZE_AR(pr.court_ruling)",
                    "NORMALIZE_AR(pr.current_status)",
                    "NORMALIZE_AR(pr.housing_location)",
                    "CAST(pr.record_number AS TEXT)"
                ]
                clause, c_params = self._build_search_clause(query, fields)
                sql += clause
                params.extend(c_params)
            if admin_id:
                sql += " AND e.administration_id = ?"
                params.append(admin_id)
            if case_type_id:
                sql += " AND pr.case_type_id = ?"
                params.append(case_type_id)
            elif case_type_query and case_type_query.strip():
                c_clause, c_params = self._build_search_clause(case_type_query, ["NORMALIZE_AR(ct.name)"])
                sql += c_clause
                params.extend(c_params)
            if status:
                sql += " AND pr.current_status = ?"
                params.append(status)
            cur.execute(sql, params)
            return cur.fetchone()["cnt"]

    # --- Employees Operations ---
    def search_employees(self, query: str = "", admin_id: Optional[int] = None, limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            sql = """
                SELECT 
                    e.id,
                    e.full_name,
                    e.national_id,
                    e.school,
                    e.phone,
                    adm.name AS administration_name,
                    (SELECT COUNT(*) FROM ExcludedRecords WHERE employee_id = e.id) as excluded_count,
                    (SELECT COUNT(*) FROM PrisonerRecords WHERE employee_id = e.id) as prisoner_count,
                    e.created_at
                FROM Employees e
                LEFT JOIN Administrations adm ON e.administration_id = adm.id
                WHERE 1=1
            """
            params: List[Any] = []
            if query:
                fields = [
                    "NORMALIZE_AR(e.full_name)",
                    "e.national_id",
                    "NORMALIZE_AR(e.school)",
                    "NORMALIZE_AR(adm.name)",
                    "e.phone"
                ]
                clause, c_params = self._build_search_clause(query, fields)
                sql += clause
                params.extend(c_params)
            if admin_id:
                sql += " AND e.administration_id = ?"
                params.append(admin_id)

            sql += " ORDER BY e.id DESC LIMIT ? OFFSET ?;"
            params.extend([limit, offset])

            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    # --- Global Unified Search ---
    def unified_search(self, query: str = "", case_type_id: Optional[int] = None, 
                       case_type_query: str = "", admin_id: Optional[int] = None) -> Dict[str, Any]:
        """Performs instantaneous unified search across both categories.
        Focuses on Name (prefix/sequential), National ID, Phone, and Record/Case Number.
        """
        ex_fields = [
            "NORMALIZE_AR(e.full_name)",
            "e.national_id",
            "e.phone",
            "CAST(er.record_number AS TEXT)"
        ]
        pr_fields = [
            "NORMALIZE_AR(e.full_name)",
            "e.national_id",
            "NORMALIZE_AR(pr.case_number)",
            "e.phone",
            "CAST(pr.record_number AS TEXT)"
        ]
        excluded = self.search_excluded(
            query=query, admin_id=admin_id, case_type_id=case_type_id, 
            case_type_query=case_type_query, limit=2000, search_fields=ex_fields
        )
        prisoners = self.search_prisoners(
            query=query, admin_id=admin_id, case_type_id=case_type_id, 
            case_type_query=case_type_query, limit=2000, search_fields=pr_fields
        )
        return {
            "excluded": excluded,
            "prisoners": prisoners,
            "employees": []
        }

    # --- Employee Record Inspection & Purging ---
    def get_employee_records_count(self, employee_id: int) -> Dict[str, Any]:
        """Returns the breakdown of records registered under an employee across Excluded and Prisoner tables."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, full_name, national_id FROM Employees WHERE id = ?;", (employee_id,))
            emp = cur.fetchone()
            if not emp:
                return {"exists": False, "excluded": 0, "prisoners": 0, "total": 0, "name": "", "national_id": ""}
            cur.execute("SELECT COUNT(*) FROM ExcludedRecords WHERE employee_id = ?;", (employee_id,))
            ex_cnt = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM PrisonerRecords WHERE employee_id = ?;", (employee_id,))
            pr_cnt = cur.fetchone()[0]
            return {
                "exists": True,
                "id": emp["id"],
                "name": emp["full_name"],
                "national_id": emp["national_id"] or "0",
                "excluded": ex_cnt,
                "prisoners": pr_cnt,
                "total": ex_cnt + pr_cnt
            }

    def delete_employee_completely(self, employee_id: int) -> bool:
        """Purges an employee and all their associated records across Excluded and Prisoner tables."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM ExcludedRecords WHERE employee_id = ?;", (employee_id,))
            cur.execute("DELETE FROM PrisonerRecords WHERE employee_id = ?;", (employee_id,))
            cur.execute("DELETE FROM Employees WHERE id = ?;", (employee_id,))
            conn.commit()
            return True

    def delete_record(self, table_name: str, record_id: int, delete_orphan_employee: bool = True) -> bool:
        """Deletes a record safely by ID from an allowed table, and cleans up orphan employee if no remaining records."""
        allowed_tables = ["ExcludedRecords", "PrisonerRecords", "Employees", "Administrations", "CaseTypes"]
        if table_name not in allowed_tables:
            raise ValueError(f"Table {table_name} is not allowed for deletion.")
        with self.get_connection() as conn:
            cur = conn.cursor()
            emp_id = None
            if table_name in ("ExcludedRecords", "PrisonerRecords") and delete_orphan_employee:
                cur.execute(f"SELECT employee_id FROM {table_name} WHERE id = ?;", (record_id,))
                row = cur.fetchone()
                if row:
                    emp_id = row["employee_id"]

            cur.execute(f"DELETE FROM {table_name} WHERE id = ?;", (record_id,))

            if emp_id and delete_orphan_employee:
                cur.execute("SELECT (SELECT COUNT(*) FROM ExcludedRecords WHERE employee_id = ?) + (SELECT COUNT(*) FROM PrisonerRecords WHERE employee_id = ?) AS cnt;", (emp_id, emp_id))
                tot = cur.fetchone()["cnt"]
                if tot == 0:
                    cur.execute("DELETE FROM Employees WHERE id = ?;", (emp_id,))

            conn.commit()
            return True

    def add_excluded_record(self, data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            emp_id = self.get_or_create_employee(
                full_name=data.get("full_name", ""),
                national_id=data.get("national_id", ""),
                administration_id=data.get("administration_id"),
                school=data.get("school", ""),
                phone=data.get("phone", ""),
                conn=conn
            )
            cur.execute("""
                INSERT INTO ExcludedRecords (
                    record_number, employee_id, case_type_id, current_job, nominee_job, 
                    exclusion_entity, exclusion_date, exclusion_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                data.get("record_number"),
                emp_id,
                data.get("case_type_id"),
                data.get("current_job", ""),
                data.get("nominee_job", ""),
                data.get("exclusion_entity", ""),
                data.get("exclusion_date", ""),
                data.get("exclusion_reason", "")
            ))
            conn.commit()
            return cur.lastrowid

    def add_prisoner_record(self, data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cur = conn.cursor()
            emp_id = self.get_or_create_employee(
                full_name=data.get("full_name", ""),
                national_id=data.get("national_id", ""),
                administration_id=data.get("administration_id"),
                school=data.get("school", ""),
                phone=data.get("phone", ""),
                conn=conn
            )
            cur.execute("""
                INSERT INTO PrisonerRecords (
                    record_number, employee_id, case_number, case_type_id, court_ruling, 
                    current_status, release_date, housing_location
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                data.get("record_number"),
                emp_id,
                data.get("case_number", ""),
                data.get("case_type_id"),
                data.get("court_ruling", ""),
                data.get("current_status", "على رأس العمل"),
                data.get("release_date", ""),
                data.get("housing_location", "")
            ))
            conn.commit()
            return cur.lastrowid

    def update_excluded_record(self, record_id: int, data: Dict[str, Any]) -> bool:
        """Updates an existing excluded record and its associated employee details."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT employee_id FROM ExcludedRecords WHERE id = ?;", (record_id,))
            row = cur.fetchone()
            if not row:
                return False
            emp_id = row["employee_id"]

            clean_nid = str(data.get("national_id", "0")).strip()
            if not clean_nid or clean_nid.lower() in ["nan", "none", "null", ""] or "مؤقت" in clean_nid or set(clean_nid) == {"0"}:
                clean_nid = "0"

            # 1. Update Employee details
            cur.execute("""
                UPDATE Employees 
                SET full_name = ?, national_id = ?, administration_id = ?, school = ?, phone = ?
                WHERE id = ?;
            """, (
                str(data.get("full_name", "")).strip(),
                clean_nid,
                data.get("administration_id"),
                str(data.get("school", "")).strip(),
                str(data.get("phone", "")).strip(),
                emp_id
            ))

            # 2. Update ExcludedRecord details
            cur.execute("""
                UPDATE ExcludedRecords 
                SET record_number = ?, case_type_id = ?, current_job = ?, nominee_job = ?, 
                    exclusion_entity = ?, exclusion_date = ?, exclusion_reason = ?
                WHERE id = ?;
            """, (
                data.get("record_number"),
                data.get("case_type_id"),
                str(data.get("current_job", "")).strip(),
                str(data.get("nominee_job", "")).strip(),
                str(data.get("exclusion_entity", "")).strip(),
                str(data.get("exclusion_date", "")).strip(),
                str(data.get("exclusion_reason", "")).strip(),
                record_id
            ))
            conn.commit()
            return True

    def update_prisoner_record(self, record_id: int, data: Dict[str, Any]) -> bool:
        """Updates an existing prisoner record and its associated employee details."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT employee_id FROM PrisonerRecords WHERE id = ?;", (record_id,))
            row = cur.fetchone()
            if not row:
                return False
            emp_id = row["employee_id"]

            clean_nid = str(data.get("national_id", "0")).strip()
            if not clean_nid or clean_nid.lower() in ["nan", "none", "null", ""] or "مؤقت" in clean_nid or set(clean_nid) == {"0"}:
                clean_nid = "0"

            # 1. Update Employee details
            cur.execute("""
                UPDATE Employees 
                SET full_name = ?, national_id = ?, administration_id = ?, school = ?, phone = ?
                WHERE id = ?;
            """, (
                str(data.get("full_name", "")).strip(),
                clean_nid,
                data.get("administration_id"),
                str(data.get("school", "")).strip(),
                str(data.get("phone", "")).strip(),
                emp_id
            ))

            # 2. Update PrisonerRecord details
            cur.execute("""
                UPDATE PrisonerRecords 
                SET record_number = ?, case_number = ?, case_type_id = ?, court_ruling = ?, 
                    current_status = ?, release_date = ?, housing_location = ?
                WHERE id = ?;
            """, (
                data.get("record_number"),
                str(data.get("case_number", "")).strip(),
                data.get("case_type_id"),
                str(data.get("court_ruling", "")).strip(),
                str(data.get("current_status", "على رأس العمل")).strip(),
                str(data.get("release_date", "")).strip(),
                str(data.get("housing_location", "")).strip(),
                record_id
            ))
            conn.commit()
            return True


    # --- Dashboard Analytical Statistics ---
    def get_dashboard_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cur = conn.cursor()

            # Counters
            cur.execute("SELECT COUNT(*) FROM Employees;")
            total_employees = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM ExcludedRecords;")
            total_excluded = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM PrisonerRecords;")
            total_prisoners = cur.fetchone()[0]

            # Released or back to work count (handling all spelling variations)
            cur.execute("""
                SELECT COUNT(*) FROM PrisonerRecords 
                WHERE current_status LIKE '%عمل%' 
                   OR current_status LIKE '%افراج%' 
                   OR current_status LIKE '%إفراج%' 
                   OR current_status LIKE '%اخلاء%' 
                   OR current_status LIKE '%إخلاء%' 
                   OR current_status LIKE '%براءة%' 
                   OR current_status LIKE '%براء%';
            """)
            released_count = cur.fetchone()[0]

            # In prison / active custody count
            cur.execute("""
                SELECT COUNT(*) FROM PrisonerRecords 
                WHERE current_status LIKE '%حبس%' 
                   OR current_status LIKE '%عقوبة%' 
                   OR current_status LIKE '%مقيد%' 
                   OR current_status LIKE '%محبوس%';
            """)
            in_prison_count = cur.fetchone()[0]

            # Distribution by Administration (Top Administrations)
            cur.execute("""
                SELECT 
                    IFNULL(adm.name, 'غير محدد') AS admin_name,
                    COUNT(DISTINCT er.id) AS excluded_cnt,
                    COUNT(DISTINCT pr.id) AS prisoner_cnt
                FROM Administrations adm
                LEFT JOIN Employees e ON e.administration_id = adm.id
                LEFT JOIN ExcludedRecords er ON er.employee_id = e.id
                LEFT JOIN PrisonerRecords pr ON pr.employee_id = e.id
                GROUP BY adm.id
                HAVING (excluded_cnt > 0 OR prisoner_cnt > 0)
                ORDER BY (excluded_cnt + prisoner_cnt) DESC
                LIMIT 8;
            """)
            admin_breakdown = [dict(row) for row in cur.fetchall()]

            # Distribution by Case Types
            cur.execute("""
                SELECT 
                    ct.name AS case_name,
                    (SELECT COUNT(*) FROM ExcludedRecords WHERE case_type_id = ct.id) +
                    (SELECT COUNT(*) FROM PrisonerRecords WHERE case_type_id = ct.id) as total_cases
                FROM CaseTypes ct
                ORDER BY total_cases DESC
                LIMIT 8;
            """)
            case_breakdown = [dict(row) for row in cur.fetchall()]

            return {
                "total_employees": total_employees,
                "total_excluded": total_excluded,
                "total_prisoners": total_prisoners,
                "total_records": total_excluded + total_prisoners,
                "in_prison": in_prison_count,
                "released": released_count,
                "admin_breakdown": admin_breakdown,
                "case_breakdown": case_breakdown
            }

    # --- Duplicate Names Detection ---
    def find_duplicate_names(self) -> List[Dict[str, Any]]:
        """Finds employees with duplicate full names across all records.
        Returns a list of dicts grouped by duplicate name."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    e.full_name,
                    COUNT(*) as name_count,
                    GROUP_CONCAT(CASE WHEN e.national_id LIKE '%مؤقت%' OR e.national_id IS NULL OR e.national_id = '' THEN '0' ELSE e.national_id END, ' | ') as national_ids,
                    GROUP_CONCAT(IFNULL(adm.name, 'غير محدد'), ' | ') as administrations,
                    GROUP_CONCAT(IFNULL(e.school, ''), ' | ') as schools
                FROM Employees e
                LEFT JOIN Administrations adm ON e.administration_id = adm.id
                GROUP BY e.full_name COLLATE NOCASE
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC;
            """)
            return [dict(row) for row in cur.fetchall()]

    def find_duplicate_names_in_records(self) -> Dict[str, List[Dict[str, Any]]]:
        """Finds duplicate names appearing across Excluded and Prisoner records.
        Returns dict with 'excluded' and 'prisoners' keys containing duplicate records."""
        duplicates = {"excluded": [], "prisoners": []}
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            # Find names that appear more than once in ExcludedRecords
            cur.execute("""
                SELECT 
                    e.full_name,
                    COUNT(*) as cnt,
                    GROUP_CONCAT(CASE WHEN e.national_id LIKE '%مؤقت%' OR e.national_id IS NULL OR e.national_id = '' THEN '0' ELSE e.national_id END, ' | ') as national_ids
                FROM ExcludedRecords er
                JOIN Employees e ON er.employee_id = e.id
                GROUP BY e.full_name COLLATE NOCASE
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC;
            """)
            duplicates["excluded"] = [dict(row) for row in cur.fetchall()]
            
            # Find names that appear more than once in PrisonerRecords
            cur.execute("""
                SELECT 
                    e.full_name,
                    COUNT(*) as cnt,
                    GROUP_CONCAT(CASE WHEN e.national_id LIKE '%مؤقت%' OR e.national_id IS NULL OR e.national_id = '' THEN '0' ELSE e.national_id END, ' | ') as national_ids
                FROM PrisonerRecords pr
                JOIN Employees e ON pr.employee_id = e.id
                GROUP BY e.full_name COLLATE NOCASE
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC;
            """)
            duplicates["prisoners"] = [dict(row) for row in cur.fetchall()]
            
        return duplicates
