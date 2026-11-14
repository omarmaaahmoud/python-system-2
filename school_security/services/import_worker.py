# -*- coding: utf-8 -*-
"""
Asynchronous QThread worker for executing Excel import transactions.
Ensures zero-freeze UI, real-time progress signals, and relational linking.
"""
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QThread, Signal

from ..database import SchoolSecurityDatabaseManager, normalize_arabic
from ..models import ImportResult
from .excel_importer import SchoolSecurityExcelImporter


class SchoolSecurityImportWorker(QThread):
    progress = Signal(int, str)
    finished_signal = Signal(object)  # Emits ImportResult
    failed_signal = Signal(str)

    def __init__(
        self,
        db_manager: SchoolSecurityDatabaseManager,
        file_path: str,
        import_mode: str = "add_and_update"  # 'add_new', 'update_existing', 'add_and_update', 'skip_duplicates'
    ):
        super().__init__()
        self.db = db_manager
        self.file_path = file_path
        self.import_mode = import_mode
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        result = ImportResult()
        try:
            self.progress.emit(10, "جاري فتح وتحليل ورقات عمل ملف الإكسيل...")
            importer = SchoolSecurityExcelImporter(self.file_path)

            if self._is_cancelled:
                return

            self.progress.emit(25, "جاري استخراج وفحص سجلات تأمين المدارس...")
            school_records = importer.parse_schools()

            self.progress.emit(40, "جاري استخراج وفحص كشوف حراس أمن الإدارات...")
            guard_records = importer.parse_guards()

            result.total_processed = len(school_records) + len(guard_records)

            if self._is_cancelled:
                return

            self.progress.emit(55, "جاري إدخال وتحديث بيانات المدارس في قاعدة البيانات...")

            # Execute transactional import
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Cache existing schools for quick linking and duplicate detection
                existing_schools_rows = cursor.execute("""
                    SELECT school_id, administration, school_name FROM schools;
                """).fetchall()

                # Mapping: (norm_admin, norm_school_name) -> school_id
                schools_map = {}
                schools_by_name = {}
                for s in existing_schools_rows:
                    sid = s["school_id"]
                    n_adm = normalize_arabic(s["administration"])
                    n_name = normalize_arabic(s["school_name"])
                    if n_name:
                        schools_map[(n_adm, n_name)] = sid
                        schools_by_name[n_name] = sid

                # 1. Process Schools
                school_keys = [
                    "administration", "school_name", "affiliation", "manager_name",
                    "manager_phone", "security_officer_name", "security_officer_phone",
                    "classrooms_count", "gates_count", "fire_extinguishers_count",
                    "fire_extinguisher_type", "fire_extinguisher_weight",
                    "activated_fire_lines", "inactive_fire_lines", "working_cameras",
                    "non_working_cameras", "camera_maintenance_company", "buckets_count",
                    "valid_fire_hoses", "invalid_fire_hoses", "notes"
                ]

                for s_rec in school_records:
                    if self._is_cancelled:
                        conn.rollback()
                        return

                    n_adm = normalize_arabic(s_rec["administration"])
                    n_name = normalize_arabic(s_rec["school_name"])
                    existing_id = schools_map.get((n_adm, n_name)) or schools_by_name.get(n_name)

                    if existing_id:
                        if self.import_mode in ("update_existing", "add_and_update"):
                            update_pairs = []
                            update_vals = []
                            for k in school_keys:
                                val = str(s_rec.get(k, "") or "").strip()
                                if val:  # only update fields with incoming data
                                    update_pairs.append(f"{k} = ?")
                                    update_vals.append(val)
                            if update_pairs:
                                update_vals.append(existing_id)
                                cursor.execute(
                                    f"UPDATE schools SET {', '.join(update_pairs)}, updated_at = CURRENT_TIMESTAMP WHERE school_id = ?;",
                                    update_vals
                                )
                                result.schools_updated += 1
                        else:
                            result.schools_skipped += 1
                    else:
                        if self.import_mode in ("add_new", "add_and_update"):
                            insert_vals = [str(s_rec.get(k, "") or "").strip() for k in school_keys]
                            cursor.execute(
                                f"INSERT INTO schools ({', '.join(school_keys)}) VALUES ({', '.join(['?'] * len(school_keys))});",
                                insert_vals
                            )
                            new_sid = cursor.lastrowid
                            schools_map[(n_adm, n_name)] = new_sid
                            schools_by_name[n_name] = new_sid
                            result.schools_inserted += 1
                        else:
                            result.schools_skipped += 1

                # 2. Process Guards and Link Assignments
                self.progress.emit(75, "جاري إدخال وتحديث حراس الأمن وربطهم بالمدارس...")

                # Cache existing guards
                existing_guards_rows = cursor.execute("""
                    SELECT guard_id, guard_name, national_id, phone FROM guards;
                """).fetchall()

                guards_by_nid = {}
                guards_by_name_phone = {}
                guards_by_name = {}

                for g in existing_guards_rows:
                    gid = g["guard_id"]
                    nid = str(g["national_id"] or "").strip()
                    phone = str(g["phone"] or "").strip()
                    n_name = normalize_arabic(g["guard_name"])

                    if nid and nid != "0" and len(nid) >= 6:
                        guards_by_nid[nid] = gid
                    if n_name and phone and len(phone) >= 7:
                        guards_by_name_phone[(n_name, phone)] = gid
                    if n_name:
                        guards_by_name[n_name] = gid

                for g_rec in guard_records:
                    if self._is_cancelled:
                        conn.rollback()
                        return

                    g_name = str(g_rec.get("guard_name", "") or "").strip()
                    n_name = normalize_arabic(g_name)
                    nid = str(g_rec.get("national_id", "") or "0").strip()
                    phone = str(g_rec.get("phone", "") or "").strip()
                    address = str(g_rec.get("address", "") or "").strip()

                    matched_gid = None
                    if nid and nid != "0" and len(nid) >= 6 and nid in guards_by_nid:
                        matched_gid = guards_by_nid[nid]
                    elif n_name and phone and (n_name, phone) in guards_by_name_phone:
                        matched_gid = guards_by_name_phone[(n_name, phone)]
                    elif n_name and n_name in guards_by_name:
                        matched_gid = guards_by_name[n_name]

                    if matched_gid:
                        if self.import_mode in ("update_existing", "add_and_update"):
                            update_pairs = ["guard_name = ?"]
                            update_vals = [g_name]
                            if nid and nid != "0":
                                update_pairs.append("national_id = ?")
                                update_vals.append(nid)
                            if phone:
                                update_pairs.append("phone = ?")
                                update_vals.append(phone)
                            update_vals.append(matched_gid)
                            cursor.execute(
                                f"UPDATE guards SET {', '.join(update_pairs)}, updated_at = CURRENT_TIMESTAMP WHERE guard_id = ?;",
                                update_vals
                            )
                            result.guards_updated += 1
                        else:
                            result.guards_skipped += 1
                        target_gid = matched_gid
                    else:
                        if self.import_mode in ("add_new", "add_and_update"):
                            cursor.execute(
                                "INSERT INTO guards (guard_name, national_id, phone, notes) VALUES (?, ?, ?, ?);",
                                (g_name, nid, phone, str(g_rec.get("notes", "") or ""))
                            )
                            target_gid = cursor.lastrowid
                            if nid and nid != "0":
                                guards_by_nid[nid] = target_gid
                            if n_name and phone:
                                guards_by_name_phone[(n_name, phone)] = target_gid
                            if n_name:
                                guards_by_name[n_name] = target_gid
                            result.guards_inserted += 1
                        else:
                            result.guards_skipped += 1
                            target_gid = None

                    # Link Guard to School Assignment
                    if target_gid:
                        sch_name = normalize_arabic(g_rec.get("school_name", ""))
                        adm_name = normalize_arabic(g_rec.get("administration", ""))

                        linked_sid = schools_map.get((adm_name, sch_name)) or schools_by_name.get(sch_name)

                        if linked_sid:
                            cursor.execute(
                                "INSERT OR REPLACE INTO school_guard_assignments (school_id, guard_id, address) VALUES (?, ?, ?);",
                                (linked_sid, target_gid, address)
                            )
                            result.assignments_created += 1
                        else:
                            result.unmatched_guards += 1

                # 3. Log into Import History
                cursor.execute("""
                    INSERT INTO import_history (
                        file_name, schools_count, guards_count, assignments_count, status, log_details
                    ) VALUES (?, ?, ?, ?, ?, ?);
                """, (
                    Path(self.file_path).name,
                    result.schools_inserted + result.schools_updated,
                    result.guards_inserted + result.guards_updated,
                    result.assignments_created,
                    "SUCCESS",
                    result.summary_message()
                ))

                conn.commit()

            self.progress.emit(100, "اكتمل الاستيراد وتحديث البيانات بنجاح!")
            self.finished_signal.emit(result)

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            self.failed_signal.emit(str(e))

