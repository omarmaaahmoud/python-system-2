# -*- coding: utf-8 -*-
"""
Schools Management View for School Security System.
Features:
- Filter Card (Search, Administration, Affiliation)
- Action Toolbar (Add, Edit, View, Delete, Export)
- Virtualized Table with SchoolTableModel
- Context menu and details dialog integration
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableView, QHeaderView, QMenu,
    QMessageBox, QFileDialog, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon

from ..services.school_service import SchoolService
from ..services.guard_service import GuardService
from ..services.excel_exporter import SchoolSecurityExcelExporter
from .table_models import SchoolTableModel
from .school_dialog import SchoolDialog


class SchoolsView(QWidget):
    data_changed = Signal()

    def __init__(
        self,
        school_service: SchoolService,
        guard_service: GuardService,
        parent=None
    ):
        super().__init__(parent)
        self.school_service = school_service
        self.guard_service = guard_service
        self.table_model = SchoolTableModel()

        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. Filter Card
        filter_card = QFrame()
        filter_card.setObjectName("FilterCard")
        filter_card.setStyleSheet("""
            QFrame#FilterCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        f_lay = QHBoxLayout(filter_card)
        f_lay.setSpacing(10)

        f_lay.addWidget(QLabel("🔍 بحث سريع:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("ابحث باسم المدرسة، المدير، مسؤول الأمن...")
        self.txt_search.textChanged.connect(self.load_data)
        f_lay.addWidget(self.txt_search, 2)

        f_lay.addWidget(QLabel("الإدارة التعليمية:"))
        self.combo_admin = QComboBox()
        self.combo_admin.addItem("— كل الإدارات —", "")
        self.combo_admin.currentIndexChanged.connect(self.load_data)
        f_lay.addWidget(self.combo_admin, 1)

        f_lay.addWidget(QLabel("التبعية:"))
        self.combo_affil = QComboBox()
        self.combo_affil.addItem("— كل التبعيات —", "")
        self.combo_affil.currentIndexChanged.connect(self.load_data)
        f_lay.addWidget(self.combo_affil, 1)

        self.btn_reset = QPushButton("إعادة تعيين")
        self.btn_reset.setObjectName("SecondaryBtn")
        self.btn_reset.clicked.connect(self.reset_filters)
        f_lay.addWidget(self.btn_reset)

        layout.addWidget(filter_card)

        # 2. Action Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_add = QPushButton("➕ إضافة مدرسة جديدة")
        self.btn_add.setObjectName("PrimaryBtn")
        self.btn_add.setMinimumHeight(38)
        self.btn_add.clicked.connect(self.open_add_dialog)
        toolbar.addWidget(self.btn_add)

        self.btn_edit = QPushButton("✏️ تعديل المدرسة")
        self.btn_edit.setObjectName("SecondaryBtn")
        self.btn_edit.setMinimumHeight(38)
        self.btn_edit.clicked.connect(self.open_edit_dialog)
        toolbar.addWidget(self.btn_edit)

        self.btn_view = QPushButton("👁️ عرض التفاصيل والحراس")
        self.btn_view.setObjectName("SecondaryBtn")
        self.btn_view.setMinimumHeight(38)
        self.btn_view.clicked.connect(self.open_details_dialog)
        toolbar.addWidget(self.btn_view)

        self.btn_delete = QPushButton("🗑️ حذف المدرسة")
        self.btn_delete.setObjectName("DangerBtn")
        self.btn_delete.setMinimumHeight(38)
        self.btn_delete.clicked.connect(self.delete_selected_school)
        toolbar.addWidget(self.btn_delete)

        toolbar.addStretch()

        self.lbl_count = QLabel("عدد المدارس: 0")
        self.lbl_count.setStyleSheet("font-weight: bold; color: #1E40AF; padding: 0 10px;")
        toolbar.addWidget(self.lbl_count)

        self.btn_export = QPushButton("📤 تصدير إلى Excel")
        self.btn_export.setObjectName("SecondaryBtn")
        self.btn_export.setMinimumHeight(38)
        self.btn_export.clicked.connect(self.export_to_excel)
        toolbar.addWidget(self.btn_export)

        layout.addLayout(toolbar)

        # 3. Virtualized Table View
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(False)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.table_view.doubleClicked.connect(self.open_details_dialog)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.horizontalHeader().setDefaultSectionSize(130)
        self.table_view.horizontalHeader().resizeSection(0, 45)
        self.table_view.horizontalHeader().resizeSection(2, 220)  # school name

        layout.addWidget(self.table_view, 1)

    def refresh_combos(self):
        cur_adm = self.combo_admin.currentData() or ""
        cur_aff = self.combo_affil.currentData() or ""

        self.combo_admin.blockSignals(True)
        self.combo_admin.clear()
        self.combo_admin.addItem("— كل الإدارات —", "")
        for adm in self.school_service.get_administrations():
            self.combo_admin.addItem(adm, adm)
        self.combo_admin.setCurrentText(cur_adm)
        self.combo_admin.blockSignals(False)

        self.combo_affil.blockSignals(True)
        self.combo_affil.clear()
        self.combo_affil.addItem("— كل التبعيات —", "")
        for aff in self.school_service.get_affiliations():
            self.combo_affil.addItem(aff, aff)
        self.combo_affil.setCurrentText(cur_aff)
        self.combo_affil.blockSignals(False)

    def load_data(self):
        query = self.txt_search.text().strip()
        adm = self.combo_admin.currentData() or ""
        aff = self.combo_affil.currentData() or ""

        schools = self.school_service.get_schools(
            search_query=query,
            administration=adm,
            affiliation=aff
        )
        self.table_model.update_data(schools)
        self.lbl_count.setText(f"عدد المدارس: {len(schools):,}")

    def reset_filters(self):
        self.txt_search.clear()
        self.combo_admin.setCurrentIndex(0)
        self.combo_affil.setCurrentIndex(0)
        self.load_data()

    def get_selected_school(self) -> Optional[Dict[str, Any]]:
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return None
        row_idx = indexes[0].row()
        return self.table_model.get_row(row_idx)

    def open_add_dialog(self):
        dlg = SchoolDialog(self.school_service, self.guard_service, parent=self)
        dlg.data_saved.connect(self.on_data_updated)
        dlg.data_saved.connect(self.data_changed.emit)
        dlg.exec()

    def open_edit_dialog(self):
        school = self.get_selected_school()
        if not school:
            QMessageBox.information(self, "تحديد سجل", "يرجى تحديد مدرسة من الجدول لتعديلها.")
            return
        dlg = SchoolDialog(self.school_service, self.guard_service, school_id=school["school_id"], parent=self)
        dlg.data_saved.connect(self.on_data_updated)
        dlg.data_saved.connect(self.data_changed.emit)
        dlg.exec()

    def open_details_dialog(self):
        school = self.get_selected_school()
        if not school:
            QMessageBox.information(self, "تحديد سجل", "يرجى تحديد مدرسة من الجدول لعرض بياناتها.")
            return
        dlg = SchoolDialog(self.school_service, self.guard_service, school_id=school["school_id"], read_only=True, parent=self)
        dlg.exec()

    def delete_selected_school(self):
        school = self.get_selected_school()
        if not school:
            QMessageBox.information(self, "تحديد سجل", "يرجى تحديد مدرسة من الجدول لحذفها.")
            return

        name = school.get("school_name", "")
        reply = QMessageBox.question(
            self,
            "تأكيد حذف مدرسة",
            f"هل أنت متأكد من حذف مدرسة «{name}» نهائياً من المنظومة؟\nسيتم حذف جميع سجلات التكليفات المرتبطة بها.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.school_service.delete_school(school["school_id"])
            self.on_data_updated()
            self.data_changed.emit()
            QMessageBox.information(self, "تم الحذف", f"تم حذف مدرسة «{name}» بنجاح.")

    def on_data_updated(self):
        self.refresh_combos()
        self.load_data()

    def export_to_excel(self):
        query = self.txt_search.text().strip()
        adm = self.combo_admin.currentData() or ""
        aff = self.combo_affil.currentData() or ""
        schools = self.school_service.get_schools(search_query=query, administration=adm, affiliation=aff)

        if not schools:
            QMessageBox.warning(self, "تنبيه", "لا توجد سجلات لتصديرها.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ تقرير المدارس",
            "سجلات_تأمين_المدارس.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            SchoolSecurityExcelExporter.export_schools(file_path, schools)
            QMessageBox.information(self, "نجاح التصدير", f"تم تصدير ({len(schools):,}) مدرسة بنجاح إلى:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر حفظ ملف الإكسيل:\n{e}")

    def show_context_menu(self, pos):
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return
        menu = QMenu(self)
        act_view = menu.addAction("👁️ عرض التفاصيل والحراس")
        act_edit = menu.addAction("✏️ تعديل بيانات المدرسة")
        menu.addSeparator()
        act_delete = menu.addAction("🗑️ حذف المدرسة")

        act_view.triggered.connect(self.open_details_dialog)
        act_edit.triggered.connect(self.open_edit_dialog)
        act_delete.triggered.connect(self.delete_selected_school)
        menu.exec(self.table_view.viewport().mapToGlobal(pos))
