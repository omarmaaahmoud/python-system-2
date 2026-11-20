# -*- coding: utf-8 -*-
"""
Security Guards management service for School Security System.
Provides CRUD, assignments linking, multi-school support, and duplicate guard detection.
"""
from typing import List, Dict, Any, Optional, Tuple
from ..database import SchoolSecurityDatabaseManager


class GuardService:
    def __init__(self, db_manager: SchoolSecurityDatabaseManager):
        self.db = db_manager

    def get_guards(
        self,
        search_query: str = "",
        administration: str = "",
        school_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            where_clauses = []
            params: List[Any] = []

            if administration and administration.strip():
                where_clauses.append("s.administration = ?")
                params.append(administration.strip())

            if school_id:
                where_clauses.append("a.school_id = ?")
                params.append(school_id)

            if search_query and search_query.strip():
                clean_q = search_query.strip()
                pattern = f"%{clean_q}%"
                where_clauses.append("""(
                    MATCH_NAME_SEQUENTIAL(g.guard_name, ?) OR
                    g.national_id LIKE ? OR
                    g.phone LIKE ? OR
                    NORMALIZE_AR(s.school_name) LIKE NORMALIZE_AR(?) OR
                    NORMALIZE_AR(s.administration) LIKE NORMALIZE_AR(?) OR
                    a.address LIKE ?
                )""")
                params.extend([clean_q, pattern, pattern, pattern, pattern, pattern])

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            limit_sql = f"LIMIT {limit} OFFSET {offset}" if limit else ""

            query = f"""
                SELECT 
                    g.guard_id,
                    g.guard_name,
                    g.national_id,
                    g.phone,
                    g.notes,
                    g.created_at,
                    a.assignment_id,
                    a.school_id,
                    a.address,
                    s.school_name,
                    s.administration
                FROM guards g
                LEFT JOIN school_guard_assignments a ON g.guard_id = a.guard_id
                LEFT JOIN schools s ON a.school_id = s.school_id
                {where_sql}
                ORDER BY g.guard_id ASC
                {limit_sql};
            """
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_guard_by_id(self, guard_id: int) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM guards WHERE guard_id = ?;", (guard_id,)).fetchone()
            if not row:
                return None
            guard = dict(row)
            # Fetch assigned schools
            assignments = conn.execute("""
                SELECT a.assignment_id, a.address, a.created_at, s.school_id, s.school_name, s.administration
                FROM school_guard_assignments a
                INNER JOIN schools s ON a.school_id = s.school_id
                WHERE a.guard_id = ?
                ORDER BY s.school_name ASC;
            """, (guard_id,)).fetchall()
            guard["assignments"] = [dict(a) for a in assignments]
            guard["assigned_schools_count"] = len(assignments)
            return guard

    def add_guard(
        self,
        guard_name: str,
        national_id: str = "0",
        phone: str = "",
        notes: str = "",
        school_id: Optional[int] = None,
        address: str = ""
    ) -> int:
        clean_name = str(guard_name or "").strip()
        clean_nid = str(national_id or "0").strip()
        clean_phone = str(phone or "").strip()
        clean_notes = str(notes or "").strip()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO guards (guard_name, national_id, phone, notes) VALUES (?, ?, ?, ?);",
                (clean_name, clean_nid, clean_phone, clean_notes)
            )
            new_guard_id = int(cursor.lastrowid)

            if school_id:
                cursor.execute(
                    "INSERT OR IGNORE INTO school_guard_assignments (school_id, guard_id, address) VALUES (?, ?, ?);",
                    (school_id, new_guard_id, address.strip())
                )

            conn.commit()
            self.db.log_audit("ADD", "GUARD", new_guard_id, f"Added guard {clean_name}")
            return new_guard_id

    def update_guard(
        self,
        guard_id: int,
        guard_name: str,
        national_id: str = "0",
        phone: str = "",
        notes: str = "",
        school_id: Optional[int] = None,
        address: str = ""
    ) -> bool:
        clean_name = str(guard_name or "").strip()
        clean_nid = str(national_id or "0").strip()
        clean_phone = str(phone or "").strip()
        clean_notes = str(notes or "").strip()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE guards SET guard_name = ?, national_id = ?, phone = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE guard_id = ?;",
                (clean_name, clean_nid, clean_phone, clean_notes, guard_id)
            )

            if school_id is not None:
                # Update or insert assignment
                existing_assignment = cursor.execute(
                    "SELECT assignment_id FROM school_guard_assignments WHERE guard_id = ?;", (guard_id,)
                ).fetchone()

                if existing_assignment:
                    cursor.execute(
                        "UPDATE school_guard_assignments SET school_id = ?, address = ? WHERE assignment_id = ?;",
                        (school_id, address.strip(), existing_assignment[0])
                    )
                else:
                    cursor.execute(
                        "INSERT OR IGNORE INTO school_guard_assignments (school_id, guard_id, address) VALUES (?, ?, ?);",
                        (school_id, guard_id, address.strip())
                    )

            conn.commit()
            success = cursor.rowcount > 0
            if success:
                self.db.log_audit("UPDATE", "GUARD", guard_id, f"Updated guard {clean_name}")
            return success

    def delete_guard(self, guard_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM school_guard_assignments WHERE guard_id = ?;", (guard_id,))
            cursor.execute("DELETE FROM guards WHERE guard_id = ?;", (guard_id,))
            conn.commit()
            success = cursor.rowcount > 0
            if success:
                self.db.log_audit("DELETE", "GUARD", guard_id, f"Deleted guard {guard_id}")
            return success

    def assign_guard(self, school_id: int, guard_id: int, address: str = "") -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO school_guard_assignments (school_id, guard_id, address) VALUES (?, ?, ?);",
                (school_id, guard_id, address.strip())
            )
            conn.commit()
            return cursor.rowcount > 0

    def remove_assignment(self, assignment_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM school_guard_assignments WHERE assignment_id = ?;", (assignment_id,))
            conn.commit()
            return cursor.rowcount > 0

    def find_duplicate_guards(self) -> List[Dict[str, Any]]:
        """Finds guards that have duplicate National IDs or identical Name and Phone."""
        with self.db.get_connection() as conn:
            duplicates = []
            # 1. By National ID (valid non-zero)
            nid_rows = conn.execute("""
                SELECT national_id, COUNT(*) as cnt 
                FROM guards 
                WHERE national_id != '0' AND national_id != '' AND length(national_id) >= 6
                GROUP BY national_id 
                HAVING cnt > 1;
            """).fetchall()

            for nr in nid_rows:
                matched = conn.execute("""
                    SELECT g.*, s.school_name, s.administration, a.address 
                    FROM guards g
                    LEFT JOIN school_guard_assignments a ON g.guard_id = a.guard_id
                    LEFT JOIN schools s ON a.school_id = s.school_id
                    WHERE g.national_id = ?;
                """, (nr["national_id"],)).fetchall()
                duplicates.append({
                    "type": "تطابق الرقم القومي",
                    "key": nr["national_id"],
                    "count": nr["cnt"],
                    "guards": [dict(m) for m in matched]
                })

            # 2. By Name
            name_rows = conn.execute("""
                SELECT NORMALIZE_AR(guard_name) as norm_name, guard_name, COUNT(*) as cnt
                FROM guards
                WHERE guard_name IS NOT NULL AND length(TRIM(guard_name)) >= 3
                GROUP BY norm_name
                HAVING cnt > 1;
            """).fetchall()

            for nm in name_rows:
                matched = conn.execute("""
                    SELECT g.*, s.school_name, s.administration, a.address 
                    FROM guards g
                    LEFT JOIN school_guard_assignments a ON g.guard_id = a.guard_id
                    LEFT JOIN schools s ON a.school_id = s.school_id
                    WHERE NORMALIZE_AR(g.guard_name) = ?;
                """, (nm["norm_name"],)).fetchall()
                duplicates.append({
                    "type": "تطابق الاسم",
                    "key": nm["guard_name"],
                    "count": nm["cnt"],
                    "guards": [dict(m) for m in matched]
                })

            return duplicates

