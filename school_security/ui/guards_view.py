# -*- coding: utf-8 -*-
"""
Security Guards Management View for School Security System.
Features:
- Filter Card (Search, Administration, School)
- Action Toolbar (Add, Edit, Reassign, Detect Duplicates, Delete, Export)
- Virtualized Table with GuardTableModel
- Context menu and dialogs integration
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableView, QHeaderView, QMenu,
    QMessageBox, QFileDialog, QFrame, QDialog, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Qt, Signal

from ..services.guard_service import GuardService
from ..services.school_service import SchoolService
from ..services.excel_exporter import SchoolSecurityExcelExporter
from .table_models import GuardTableModel
from .guard_dialog import GuardDialog


class DuplicatesDialog(QDialog):
    """Dialog displaying detected duplicate guards with resolution options."""
    def __init__(self, duplicates, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠️ كشف وتحليل حراس الأمن المكررين والمتشابهين")
        self.resize(750, 480)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        info = QLabel(f"تم اكتشاف ({len(duplicates)}) حالة تشابه أو تكرار بالرقم القومي أو الاسم:")
        info.setStyleSheet("font-weight: bold; color: #B45309; font-size: 13px;")
        layout.addWidget(info)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["نوع التكرار", "القيمة / المفتاح", "اسم الحارس", "المدرسة المكلفة", "الإدارة"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        row_cnt = 0
        for group in duplicates:
            g_type = group["type"]
            g_key = group["key"]
            for g in group["guards"]:
                table.insertRow(row_cnt)
                table.setItem(row_cnt, 0, QTableWidgetItem(g_type))
                table.setItem(row_cnt, 1, QTableWidgetItem(str(g_key)))
                table.setItem(row_cnt, 2, QTableWidgetItem(g.get("guard_name", "")))
                table.setItem(row_cnt, 3, QTableWidgetItem(g.get("school_name", "—")))
                table.setItem(row_cnt, 4, QTableWidgetItem(g.get("administration", "—")))
                row_cnt += 1

        layout.addWidget(table, 1)

        btn_close = QPushButton("إغلاق")
        btn_close.setObjectName("SecondaryBtn")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)


class GuardsView(QWidget):
    data_changed = Signal()

    def __init__(
        self,
        guard_service: GuardService,
        school_service: SchoolService,
        parent=None
    ):
        super().__init__(parent)
        self.guard_service = guard_service
        self.school_service = school_service
        self.table_model = GuardTableModel()

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
        self.txt_search.setPlaceholderText("ابحث باسم الحارس، الرقم القومي، الهاتف، أو المدرسة...")
        self.txt_search.textChanged.connect(self.load_data)
        f_lay.addWidget(self.txt_search, 2)

        f_lay.addWidget(QLabel("الإدارة التعليمية:"))
        self.combo_admin = QComboBox()
        self.combo_admin.addItem("— كل الإدارات —", "")
        self.combo_admin.currentIndexChanged.connect(self.load_data)
        f_lay.addWidget(self.combo_admin, 1)

        self.btn_reset = QPushButton("إعادة تعيين")
        self.btn_reset.setObjectName("SecondaryBtn")
        self.btn_reset.clicked.connect(self.reset_filters)
        f_lay.addWidget(self.btn_reset)

        layout.addWidget(filter_card)

        # 2. Action Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_add = QPushButton("➕ إضافة حارس أمن جديد")
        self.btn_add.setObjectName("PrimaryBtn")
        self.btn_add.setMinimumHeight(38)
        self.btn_add.clicked.connect(self.open_add_dialog)
        toolbar.addWidget(self.btn_add)

        self.btn_edit = QPushButton("✏️ تعديل بيانات الحارس")
        self.btn_edit.setObjectName("SecondaryBtn")
        self.btn_edit.setMinimumHeight(38)
        self.btn_edit.clicked.connect(self.open_edit_dialog)
        toolbar.addWidget(self.btn_edit)

        self.btn_dups = QPushButton("⚠️ كشف المتشابهات")
        self.btn_dups.setObjectName("SecondaryBtn")
        self.btn_dups.setMinimumHeight(38)
        self.btn_dups.clicked.connect(self.check_duplicates)
        toolbar.addWidget(self.btn_dups)

        self.btn_delete = QPushButton("🗑️ حذف الحارس")
        self.btn_delete.setObjectName("DangerBtn")
        self.btn_delete.setMinimumHeight(38)
        self.btn_delete.clicked.connect(self.delete_selected_guard)
        toolbar.addWidget(self.btn_delete)

        toolbar.addStretch()

        self.lbl_count = QLabel("عدد الحراس: 0")
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
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        self.table_view.doubleClicked.connect(self.open_edit_dialog)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.horizontalHeader().setDefaultSectionSize(140)
        self.table_view.horizontalHeader().resizeSection(0, 45)
        self.table_view.horizontalHeader().resizeSection(1, 180)  # guard name
        self.table_view.horizontalHeader().resizeSection(4, 200)  # school name

        layout.addWidget(self.table_view, 1)

    def refresh_combos(self):
        cur_adm = self.combo_admin.currentData() or ""
        self.combo_admin.blockSignals(True)
        self.combo_admin.clear()
        self.combo_admin.addItem("— كل الإدارات —", "")
        for adm in self.school_service.get_administrations():
            self.combo_admin.addItem(adm, adm)
        self.combo_admin.setCurrentText(cur_adm)
        self.combo_admin.blockSignals(False)

    def load_data(self):
        query = self.txt_search.text().strip()
        adm = self.combo_admin.currentData() or ""

        guards = self.guard_service.get_guards(
            search_query=query,
            administration=adm
        )
        self.table_model.update_data(guards)
        self.lbl_count.setText(f"عدد الحراس: {len(guards):,}")

    def reset_filters(self):
        self.txt_search.clear()
        self.combo_admin.setCurrentIndex(0)
        self.load_data()

    def get_selected_guard(self) -> Optional[Dict[str, Any]]:
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return None
        row_idx = indexes[0].row()
        return self.table_model.get_row(row_idx)

    def open_add_dialog(self):
        dlg = GuardDialog(self.guard_service, self.school_service, parent=self)
        dlg.data_saved.connect(self.on_data_updated)
        dlg.data_saved.connect(self.data_changed.emit)
        dlg.exec()

    def open_edit_dialog(self):
        guard = self.get_selected_guard()
        if not guard:
            QMessageBox.information(self, "تحديد سجل", "يرجى تحديد حارس أمن من الجدول لتعديله.")
            return
        dlg = GuardDialog(self.guard_service, self.school_service, guard_id=guard["guard_id"], parent=self)
        dlg.data_saved.connect(self.on_data_updated)
        dlg.data_saved.connect(self.data_changed.emit)
        dlg.exec()

    def check_duplicates(self):
        duplicates = self.guard_service.find_duplicate_guards()
        if not duplicates:
            QMessageBox.information(self, "فحص المتشابهات", "✅ لا توجد أي سجلات مكررة في الرقم القومي أو الأسماء.")
            return
        dlg = DuplicatesDialog(duplicates, parent=self)
        dlg.exec()

    def delete_selected_guard(self):
        guard = self.get_selected_guard()
        if not guard:
            QMessageBox.information(self, "تحديد سجل", "يرجى تحديد حارس أمن من الجدول لحذفه.")
            return

        name = guard.get("guard_name", "")
        reply = QMessageBox.question(
            self,
            "تأكيد حذف حارس أمن",
            f"هل أنت متأكد من حذف الحارس «{name}» نهائياً من المنظومة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.guard_service.delete_guard(guard["guard_id"])
            self.on_data_updated()
            self.data_changed.emit()
            QMessageBox.information(self, "تم الحذف", f"تم حذف الحارس «{name}» بنجاح.")

    def on_data_updated(self):
        self.refresh_combos()
        self.load_data()

    def export_to_excel(self):
        query = self.txt_search.text().strip()
        adm = self.combo_admin.currentData() or ""
        guards = self.guard_service.get_guards(search_query=query, administration=adm)

        if not guards:
            QMessageBox.warning(self, "تنبيه", "لا توجد سجلات لتصديرها.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ كشف حراس الأمن",
            "كشف_حراس_أمن_المدارس.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            SchoolSecurityExcelExporter.export_guards(file_path, guards)
            QMessageBox.information(self, "نجاح التصدير", f"تم تصدير ({len(guards):,}) حارس أمن بنجاح إلى:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر حفظ ملف الإكسيل:\n{e}")

    def show_context_menu(self, pos):
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return
        menu = QMenu(self)
        act_edit = menu.addAction("✏️ تعديل بيانات الحارس")
        menu.addSeparator()
        act_delete = menu.addAction("🗑️ حذف الحارس")

        act_edit.triggered.connect(self.open_edit_dialog)
        act_delete.triggered.connect(self.delete_selected_guard)
        menu.exec(self.table_view.viewport().mapToGlobal(pos))
