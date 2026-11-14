# -*- coding: utf-8 -*-
"""
Asynchronous QThread worker for executing Excel import transactions.
Ensures zero-freeze UI, real-time progress signals, and relational linking.
Supports single-file or multi-file bulk imports seamlessly.
"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
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
        file_paths: Union[str, List[str]],
        import_mode: str = "add_and_update"  # 'add_new', 'update_existing', 'add_and_update', 'skip_duplicates'
    ):
        super().__init__()
        self.db = db_manager
        if isinstance(file_paths, (str, Path)):
            self.file_paths = [str(file_paths)]
        else:
            self.file_paths = [str(f) for f in file_paths if f]
        self.file_path = self.file_paths[0] if self.file_paths else ""
        self.import_mode = import_mode
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        result = ImportResult()
        if not self.file_paths:
            self.failed_signal.emit("لم يتم تحديد أي ملفات صالحة للاستيراد.")
            return

        total_files = len(self.file_paths)

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Cache existing schools for quick linking and duplicate detection
                existing_schools_rows = cursor.execute("""
                    SELECT school_id, administration, school_name, manager_phone, security_officer_phone FROM schools;
                """).fetchall()

                schools_list: List[Dict[str, Any]] = []
                for s in existing_schools_rows:
                    schools_list.append({
                        "school_id": s["school_id"],
                        "admin_norm": normalize_arabic(s["administration"]),
                        "school_norm": normalize_arabic(s["school_name"]),
                        "mgr_phone": re.sub(r"[^\d]", "", str(s["manager_phone"] or "")),
                        "sec_phone": re.sub(r"[^\d]", "", str(s["security_officer_phone"] or ""))
                    })

                # 1. School keys
                school_keys = [
                    "administration", "school_name", "affiliation", "manager_name",
                    "manager_phone", "security_officer_name", "security_officer_phone",
                    "classrooms_count", "gates_count", "fire_extinguishers_count",
                    "fire_extinguisher_type", "fire_extinguisher_weight",
                    "activated_fire_lines", "inactive_fire_lines", "working_cameras",
                    "non_working_cameras", "camera_maintenance_company", "buckets_count",
                    "valid_fire_hoses", "invalid_fire_hoses", "notes"
                ]

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
                    phone = re.sub(r"[^\d]", "", str(g["phone"] or ""))
                    n_name = normalize_arabic(g["guard_name"])

                    if nid and nid != "0" and len(nid) >= 6:
                        guards_by_nid[nid] = gid
                    if n_name and phone and len(phone) >= 7:
                        guards_by_name_phone[(n_name, phone)] = gid
                    if n_name:
                        guards_by_name[n_name] = gid

                def find_school_for_guard(g_adm: str, g_sch: str, g_phone: str) -> Optional[int]:
                    g_adm_norm = normalize_arabic(g_adm)
                    g_sch_norm = normalize_arabic(g_sch)
                    g_phone_clean = re.sub(r"[^\d]", "", str(g_phone or ""))

                    # Pass 1: Exact admin and school
                    for s in schools_list:
                        if s["admin_norm"] == g_adm_norm and s["school_norm"] == g_sch_norm:
                            return s["school_id"]

                    # Pass 2: Token overlap in same admin
                    g_tokens = set(g_sch_norm.split())
                    if g_tokens:
                        for s in schools_list:
                            if s["admin_norm"] == g_adm_norm:
                                s_tokens = set(s["school_norm"].split())
                                if (g_tokens & s_tokens) or (g_sch_norm and g_sch_norm in s["school_norm"]) or (s["school_norm"] and s["school_norm"] in g_sch_norm):
                                    return s["school_id"]

                    # Pass 3: Phone match with security officer or manager
                    if g_phone_clean and len(g_phone_clean) >= 7:
                        for s in schools_list:
                            if (s["sec_phone"] and g_phone_clean in s["sec_phone"]) or (s["mgr_phone"] and g_phone_clean in s["mgr_phone"]):
                                return s["school_id"]

                    # Pass 4: Single school in administration fallback
                    same_admin = [s for s in schools_list if s["admin_norm"] == g_adm_norm]
                    if len(same_admin) == 1:
                        return same_admin[0]["school_id"]

                    # Pass 5: Cross-admin name match
                    if g_sch_norm and len(g_sch_norm) >= 3:
                        for s in schools_list:
                            if s["school_norm"] == g_sch_norm or (len(g_sch_norm) >= 4 and g_sch_norm in s["school_norm"]):
                                return s["school_id"]

                    return None

                for file_idx, f_path in enumerate(self.file_paths):
                    if self._is_cancelled:
                        conn.rollback()
                        return

                    file_name = Path(f_path).name
                    pct_file_start = int((file_idx / total_files) * 90)
                    pct_file_mid = int(((file_idx + 0.5) / total_files) * 90)
                    pct_file_end = int(((file_idx + 1) / total_files) * 90)

                    self.progress.emit(
                        pct_file_start + 1,
                        f"[{file_idx + 1}/{total_files}] جاري فحص ملف: {file_name}..."
                    )

                    try:
                        importer = SchoolSecurityExcelImporter(f_path)
                        school_records = importer.parse_schools()
                        guard_records = importer.parse_guards()
                    except Exception as parse_err:
                        err_str = f"الملف «{file_name}»: تعذر قراءته ({parse_err})"
                        result.errors.append(err_str)
                        continue

                    file_processed = len(school_records) + len(guard_records)
                    result.total_processed += file_processed

                    f_schools_inserted = 0
                    f_schools_updated = 0
                    f_guards_inserted = 0
                    f_guards_updated = 0
                    f_assignments = 0

                    self.progress.emit(
                        pct_file_mid,
                        f"[{file_idx + 1}/{total_files}] جاري حفظ بيانات: {file_name} ({len(school_records)} مدرسة، {len(guard_records)} حارس)..."
                    )

                    # 1. Process Schools
                    for s_rec in school_records:
                        if self._is_cancelled:
                            conn.rollback()
                            return

                        n_adm = normalize_arabic(s_rec["administration"])
                        n_name = normalize_arabic(s_rec["school_name"])

                        # Match existing school
                        existing_id = None
                        for s_item in schools_list:
                            if s_item["admin_norm"] == n_adm and s_item["school_norm"] == n_name:
                                existing_id = s_item["school_id"]
                                break
                        if not existing_id:
                            for s_item in schools_list:
                                if s_item["school_norm"] == n_name and n_name:
                                    existing_id = s_item["school_id"]
                                    break

                        if existing_id:
                            if self.import_mode in ("update_existing", "add_and_update"):
                                update_pairs = []
                                update_vals = []
                                for k in school_keys:
                                    val = str(s_rec.get(k, "") or "").strip()
                                    if val:
                                        update_pairs.append(f"{k} = ?")
                                        update_vals.append(val)
                                if update_pairs:
                                    update_vals.append(existing_id)
                                    cursor.execute(
                                        f"UPDATE schools SET {', '.join(update_pairs)}, updated_at = CURRENT_TIMESTAMP WHERE school_id = ?;",
                                        update_vals
                                    )
                                    result.schools_updated += 1
                                    f_schools_updated += 1
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
                                schools_list.append({
                                    "school_id": new_sid,
                                    "admin_norm": n_adm,
                                    "school_norm": n_name,
                                    "mgr_phone": re.sub(r"[^\d]", "", str(s_rec.get("manager_phone", "") or "")),
                                    "sec_phone": re.sub(r"[^\d]", "", str(s_rec.get("security_officer_phone", "") or ""))
                                })
                                result.schools_inserted += 1
                                f_schools_inserted += 1
                            else:
                                result.schools_skipped += 1

                    # 2. Process Guards and Link Assignments
                    for g_rec in guard_records:
                        if self._is_cancelled:
                            conn.rollback()
                            return

                        g_name = str(g_rec.get("guard_name", "") or "").strip()
                        n_name = normalize_arabic(g_name)
                        nid = str(g_rec.get("national_id", "") or "0").strip()
                        phone = str(g_rec.get("phone", "") or "").strip()
                        phone_clean = re.sub(r"[^\d]", "", phone)
                        address = str(g_rec.get("address", "") or "").strip()

                        matched_gid = None
                        if nid and nid != "0" and len(nid) >= 6 and nid in guards_by_nid:
                            matched_gid = guards_by_nid[nid]
                        elif n_name and phone_clean and (n_name, phone_clean) in guards_by_name_phone:
                            matched_gid = guards_by_name_phone[(n_name, phone_clean)]
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
                                f_guards_updated += 1
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
                                if n_name and phone_clean:
                                    guards_by_name_phone[(n_name, phone_clean)] = target_gid
                                if n_name:
                                    guards_by_name[n_name] = target_gid
                                result.guards_inserted += 1
                                f_guards_inserted += 1
                            else:
                                result.guards_skipped += 1
                                target_gid = None

                        # Link Guard to School Assignment
                        if target_gid:
                            linked_sid = find_school_for_guard(
                                g_rec.get("administration", ""),
                                g_rec.get("school_name", ""),
                                phone
                            )

                            if linked_sid:
                                cursor.execute(
                                    "INSERT OR REPLACE INTO school_guard_assignments (school_id, guard_id, address) VALUES (?, ?, ?);",
                                    (linked_sid, target_gid, address)
                                )
                                result.assignments_created += 1
                                f_assignments += 1
                            else:
                                result.unmatched_guards += 1

                    # Log import history for this specific file
                    cursor.execute("""
                        INSERT INTO import_history (
                            file_name, schools_count, guards_count, assignments_count, status, log_details
                        ) VALUES (?, ?, ?, ?, ?, ?);
                    """, (
                        file_name,
                        f_schools_inserted + f_schools_updated,
                        f_guards_inserted + f_guards_updated,
                        f_assignments,
                        "SUCCESS",
                        f"تم بنجاح (مدارس: {f_schools_inserted} جديد، {f_schools_updated} محدث | حراس: {f_guards_inserted} جديد، {f_guards_updated} محدث)"
                    ))
                    conn.commit()

                    self.progress.emit(
                        pct_file_end,
                        f"[{file_idx + 1}/{total_files}] تم حفظ: {file_name}"
                    )

                result.success = True
                self.progress.emit(100, f"اكتمل استيراد ومعالجة كافة الملفات ({total_files} ملف) بنجاح تام!")
                self.finished_signal.emit(result)

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            self.failed_signal.emit(str(e))
