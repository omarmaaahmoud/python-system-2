# -*- coding: utf-8 -*-
"""
Reports & Analytical Summaries View for School Security Management System.
Generates specialized reports on equipment defects, guard allocations, and safety hazards.
"""
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt

from ..database import SchoolSecurityDatabaseManager
from ..services.school_service import SchoolService
from ..services.excel_exporter import SchoolSecurityExcelExporter


class ReportsView(QWidget):
    def __init__(
        self,
        db_manager: SchoolSecurityDatabaseManager,
        school_service: SchoolService,
        parent=None
    ):
        super().__init__(parent)
        self.db = db_manager
        self.school_service = school_service
        self.current_report_data: List[List[Any]] = []
        self.current_headers: List[str] = []
        self.current_report_title: str = ""

        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()
        self.generate_selected_report()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # 1. Report Selector Toolbar
        top_card = QFrame()
        top_card.setStyleSheet("background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px;")
        t_lay = QHBoxLayout(top_card)
        t_lay.setSpacing(12)

        t_lay.addWidget(QLabel("📑 نوع التقرير المطلوب:"))
        self.combo_report = QComboBox()
        self.combo_report.addItem("تقرير المدارس ذات الكاميرات المعطلة", "broken_cameras")
        self.combo_report.addItem("تقرير أعطال خطوط وخراطيم الحريق التالفة", "fire_hazards")
        self.combo_report.addItem("تقرير المدارس التي ليس بها حراس أمن مكلفين", "no_guards")
        self.combo_report.addItem("تقرير بيان حصر تجهيزات الأمان حسب الإدارات", "admin_summary")
        self.combo_report.addItem("تقرير كشف الحراس وتوزيعهم وعناوينهم", "guards_distribution")
        self.combo_report.currentIndexChanged.connect(self.generate_selected_report)
        t_lay.addWidget(self.combo_report, 2)

        t_lay.addWidget(QLabel("الإدارة التعليمية:"))
        self.combo_admin = QComboBox()
        self.combo_admin.addItem("— كل الإدارات —", "")
        for adm in self.school_service.get_administrations():
            self.combo_admin.addItem(adm, adm)
        self.combo_admin.currentIndexChanged.connect(self.generate_selected_report)
        t_lay.addWidget(self.combo_admin, 1)

        self.btn_refresh = QPushButton("تحديث التقرير")
        self.btn_refresh.setObjectName("SecondaryBtn")
        self.btn_refresh.clicked.connect(self.generate_selected_report)
        t_lay.addWidget(self.btn_refresh)

        t_lay.addStretch()

        self.btn_export = QPushButton("📤 تصدير التقرير لـ Excel")
        self.btn_export.setObjectName("PrimaryBtn")
        self.btn_export.setMinimumHeight(38)
        self.btn_export.clicked.connect(self.export_report)
        t_lay.addWidget(self.btn_export)

        layout.addWidget(top_card)

        # 2. Report Details Header
        self.lbl_title = QLabel("تقرير:")
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E3A8A;")
        layout.addWidget(self.lbl_title)

        # 3. Report Data Table
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

    def generate_selected_report(self):
        rep_type = self.combo_report.currentData()
        adm = self.combo_admin.currentData() or ""

        where_admin = f"WHERE s.administration = '{adm}'" if adm else ""

        with self.db.get_connection() as conn:
            if rep_type == "broken_cameras":
                self.current_report_title = "تقرير المدارس ذات الكاميرات المعطلة وتحتاج صيانة"
                self.current_headers = ["م", "الإدارة", "اسم المدرسة", "مدير المدرسة وهاتفه", "كاميرات معطلة", "كاميرات تعمل", "شركة الصيانة المسؤولة"]
                q = f"""
                    SELECT s.administration, s.school_name, 
                           s.manager_name || ' (' || s.manager_phone || ')',
                           s.non_working_cameras, s.working_cameras, s.camera_maintenance_company
                    FROM schools s
                    {where_admin}
                    {'AND' if where_admin else 'WHERE'} (s.non_working_cameras != '' AND s.non_working_cameras != '0' AND s.non_working_cameras != '—')
                    ORDER BY CAST(s.non_working_cameras AS INTEGER) DESC;
                """
                rows = conn.execute(q).fetchall()
                self.current_report_data = [[i+1] + list(r) for i, r in enumerate(rows)]

            elif rep_type == "fire_hazards":
                self.current_report_title = "تقرير أعطال منظومة الإطفاء وخراطيم الحريق غير الصالحة"
                self.current_headers = ["م", "الإدارة", "اسم المدرسة", "مسؤول الأمن وهاتفه", "خطوط غير مفعلة", "خراطيم غير صالحة", "إجمالي الطفايات"]
                q = f"""
                    SELECT s.administration, s.school_name,
                           s.security_officer_name || ' (' || s.security_officer_phone || ')',
                           s.inactive_fire_lines, s.invalid_fire_hoses, s.fire_extinguishers_count
                    FROM schools s
                    {where_admin}
                    {'AND' if where_admin else 'WHERE'} (
                        (s.inactive_fire_lines != '' AND s.inactive_fire_lines != '0' AND s.inactive_fire_lines != '—') OR
                        (s.invalid_fire_hoses != '' AND s.invalid_fire_hoses != '0' AND s.invalid_fire_hoses != '—')
                    )
                    ORDER BY s.administration ASC;
                """
                rows = conn.execute(q).fetchall()
                self.current_report_data = [[i+1] + list(r) for i, r in enumerate(rows)]

            elif rep_type == "no_guards":
                self.current_report_title = "تقرير المدارس التي ليس بها حراس أمن مكلفين"
                self.current_headers = ["م", "الإدارة", "اسم المدرسة", "التبعية", "مدير المدرسة", "هاتف المدير", "عدد البوابات"]
                q = f"""
                    SELECT s.administration, s.school_name, s.affiliation, s.manager_name, s.manager_phone, s.gates_count
                    FROM schools s
                    LEFT JOIN school_guard_assignments a ON s.school_id = a.school_id
                    {where_admin}
                    {'AND' if where_admin else 'WHERE'} a.guard_id IS NULL
                    ORDER BY s.administration ASC;
                """
                rows = conn.execute(q).fetchall()
                self.current_report_data = [[i+1] + list(r) for i, r in enumerate(rows)]

            elif rep_type == "admin_summary":
                self.current_report_title = "تقرير بيان حصر تجهيزات الأمان ومعدات الطوارئ حسب الإدارات"
                self.current_headers = ["م", "الإدارة التعليمية", "عدد المدارس", "عدد الحراس", "كاميرات تعمل", "كاميرات معطلة", "طفايات حريق", "خطوط مفعلة"]
                q = """
                    SELECT 
                        s.administration,
                        COUNT(DISTINCT s.school_id) as sch_cnt,
                        COUNT(DISTINCT a.guard_id) as grd_cnt,
                        SUM(CASE WHEN s.working_cameras GLOB '[0-9]*' THEN CAST(s.working_cameras AS INTEGER) ELSE 0 END),
                        SUM(CASE WHEN s.non_working_cameras GLOB '[0-9]*' THEN CAST(s.non_working_cameras AS INTEGER) ELSE 0 END),
                        SUM(CASE WHEN s.fire_extinguishers_count GLOB '[0-9]*' THEN CAST(s.fire_extinguishers_count AS INTEGER) ELSE 0 END),
                        SUM(CASE WHEN s.activated_fire_lines GLOB '[0-9]*' THEN CAST(s.activated_fire_lines AS INTEGER) ELSE 0 END)
                    FROM schools s
                    LEFT JOIN school_guard_assignments a ON s.school_id = a.school_id
                    WHERE s.administration != ''
                    GROUP BY s.administration
                    ORDER BY sch_cnt DESC;
                """
                rows = conn.execute(q).fetchall()
                self.current_report_data = [[i+1] + list(r) for i, r in enumerate(rows)]

            elif rep_type == "guards_distribution":
                self.current_report_title = "تقرير كشف حراس أمن المدارس وتوزيعهم وعناوينهم"
                self.current_headers = ["م", "اسم الحارس", "الرقم القومي", "رقم الهاتف", "المدرسة المكلف بها", "الإدارة التعليمية", "العنوان"]
                q = f"""
                    SELECT g.guard_name, g.national_id, g.phone, s.school_name, s.administration, a.address
                    FROM guards g
                    LEFT JOIN school_guard_assignments a ON g.guard_id = a.guard_id
                    LEFT JOIN schools s ON a.school_id = s.school_id
                    {where_admin.replace('s.administration', 's.administration')}
                    ORDER BY s.administration ASC, g.guard_name ASC;
                """
                rows = conn.execute(q).fetchall()
                self.current_report_data = [[i+1] + list(r) for i, r in enumerate(rows)]

        self.lbl_title.setText(f"📑 {self.current_report_title} — إجمالي السجلات: ({len(self.current_report_data):,})")
        self.render_table()

    def render_table(self):
        self.table.setColumnCount(len(self.current_headers))
        self.table.setHorizontalHeaderLabels(self.current_headers)
        self.table.setRowCount(len(self.current_report_data))

        for r_idx, row in enumerate(self.current_report_data):
            for c_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val) if val is not None else "—")
                if c_idx == 0 or (isinstance(val, (int, float))):
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r_idx, c_idx, item)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

    def export_report(self):
        if not self.current_report_data:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات لتصديرها في التقرير الحالي.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ التقرير الإحصائي",
            f"{self.current_report_title.replace(' ', '_')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "تقرير إحصائي"
            SchoolSecurityExcelExporter._apply_styles(ws, self.current_report_title, self.current_headers, self.current_report_data)
            wb.save(file_path)
            QMessageBox.information(self, "نجاح التصدير", f"تم تصدير التقرير بنجاح إلى:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر حفظ التقرير:\n{e}")

