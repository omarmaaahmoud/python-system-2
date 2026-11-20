# -*- coding: utf-8 -*-
"""
Advanced Unified Search View for School Security Management System.
Allows cross-searching across schools, managers, security officers, and guards.
"""
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal

from ..database import SchoolSecurityDatabaseManager, normalize_arabic
from ..services.school_service import SchoolService
from ..services.excel_exporter import SchoolSecurityExcelExporter


class AdvancedSearchView(QWidget):
    open_school_requested = Signal(int)

    def __init__(
        self,
        db_manager: SchoolSecurityDatabaseManager,
        school_service: SchoolService,
        parent=None
    ):
        super().__init__(parent)
        self.db = db_manager
        self.school_service = school_service
        self.current_results: List[Dict[str, Any]] = []

        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # 1. Search Criteria Card
        search_card = QFrame()
        search_card.setObjectName("SearchCard")
        search_card.setStyleSheet("""
            QFrame#SearchCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        g_lay = QGridLayout(search_card)
        g_lay.setSpacing(10)

        title = QLabel("🔍 محرك البحث الشامل والمتقدم في منظومة تأمين المدارس")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E3A8A;")
        g_lay.addWidget(title, 0, 0, 1, 4)

        g_lay.addWidget(QLabel("اسم المدرسة / الكلمة المفتاحية:"), 1, 0)
        self.txt_school = QLineEdit()
        self.txt_school.setPlaceholderText("اكتب جزءاً من اسم المدرسة...")
        g_lay.addWidget(self.txt_school, 1, 1)

        g_lay.addWidget(QLabel("الإدارة التعليمية:"), 1, 2)
        self.combo_admin = QComboBox()
        self.combo_admin.addItem("— كل الإدارات —", "")
        for adm in self.school_service.get_administrations():
            self.combo_admin.addItem(adm, adm)
        g_lay.addWidget(self.combo_admin, 1, 3)

        g_lay.addWidget(QLabel("اسم الحارس / الرقم القومي:"), 2, 0)
        self.txt_guard = QLineEdit()
        self.txt_guard.setPlaceholderText("اسم الحارس أو الرقم القومي...")
        g_lay.addWidget(self.txt_guard, 2, 1)

        g_lay.addWidget(QLabel("رقم الهاتف (مدير / أمن / حارس):"), 2, 2)
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("أدخل رقم الهاتف...")
        g_lay.addWidget(self.txt_phone, 2, 3)

        g_lay.addWidget(QLabel("حالة التجهيزات والأمان:"), 3, 0)
        self.combo_equipment = QComboBox()
        self.combo_equipment.addItem("— كافة التجهيزات —", "all")
        self.combo_equipment.addItem("مدارس بها كاميرات معطلة", "broken_cameras")
        self.combo_equipment.addItem("مدارس بها خطوط حريق غير مفعلة", "inactive_lines")
        self.combo_equipment.addItem("مدارس ليس بها حراس أمن مكلفين", "no_guards")
        self.combo_equipment.addItem("مدارس غير محدد بها مسؤول أمن", "no_sec_officer")
        g_lay.addWidget(self.combo_equipment, 3, 1)

        # Buttons
        btn_h = QHBoxLayout()
        btn_h.setSpacing(8)

        self.btn_search = QPushButton("🔍 تنفيذ البحث الفوري")
        self.btn_search.setObjectName("PrimaryBtn")
        self.btn_search.setMinimumHeight(38)
        self.btn_search.clicked.connect(self.execute_search)
        btn_h.addWidget(self.btn_search)

        self.btn_reset = QPushButton("إعادة تعيين الحقول")
        self.btn_reset.setObjectName("SecondaryBtn")
        self.btn_reset.setMinimumHeight(38)
        self.btn_reset.clicked.connect(self.reset_criteria)
        btn_h.addWidget(self.btn_reset)

        btn_h.addStretch()
        g_lay.addLayout(btn_h, 3, 2, 1, 2)

        layout.addWidget(search_card)

        # 2. Results Toolbar
        res_bar = QHBoxLayout()
        self.lbl_results_count = QLabel("نتائج البحث: 0 سجل")
        self.lbl_results_count.setStyleSheet("font-weight: bold; color: #1E40AF; font-size: 13px;")
        res_bar.addWidget(self.lbl_results_count)

        res_bar.addStretch()

        self.btn_export = QPushButton("📤 تصدير نتائج البحث إلى Excel")
        self.btn_export.setObjectName("SecondaryBtn")
        self.btn_export.setMinimumHeight(36)
        self.btn_export.clicked.connect(self.export_results)
        res_bar.addWidget(self.btn_export)

        layout.addLayout(res_bar)

        # 3. Results Table
        self.table_results = QTableWidget(0, 8)
        self.table_results.setHorizontalHeaderLabels([
            "م", "الإدارة", "اسم المدرسة", "مدير المدرسة وهاتفه",
            "مسؤول الأمن", "الحراس المكلفون", "الكاميرات", "خطوط الحريق"
        ])
        self.table_results.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_results.verticalHeader().setVisible(False)
        self.table_results.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_results.doubleClicked.connect(self.on_row_double_click)

        layout.addWidget(self.table_results, 1)

    def reset_criteria(self):
        self.txt_school.clear()
        self.combo_admin.setCurrentIndex(0)
        self.txt_guard.clear()
        self.txt_phone.clear()
        self.combo_equipment.setCurrentIndex(0)
        self.table_results.setRowCount(0)
        self.lbl_results_count.setText("نتائج البحث: 0 سجل")

    def execute_search(self):
        sch_name = self.txt_school.text().strip()
        adm = self.combo_admin.currentData() or ""
        guard_kw = self.txt_guard.text().strip()
        phone_kw = self.txt_phone.text().strip()
        equip_filter = self.combo_equipment.currentData()

        where_clauses = []
        params = []

        if adm:
            where_clauses.append("s.administration = ?")
            params.append(adm)

        if sch_name:
            where_clauses.append("NORMALIZE_AR(s.school_name) LIKE NORMALIZE_AR(?)")
            params.append(f"%{sch_name}%")

        if guard_kw:
            clean_guard_kw = guard_kw.strip()
            where_clauses.append("(MATCH_NAME_SEQUENTIAL(g.guard_name, ?) OR g.national_id LIKE ?)")
            params.extend([clean_guard_kw, f"%{clean_guard_kw}%"])

        if phone_kw:
            where_clauses.append("(s.manager_phone LIKE ? OR s.security_officer_phone LIKE ? OR g.phone LIKE ?)")
            params.extend([f"%{phone_kw}%", f"%{phone_kw}%", f"%{phone_kw}%"])

        if equip_filter == "broken_cameras":
            where_clauses.append("(s.non_working_cameras != '' AND s.non_working_cameras != '0' AND s.non_working_cameras != '—')")
        elif equip_filter == "inactive_lines":
            where_clauses.append("(s.inactive_fire_lines != '' AND s.inactive_fire_lines != '0' AND s.inactive_fire_lines != '—')")
        elif equip_filter == "no_guards":
            where_clauses.append("a.guard_id IS NULL")
        elif equip_filter == "no_sec_officer":
            where_clauses.append("(s.security_officer_name = '' OR s.security_officer_name IS NULL)")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT 
                s.school_id,
                s.administration,
                s.school_name,
                s.manager_name,
                s.manager_phone,
                s.security_officer_name,
                s.security_officer_phone,
                s.working_cameras,
                s.non_working_cameras,
                s.activated_fire_lines,
                s.inactive_fire_lines,
                GROUP_CONCAT(g.guard_name, ' | ') as guards_preview
            FROM schools s
            LEFT JOIN school_guard_assignments a ON s.school_id = a.school_id
            LEFT JOIN guards g ON a.guard_id = g.guard_id
            {where_sql}
            GROUP BY s.school_id
            ORDER BY s.school_id ASC;
        """

        with self.db.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            self.current_results = [dict(r) for r in rows]

        self.table_results.setRowCount(len(self.current_results))
        for r_idx, r in enumerate(self.current_results):
            self.table_results.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.table_results.setItem(r_idx, 1, QTableWidgetItem(r.get("administration", "—")))
            self.table_results.setItem(r_idx, 2, QTableWidgetItem(r.get("school_name", "—")))
            mgr_info = f"{r.get('manager_name', '—')} ({r.get('manager_phone', '')})" if r.get("manager_phone") else r.get("manager_name", "—")
            self.table_results.setItem(r_idx, 3, QTableWidgetItem(mgr_info))
            sec_info = f"{r.get('security_officer_name', '—')} ({r.get('security_officer_phone', '')})" if r.get("security_officer_phone") else r.get("security_officer_name", "—")
            self.table_results.setItem(r_idx, 4, QTableWidgetItem(sec_info))
            self.table_results.setItem(r_idx, 5, QTableWidgetItem(r.get("guards_preview") or "لا يوجد حراس"))
            cam_str = f"تعمل: {r.get('working_cameras', '0')} | معطلة: {r.get('non_working_cameras', '0')}"
            self.table_results.setItem(r_idx, 6, QTableWidgetItem(cam_str))
            line_str = f"مفعلة: {r.get('activated_fire_lines', '0')} | غير مفعلة: {r.get('inactive_fire_lines', '0')}"
            self.table_results.setItem(r_idx, 7, QTableWidgetItem(line_str))

        self.lbl_results_count.setText(f"نتائج البحث: {len(self.current_results):,} سجل")

    def on_row_double_click(self, index):
        if 0 <= index.row() < len(self.current_results):
            school_id = self.current_results[index.row()]["school_id"]
            self.open_school_requested.emit(school_id)

    def export_results(self):
        if not self.current_results:
            QMessageBox.warning(self, "تنبيه", "لا توجد نتائج بحث لتصديرها.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ نتائج البحث المتقدم",
            "نتائج_بحث_تأمين_المدارس.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            SchoolSecurityExcelExporter.export_schools(file_path, self.current_results)
            QMessageBox.information(self, "نجاح التصدير", f"تم حفظ نتائج البحث بنجاح في:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر تصدير النتائج:\n{e}")

