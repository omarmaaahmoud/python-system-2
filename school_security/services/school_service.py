# -*- coding: utf-8 -*-
"""
School management service for School Security System.
Provides CRUD, advanced search, filtering, and live KPI dashboard metrics.
"""
import re
from typing import List, Dict, Any, Optional
from ..database import SchoolSecurityDatabaseManager


class SchoolService:
    def __init__(self, db_manager: SchoolSecurityDatabaseManager):
        self.db = db_manager

    def get_schools(
        self,
        search_query: str = "",
        administration: str = "",
        affiliation: str = "",
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            where_clauses = []
            params: List[Any] = []

            if administration and administration.strip():
                where_clauses.append("s.administration = ?")
                params.append(administration.strip())

            if affiliation and affiliation.strip():
                where_clauses.append("s.affiliation = ?")
                params.append(affiliation.strip())

            if search_query and search_query.strip():
                pattern = f"%{search_query.strip()}%"
                where_clauses.append("""(
                    NORMALIZE_AR(s.school_name) LIKE NORMALIZE_AR(?) OR
                    NORMALIZE_AR(s.manager_name) LIKE NORMALIZE_AR(?) OR
                    s.manager_phone LIKE ? OR
                    NORMALIZE_AR(s.security_officer_name) LIKE NORMALIZE_AR(?) OR
                    s.security_officer_phone LIKE ? OR
                    s.camera_maintenance_company LIKE ?
                )""")
                params.extend([pattern] * 6)

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            limit_sql = f"LIMIT {limit} OFFSET {offset}" if limit else ""

            query = f"""
                SELECT 
                    s.*,
                    COUNT(DISTINCT a.guard_id) as assigned_guards_count,
                    GROUP_CONCAT(g.guard_name, ' | ') as guard_names_preview
                FROM schools s
                LEFT JOIN school_guard_assignments a ON s.school_id = a.school_id
                LEFT JOIN guards g ON a.guard_id = g.guard_id
                {where_sql}
                GROUP BY s.school_id
                ORDER BY s.school_id ASC
                {limit_sql};
            """
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_school_by_id(self, school_id: int) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM schools WHERE school_id = ?;", (school_id,)).fetchone()
            if not row:
                return None
            school = dict(row)
            # Fetch assigned guards
            guards = conn.execute("""
                SELECT g.*, a.address, a.assignment_id, a.created_at as assigned_at
                FROM guards g
                INNER JOIN school_guard_assignments a ON g.guard_id = a.guard_id
                WHERE a.school_id = ?
                ORDER BY g.guard_name ASC;
            """, (school_id,)).fetchall()
            school["assigned_guards"] = [dict(g) for g in guards]
            school["assigned_guards_count"] = len(guards)
            return school

    def add_school(self, data: Dict[str, Any]) -> int:
        keys = [
            "administration", "school_name", "affiliation", "manager_name",
            "manager_phone", "security_officer_name", "security_officer_phone",
            "classrooms_count", "gates_count", "fire_extinguishers_count",
            "fire_extinguisher_type", "fire_extinguisher_weight",
            "activated_fire_lines", "inactive_fire_lines", "working_cameras",
            "non_working_cameras", "camera_maintenance_company", "buckets_count",
            "valid_fire_hoses", "invalid_fire_hoses", "notes"
        ]
        values = [str(data.get(k, "") or "").strip() for k in keys]
        sql = f"INSERT INTO schools ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))});"
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            new_id = cursor.lastrowid
            conn.commit()
            self.db.log_audit("ADD", "SCHOOL", new_id, f"Added school {data.get('school_name')}")
            return int(new_id)

    def update_school(self, school_id: int, data: Dict[str, Any]) -> bool:
        keys = [
            "administration", "school_name", "affiliation", "manager_name",
            "manager_phone", "security_officer_name", "security_officer_phone",
            "classrooms_count", "gates_count", "fire_extinguishers_count",
            "fire_extinguisher_type", "fire_extinguisher_weight",
            "activated_fire_lines", "inactive_fire_lines", "working_cameras",
            "non_working_cameras", "camera_maintenance_company", "buckets_count",
            "valid_fire_hoses", "invalid_fire_hoses", "notes"
        ]
        set_clause = ", ".join(f"{k} = ?" for k in keys) + ", updated_at = CURRENT_TIMESTAMP"
        values = [str(data.get(k, "") or "").strip() for k in keys]
        values.append(school_id)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE schools SET {set_clause} WHERE school_id = ?;", values)
            conn.commit()
            success = cursor.rowcount > 0
            if success:
                self.db.log_audit("UPDATE", "SCHOOL", school_id, f"Updated school {data.get('school_name')}")
            return success

    def delete_school(self, school_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schools WHERE school_id = ?;", (school_id,))
            conn.commit()
            success = cursor.rowcount > 0
            if success:
                self.db.log_audit("DELETE", "SCHOOL", school_id, f"Deleted school {school_id}")
            return success

    def get_administrations(self) -> List[str]:
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT administration FROM schools 
                WHERE administration IS NOT NULL AND TRIM(administration) != ''
                ORDER BY administration ASC;
            """).fetchall()
            return [r["administration"] for r in rows]

    def get_affiliations(self) -> List[str]:
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT affiliation FROM schools 
                WHERE affiliation IS NOT NULL AND TRIM(affiliation) != ''
                ORDER BY affiliation ASC;
            """).fetchall()
            return [r["affiliation"] for r in rows]

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calculates live statistical metrics from actual database records."""
        with self.db.get_connection() as conn:
            # 1. Total counts
            total_schools = conn.execute("SELECT COUNT(*) FROM schools;").fetchone()[0]
            total_guards = conn.execute("SELECT COUNT(*) FROM guards;").fetchone()[0]
            total_assignments = conn.execute("SELECT COUNT(*) FROM school_guard_assignments;").fetchone()[0]
            total_admins = conn.execute("SELECT COUNT(DISTINCT administration) FROM schools WHERE administration != '';").fetchone()[0]

            # 2. Equipment aggregations
            schools_rows = conn.execute("""
                SELECT 
                    classrooms_count, gates_count, fire_extinguishers_count,
                    activated_fire_lines, inactive_fire_lines,
                    working_cameras, non_working_cameras,
                    buckets_count, valid_fire_hoses, invalid_fire_hoses,
                    security_officer_name, manager_phone, working_cameras
                FROM schools;
            """).fetchall()

            total_classrooms = 0
            total_gates = 0
            total_extinguishers = 0
            total_active_lines = 0
            total_inactive_lines = 0
            total_working_cameras = 0
            total_broken_cameras = 0
            total_buckets = 0
            total_valid_hoses = 0
            total_invalid_hoses = 0
            incomplete_schools_count = 0

            for r in schools_rows:
                def safe_int(val):
                    try:
                        clean = re.sub(r"[^\d]", "", str(val or ""))
                        return int(clean) if clean else 0
                    except Exception:
                        return 0

                total_classrooms += safe_int(r["classrooms_count"])
                total_gates += safe_int(r["gates_count"])
                total_extinguishers += safe_int(r["fire_extinguishers_count"])
                total_active_lines += safe_int(r["activated_fire_lines"])
                total_inactive_lines += safe_int(r["inactive_fire_lines"])
                total_working_cameras += safe_int(r["working_cameras"])
                total_broken_cameras += safe_int(r["non_working_cameras"])
                total_buckets += safe_int(r["buckets_count"])
                total_valid_hoses += safe_int(r["valid_fire_hoses"])
                total_invalid_hoses += safe_int(r["invalid_fire_hoses"])

                # Check incomplete security profile
                has_sec_officer = bool(str(r["security_officer_name"] or "").strip())
                has_mgr_phone = bool(str(r["manager_phone"] or "").strip())
                if not has_sec_officer or not has_mgr_phone:
                    incomplete_schools_count += 1

            # 3. Administration Breakdown
            admin_breakdown_rows = conn.execute("""
                SELECT 
                    s.administration,
                    COUNT(DISTINCT s.school_id) as schools_cnt,
                    COUNT(DISTINCT a.guard_id) as guards_cnt
                FROM schools s
                LEFT JOIN school_guard_assignments a ON s.school_id = a.school_id
                WHERE s.administration IS NOT NULL AND TRIM(s.administration) != ''
                GROUP BY s.administration
                ORDER BY schools_cnt DESC;
            """).fetchall()

            admin_breakdown = [dict(r) for r in admin_breakdown_rows]

            return {
                "total_schools": total_schools,
                "total_guards": total_guards,
                "total_assignments": total_assignments,
                "total_administrations": total_admins,
                "total_classrooms": total_classrooms,
                "total_gates": total_gates,
                "total_extinguishers": total_extinguishers,
                "total_active_lines": total_active_lines,
                "total_inactive_lines": total_inactive_lines,
                "total_working_cameras": total_working_cameras,
                "total_broken_cameras": total_broken_cameras,
                "total_buckets": total_buckets,
                "total_valid_hoses": total_valid_hoses,
                "total_invalid_hoses": total_invalid_hoses,
                "incomplete_schools_count": incomplete_schools_count,
                "admin_breakdown": admin_breakdown
            }

