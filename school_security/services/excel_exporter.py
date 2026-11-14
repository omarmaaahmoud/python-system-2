# -*- coding: utf-8 -*-
"""
Excel Exporter for School Security Management System.
Exports styled Arabic Excel workbooks with professional headers and formatting.
"""
from typing import List, Dict, Any
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class SchoolSecurityExcelExporter:
    @staticmethod
    def _apply_styles(ws, title: str, headers: List[str], rows: List[List[Any]]):
        ws.views.sheetView[0].rightToLeft = True

        # Header Fill & Fonts
        title_font = Font(name="Arial", size=15, bold=True, color="1E3A8A")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
        data_font = Font(name="Arial", size=10)
        alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        thin_side = Side(border_style="thin", color="CBD5E1")
        border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        right_align = Alignment(horizontal="right", vertical="center")

        # 1. Title Row
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        title_cell = ws.cell(row=1, column=1, value=title)
        title_cell.font = title_font
        title_cell.alignment = center_align
        ws.row_dimensions[1].height = 40

        # 2. Column Headers
        ws.row_dimensions[2].height = 28
        for col_idx, h_text in enumerate(headers, start=1):
            cell = ws.cell(row=2, column=col_idx, value=h_text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border

        # 3. Data Rows
        for r_idx, row_data in enumerate(rows, start=3):
            ws.row_dimensions[r_idx].height = 22
            is_alt = (r_idx % 2 == 0)
            for c_idx, val in enumerate(row_data, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val if val is not None else "—")
                cell.font = data_font
                cell.border = border
                if is_alt:
                    cell.fill = alt_fill
                if isinstance(val, (int, float)) or (isinstance(val, str) and val.isdigit()):
                    cell.alignment = center_align
                else:
                    cell.alignment = right_align

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    @classmethod
    def export_schools(cls, file_path: str, schools: List[Dict[str, Any]]):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "سجلات تأمين المدارس"

        headers = [
            "م", "الإدارة التعليمية", "اسم المدرسة", "التبعية", "مدير المدرسة",
            "تليفون المدير", "مسؤول الأمن", "تليفون مسؤول الأمن", "الفصول",
            "البوابات", "الطفايات", "نوع الطفاية", "الوزن", "خطوط مفعلة",
            "خطوط غير مفعلة", "كاميرات تعمل", "كاميرات معطلة", "شركة الصيانة",
            "الجرادل", "خراطيم صالحة", "خراطيم غير صالحة", "عدد الحراس المكلفين"
        ]

        rows = []
        for idx, s in enumerate(schools, start=1):
            rows.append([
                idx,
                s.get("administration", ""),
                s.get("school_name", ""),
                s.get("affiliation", ""),
                s.get("manager_name", ""),
                s.get("manager_phone", ""),
                s.get("security_officer_name", ""),
                s.get("security_officer_phone", ""),
                s.get("classrooms_count", ""),
                s.get("gates_count", ""),
                s.get("fire_extinguishers_count", ""),
                s.get("fire_extinguisher_type", ""),
                s.get("fire_extinguisher_weight", ""),
                s.get("activated_fire_lines", ""),
                s.get("inactive_fire_lines", ""),
                s.get("working_cameras", ""),
                s.get("non_working_cameras", ""),
                s.get("camera_maintenance_company", ""),
                s.get("buckets_count", ""),
                s.get("valid_fire_hoses", ""),
                s.get("invalid_fire_hoses", ""),
                s.get("assigned_guards_count", 0)
            ])

        cls._apply_styles(ws, "كشف بيانات تأمين المدارس — مديرية التربية والتعليم بالإسكندرية", headers, rows)
        wb.save(file_path)

    @classmethod
    def export_guards(cls, file_path: str, guards: List[Dict[str, Any]]):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "حراس أمن المدارس"

        headers = [
            "م", "اسم الحارس", "الرقم القومي", "رقم الهاتف",
            "المدرسة المكلف بها", "الإدارة التعليمية", "عنوان المدرسة", "ملاحظات"
        ]

        rows = []
        for idx, g in enumerate(guards, start=1):
            rows.append([
                idx,
                g.get("guard_name", ""),
                g.get("national_id", ""),
                g.get("phone", ""),
                g.get("school_name", "—"),
                g.get("administration", "—"),
                g.get("address", "—"),
                g.get("notes", "")
            ])

        cls._apply_styles(ws, "بيان حراس أمن المدارس وتوزيعهم — مديرية التربية والتعليم", headers, rows)
        wb.save(file_path)

