# -*- coding: utf-8 -*-
"""
Smart Excel Importer for School Security Management System.
Features:
- Dynamic worksheet discovery
- Intelligent rule-based Arabic column name mapping
- Cleans and normalizes Arabic text and administrations
- Preserves leading zeros in National IDs and phone numbers (as TEXT)
- Detects conflicts and maps guards to schools
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import openpyxl

from ..database import normalize_arabic
from ..models import ImportResult


def clean_cell_text(val: Any) -> str:
    """Cleans Excel cell value into normalized string, preserving leading zeros."""
    if val is None:
        return ""
    if isinstance(val, float):
        if val.is_integer():
            return str(int(val)).strip()
    s = str(val).strip()
    if s.lower() in ("none", "nan", "null"):
        return ""
    return s


def normalize_numeric_string(val: Any) -> str:
    """Formats phone numbers or national IDs as pure digit string with leading zero intact."""
    s = clean_cell_text(val)
    if not s:
        return ""
    if "." in s:
        s = s.split(".")[0]
    digits = re.sub(r"[^\d]", "", s).strip()
    if digits.startswith("1") and len(digits) == 10:
        digits = "0" + digits
    return digits


def normalize_admin_name(raw: str) -> str:
    """Standardizes administration names to official directorate names."""
    if not raw:
        return ""
    n = normalize_arabic(raw).strip()
    if "متزه" in n or "منتزه" in n:
        if any(w in n for w in ("ثان", "تان", "2", "تاني")):
            return "إدارة المنتزه ثان"
        if any(w in n for w in ("اول", "1")):
            return "إدارة المنتزه أول"
        return "إدارة المنتزه"
    if "شرق" in n:
        return "إدارة شرق التعليمية"
    if "وسط" in n:
        return "إدارة وسط التعليمية"
    if "غرب" in n:
        return "إدارة غرب التعليمية"
    if "جمرك" in n:
        return "إدارة الجمرك التعليمية"
    if "عجمي" in n or "عجمى" in n:
        return "إدارة العجمي التعليمية"
    if "عامري" in n:
        return "إدارة العامرية التعليمية"
    if "برج" in n:
        return "إدارة برج العرب التعليمية"
    if "ديوان" in n or "مديري" in n:
        return "ديوان عام المديرية"
    return str(raw).strip()


def match_school_column(header_text: str) -> str:
    """Accurately maps header text for the schools sheet."""
    if not header_text:
        return ""
    h = normalize_arabic(header_text).strip()
    if h in ("م", "م.", "مسلسل", "الرقم", "رقم"):
        return "serial"

    # Specific compound terms first
    if "مدير" in h and any(p in h for p in ("تليفون", "هاتف", "موبايل", "رقم")):
        return "manager_phone"
    if "مدير" in h:
        return "manager_name"
    if ("مسئول" in h or "مسؤول" in h or "امن" in h or "أمن" in h) and any(p in h for p in ("تليفون", "هاتف", "موبايل", "رقم")):
        return "security_officer_phone"
    if "مسئول" in h or "مسؤول" in h:
        return "security_officer_name"

    # Generic phone/telephone (will be contextually resolved in _find_header_row)
    if any(p in h for p in ("تليفون", "هاتف", "موبايل", "جوال")):
        return "generic_phone"

    # Cameras
    if any(w in h for w in ("كاميرات تعمل", "الكاميرات التي تعمل", "الكاميرات التى تعمل")) and "لا" not in h:
        return "working_cameras"
    if any(w in h for w in ("لا تعمل", "معطلة", "معطله", "غير تعمل")):
        return "non_working_cameras"
    if any(w in h for w in ("صيانه", "شركه", "شركة")):
        return "camera_maintenance_company"

    # Fire Lines
    if "مفعل" in h and "غير" not in h and "لا" not in h:
        return "activated_fire_lines"
    if "غير مفعل" in h or "غير مفعله" in h or "معطل" in h:
        return "inactive_fire_lines"

    # Fire Hoses
    if "خراطيم" in h and ("غير" in h or "تالف" in h or "معطل" in h):
        return "invalid_fire_hoses"
    if "خراطيم" in h:
        return "valid_fire_hoses"

    # Buckets
    if "جرادل" in h or "جردل" in h:
        return "buckets_count"

    # Extinguishers
    if "طفايه" in h or "طفايات" in h:
        if "نوع" in h:
            return "fire_extinguisher_type"
        if "وزن" in h:
            return "fire_extinguisher_weight"
        return "fire_extinguishers_count"

    # Basic School Info
    if "فصول" in h:
        return "classrooms_count"
    if "بوابات" in h:
        return "gates_count"
    if "تبعيه" in h or "نوع المدرسه" in h or "حكومي" in h or "خاص" in h:
        return "affiliation"
    if "مدرسه" in h and "مدير" not in h and "مسئول" not in h:
        return "school_name"
    if "اداره" in h or "إدارة" in h or "متزه" in h or "منتزه" in h:
        return "administration"

    return ""


def match_guard_column(header_text: str) -> str:
    """Accurately maps header text for the guards sheet."""
    if not header_text:
        return ""
    h = normalize_arabic(header_text).strip()
    if h in ("م", "م.", "مسلسل", "الرقم", "رقم"):
        return "serial"

    if any(w in h for w in ("قومي", "قومى", "بطاقه")):
        return "national_id"
    if any(w in h for w in ("هاتف", "تليفون", "موبايل", "جوال")):
        return "phone"
    if any(w in h for w in ("عنوان", "مقر", "مكان")):
        return "address"
    if "مدرسه" in h:
        return "school_name"
    if "اداره" in h or "إدارة" in h or "متزه" in h or "منتزه" in h:
        return "administration"
    if any(w in h for w in ("حارس", "عمال", "فرد", "عامل", "اسم", "الاسم")):
        return "guard_name"

    return ""


class SchoolSecurityExcelImporter:
    """Parses and validates the School Security Excel workbook."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.workbook = openpyxl.load_workbook(file_path, data_only=True)
        self.schools_sheet_name: Optional[str] = None
        self.guards_sheet_name: Optional[str] = None
        self._detect_sheets()

    def _detect_sheets(self):
        """Dynamically identifies the school and guard sheets."""
        for sheet_name in self.workbook.sheetnames:
            normalized = normalize_arabic(sheet_name)
            if "تامين" in normalized or "مدارس" in normalized:
                self.schools_sheet_name = sheet_name
            elif "حراس" in normalized or "حراسه" in normalized or "عمال" in normalized:
                self.guards_sheet_name = sheet_name

        if not self.schools_sheet_name and len(self.workbook.sheetnames) > 0:
            self.schools_sheet_name = self.workbook.sheetnames[0]
        if not self.guards_sheet_name and len(self.workbook.sheetnames) > 1:
            self.guards_sheet_name = self.workbook.sheetnames[1]

    def _find_header_row(self, ws, sheet_type: str = "school") -> Tuple[int, Dict[int, str]]:
        """Finds the row index that contains the column headers and builds index-to-key map."""
        max_scan = min(15, ws.max_row)
        best_row_idx = 1
        best_mapping: Dict[int, str] = {}
        max_matches = 0

        matcher = match_school_column if sheet_type == "school" else match_guard_column

        for r_idx, row in enumerate(ws.iter_rows(max_row=max_scan, values_only=True), start=1):
            current_mapping = {}
            matches_count = 0
            seen_manager_name = False
            seen_manager_phone = False
            seen_sec_officer = False

            for col_idx, cell in enumerate(row):
                cell_text = clean_cell_text(cell)
                if not cell_text:
                    continue
                matched_key = matcher(cell_text)
                if not matched_key or matched_key == "serial":
                    continue

                if sheet_type == "school":
                    if matched_key == "manager_name":
                        if seen_manager_name:
                            continue
                        seen_manager_name = True
                    elif matched_key == "manager_phone":
                        seen_manager_phone = True
                    elif matched_key == "security_officer_name":
                        if seen_sec_officer:
                            continue
                        seen_sec_officer = True
                    elif matched_key == "security_officer_phone":
                        pass
                    elif matched_key == "generic_phone":
                        # Disambiguate generic phone: if manager phone already seen or sec officer seen
                        if seen_sec_officer or seen_manager_phone:
                            matched_key = "security_officer_phone"
                        else:
                            matched_key = "manager_phone"
                            seen_manager_phone = True

                current_mapping[col_idx] = matched_key
                matches_count += 1

            if matches_count > max_matches:
                max_matches = matches_count
                best_row_idx = r_idx
                best_mapping = current_mapping

        return best_row_idx, best_mapping

    def parse_schools(self) -> List[Dict[str, Any]]:
        """Extracts and validates school records from the schools sheet."""
        if not self.schools_sheet_name:
            return []

        ws = self.workbook[self.schools_sheet_name]
        header_row, col_map = self._find_header_row(ws, sheet_type="school")

        records = []
        rows = list(ws.iter_rows(min_row=header_row + 1, values_only=True))

        for row_idx, row in enumerate(rows, start=header_row + 1):
            non_empty_cells = [c for c in row if clean_cell_text(c)]
            if not non_empty_cells:
                continue

            record = {
                "excel_row": row_idx,
                "administration": "",
                "school_name": "",
                "affiliation": "",
                "manager_name": "",
                "manager_phone": "",
                "security_officer_name": "",
                "security_officer_phone": "",
                "classrooms_count": "",
                "gates_count": "",
                "fire_extinguishers_count": "",
                "fire_extinguisher_type": "",
                "fire_extinguisher_weight": "",
                "activated_fire_lines": "",
                "inactive_fire_lines": "",
                "working_cameras": "",
                "non_working_cameras": "",
                "camera_maintenance_company": "",
                "buckets_count": "",
                "valid_fire_hoses": "",
                "invalid_fire_hoses": "",
                "notes": ""
            }

            for col_idx, cell in enumerate(row):
                if col_idx in col_map:
                    key = col_map[col_idx]
                    val = clean_cell_text(cell)
                    if "phone" in key:
                        val = normalize_numeric_string(cell)
                    if val or not record.get(key):
                        record[key] = val

            # Normalize administration name
            if record["administration"]:
                record["administration"] = normalize_admin_name(record["administration"])

            # Ignore rows that have no school name and no administration
            if not record["school_name"] and not record["administration"]:
                continue

            records.append(record)

        return records

    def parse_guards(self) -> List[Dict[str, Any]]:
        """Extracts and validates guard records from the guards sheet."""
        if not self.guards_sheet_name:
            return []

        ws = self.workbook[self.guards_sheet_name]
        header_row, col_map = self._find_header_row(ws, sheet_type="guard")

        records = []
        rows = list(ws.iter_rows(min_row=header_row + 1, values_only=True))

        for row_idx, row in enumerate(rows, start=header_row + 1):
            non_empty_cells = [c for c in row if clean_cell_text(c)]
            if not non_empty_cells:
                continue

            record = {
                "excel_row": row_idx,
                "administration": "",
                "school_name": "",
                "address": "",
                "guard_name": "",
                "phone": "",
                "national_id": "",
                "notes": ""
            }

            for col_idx, cell in enumerate(row):
                if col_idx in col_map:
                    key = col_map[col_idx]
                    val = clean_cell_text(cell)
                    if key in ("phone", "national_id"):
                        val = normalize_numeric_string(cell)
                    if val or not record.get(key):
                        record[key] = val

            # Normalize administration name
            if record["administration"]:
                record["administration"] = normalize_admin_name(record["administration"])

            # Ignore placeholder guard names like "لا يوجد" or "بدون"
            norm_gname = normalize_arabic(record["guard_name"]).strip()
            if norm_gname in ("لا يوجد", "لايوجد", "لاشيء", "لا شيء", "بدون", "لا توجد", "—", "-", "لا"):
                record["guard_name"] = ""

            if not record["guard_name"]:
                continue

            records.append(record)

        return records
