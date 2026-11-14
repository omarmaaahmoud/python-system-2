# -*- coding: utf-8 -*-
"""
Smart Excel Importer for School Security Management System.
Features:
- Dynamic worksheet discovery
- Flexible Arabic column name mapping
- Cleans and normalizes Arabic text
- Preserves leading zeros in National IDs and phone numbers (as TEXT)
- Detects conflicts and maps guards to schools
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import openpyxl

from ..database import normalize_arabic
from ..models import ImportResult


# Flexible Arabic Synonyms for School Sheet Columns
SCHOOL_COLUMN_SYNONYMS = {
    "administration": ["الإدارة", "الادارة", "الادارة التعليمية", "الإدارة التعليمية", "اسم الادارة", "اسم الإدارة"],
    "school_name": ["اسم المدرسة", "المدرسة", "اسم المدرسه", "المدرسه"],
    "affiliation": ["التبعية", "نوع التبعية", "نوع المدرسة", "التبعيه"],
    "manager_name": ["اسم مدير المدرسة", "مدير المدرسة", "اسم المدير", "المدير", "مدير المدرسه"],
    "manager_phone": ["التليفون", "تليفون المدير", "رقم المدير", "هاتف المدير", "موبايل المدير"],
    "security_officer_name": ["اسم مسئول الأمن", "اسم مسؤول الأمن", "مسئول الأمن", "مسؤول الأمن", "مسئول الامن", "مسؤول الامن"],
    "security_officer_phone": ["التليفون مسئول الامن", "تليفون مسئول الامن", "هاتف مسئول الامن", "تليفون مسؤول الأمن", "هاتف مسؤول الأمن"],
    "classrooms_count": ["عدد الفصول", "الفصول"],
    "gates_count": ["عدد البوابات", "البوابات"],
    "fire_extinguishers_count": ["عدد الطفايات", "الطفايات"],
    "fire_extinguisher_type": ["نوع الطفاية", "نوع الطفايه"],
    "fire_extinguisher_weight": ["وزن الطفاية", "وزن الطفايه", "الوزن"],
    "activated_fire_lines": ["عددخط الحريق المفعل", "عدد خط الحريق المفعل", "خطوط مفعلة", "خطوط مفعله"],
    "inactive_fire_lines": ["عدد خط الحريق غير مفعل", "عدد خط الحريق غير المفعل", "خطوط غير مفعلة", "خطوط غير مفعله"],
    "working_cameras": ["عدد الكاميرات التى تعمل", "عدد الكاميرات التي تعمل", "كاميرات تعمل"],
    "non_working_cameras": ["عدد الكاميرات التى لا تعمل", "عدد الكاميرات التي لا تعمل", "كاميرات معطلة", "كاميرات لا تعمل"],
    "camera_maintenance_company": ["اسم شركة صيانة الكاميرات", "شركة الصيانة", "شركه الصيانه", "صيانة الكاميرات"],
    "buckets_count": ["عدد الجرادل", "الجرادل"],
    "valid_fire_hoses": ["عدد خراطيم الحريق الصالحة", "خراطيم صالحة", "خراطيم صالحه"],
    "invalid_fire_hoses": ["عدد خراطيم الحريق الغير صالحة", "خراطيم غير صالحة", "خراطيم غير صالحه", "خراطيم تالفة"],
}

# Flexible Arabic Synonyms for Guard Sheet Columns
GUARD_COLUMN_SYNONYMS = {
    "administration": ["الإدارة", "الادارة", "الادارة التعليمية", "الإدارة التعليمية"],
    "school_name": ["المدرسة", "اسم المدرسة", "المدرسه", "اسم المدرسه"],
    "address": ["العنوان", "عنوان المدرسة", "عنوان المدرسه"],
    "guard_name": ["اسم الحارس", "اسم عمال الحراسة", "اسم العامل", "الحارس", "اسم حارس الأمن"],
    "phone": ["رقم الهاتف", "الهاتف", "التليفون", "رقم التليفون", "موبايل"],
    "national_id": ["الرقم القومي", "الرقم القومى", "بطاقة الرقم القومي"],
}


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
    """Formats phone numbers or national IDs as pure digit string."""
    s = clean_cell_text(val)
    if not s:
        return ""
    # Remove decimal points if float
    if "." in s:
        s = s.split(".")[0]
    return s.strip()


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

        # Fallback if names didn't match keywords
        if not self.schools_sheet_name and len(self.workbook.sheetnames) > 0:
            self.schools_sheet_name = self.workbook.sheetnames[0]
        if not self.guards_sheet_name and len(self.workbook.sheetnames) > 1:
            self.guards_sheet_name = self.workbook.sheetnames[1]

    def _find_header_row(self, ws, synonyms: Dict[str, List[str]]) -> Tuple[int, Dict[int, str]]:
        """Finds the row index that contains the column headers and builds index-to-key map."""
        max_scan = min(15, ws.max_row)
        best_row_idx = 1
        best_mapping: Dict[int, str] = {}
        max_matches = 0

        for r_idx, row in enumerate(ws.iter_rows(max_row=max_scan, values_only=True), start=1):
            current_mapping = {}
            matches_count = 0
            for col_idx, cell in enumerate(row):
                cell_text = clean_cell_text(cell)
                if not cell_text:
                    continue
                cell_norm = normalize_arabic(cell_text)

                for target_key, syn_list in synonyms.items():
                    for syn in syn_list:
                        if normalize_arabic(syn) in cell_norm or cell_norm in normalize_arabic(syn):
                            current_mapping[col_idx] = target_key
                            matches_count += 1
                            break
                    if col_idx in current_mapping:
                        break

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
        header_row, col_map = self._find_header_row(ws, SCHOOL_COLUMN_SYNONYMS)

        records = []
        rows = list(ws.iter_rows(min_row=header_row + 1, values_only=True))

        for row_idx, row in enumerate(rows, start=header_row + 1):
            # Check if row is empty or serial-only
            non_empty_cells = [c for i, c in enumerate(row) if clean_cell_text(c)]
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
                    record[key] = val

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
        header_row, col_map = self._find_header_row(ws, GUARD_COLUMN_SYNONYMS)

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
                    record[key] = val

            # Ignore rows with no guard name and no school name
            if not record["guard_name"] and not record["school_name"]:
                continue

            records.append(record)

        return records

