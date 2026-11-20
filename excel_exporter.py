import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from typing import List, Dict, Any, Optional

def export_records_to_excel(
    file_path: str,
    title: str,
    records: List[Dict[str, Any]],
    columns_config: List[tuple[str, str, int]] # (data_key, header_title, min_width)
) -> bool:
    """Exports dataset to a beautifully formatted, executive Arabic RTL Excel file.
    Features:
    - Native Arabic Right-To-Left (RTL) worksheet
    - Alexandria Educational Directorate Header Banner
    - Formatted National ID as explicit text (prevents scientific notation like 2.87E+13)
    - Auto-fitted column widths with clean padding
    - Alternating row zebra striping
    - Header freeze pane
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:30]

    # 1. Enable Right-To-Left (RTL)
    ws.views.sheetView[0].rightToLeft = True

    # Styles
    font_main = Font(name="Segoe UI", size=11)
    font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    font_title = Font(name="Segoe UI", size=14, bold=True, color="1E3A8A")
    font_meta = Font(name="Segoe UI", size=9, color="64748B", italic=True)

    fill_header = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=False)
    align_right = Alignment(horizontal="right", vertical="center", wrap_text=False)

    num_cols = len(columns_config)

    # 2. Title Banner (Rows 1-3)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    cell_top = ws.cell(row=1, column=1)
    cell_top.value = "جمهورية مصر العربية - محافظة الإسكندرية - مديرية التربية والتعليم"
    cell_top.font = Font(name="Segoe UI", size=10, bold=True, color="0284C7")
    cell_top.alignment = align_center

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    cell_title = ws.cell(row=2, column=1)
    cell_title.value = title
    cell_title.font = font_title
    cell_title.alignment = align_center

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=num_cols)
    cell_meta = ws.cell(row=3, column=1)
    cell_meta.value = f"تاريخ الاستخراج: {datetime.now().strftime('%Y-%m-%d %H:%M')} | إجمالي السجلات: {len(records):,}"
    cell_meta.font = font_meta
    cell_meta.alignment = align_center

    ws.row_dimensions[1].height = 20
    ws.row_dimensions[2].height = 28
    ws.row_dimensions[3].height = 18
    ws.row_dimensions[4].height = 8 # Spacing

    # 3. Column Headers (Row 5)
    header_row = 5
    ws.row_dimensions[header_row].height = 28

    for col_idx, (_, header_name, _) in enumerate(columns_config, start=1):
        c = ws.cell(row=header_row, column=col_idx)
        c.value = header_name
        c.font = font_header
        c.fill = fill_header
        c.alignment = align_center
        c.border = thin_border

    # 4. Data Rows (Row 6 onwards)
    current_row = 6
    for idx, rec in enumerate(records, start=1):
        ws.row_dimensions[current_row].height = 22
        is_even = (idx % 2 == 0)
        row_fill = fill_zebra if is_even else fill_white

        for col_idx, (key, _, _) in enumerate(columns_config, start=1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.border = thin_border
            cell.fill = row_fill
            cell.font = font_main

            if key == "serial" or key == "index":
                # Serial number (use record_number if available, else sequential)
                rec_num = rec.get("record_number")
                cell.value = int(rec_num) if rec_num else idx
                cell.alignment = align_center
                cell.number_format = "0"
            elif key == "national_id":
                val = str(rec.get("national_id") or "").strip()
                if not val or "مؤقت" in val or val in ["None", "nan", "—"]:
                    val = "0"
                cell.value = val
                cell.alignment = align_center
                cell.number_format = "@" # Text format to prevent scientific notation
            else:
                val = rec.get(key)
                if val is None or val == "" or str(val).strip() in ["0", "0.0", "nan", "NaN", "None"]:
                    cell.value = "—"
                    cell.alignment = align_center
                else:
                    cell.value = str(val).strip()
                    # Align dates and numbers in center, text right
                    if any(term in key for term in ["date", "phone", "number", "id"]):
                        cell.alignment = align_center
                    else:
                        cell.alignment = align_right

        current_row += 1

    # 5. Auto-fit Column Widths with Minimums
    for col_idx, (key, header_name, min_w) in enumerate(columns_config, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = len(header_name)
        for r in range(6, min(current_row, 100)): # Check first 100 rows for speed
            val_str = str(ws.cell(row=r, column=col_idx).value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        calc_width = max(max_len + 3, min_w)
        ws.column_dimensions[col_letter].width = min(calc_width, 35)

    # 6. Freeze Panes at row 6
    ws.freeze_panes = "A6"

    wb.save(file_path)
    return True
