from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QTableView, QHeaderView, QMessageBox, 
    QFileDialog, QFrame, QMenu, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer
import pandas as pd
from config import PALETTE, PRISONER_STATUSES
from database import DatabaseManager
from ui.table_models import PrisonersTableModel
from ui.record_dialog import AddPrisonerDialog, RecordDetailsDialog
from ui.delete_helper import prompt_smart_delete, KeyCatchingTableView

class PrisonersView(QWidget):
    """Prisoners & Criminal Cases Data Grid & Filter Controls."""
    data_changed_signal = Signal()

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.model = PrisonersTableModel([])
        self.setLayoutDirection(Qt.RightToLeft)

        # Debounce timer for smooth typing on low-end machines
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(220)
        self.search_timer.timeout.connect(self.load_data)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # Filter Bar
        filter_card = QFrame()
        filter_card.setStyleSheet(f"""
            QFrame {{ background-color: {PALETTE['surface']}; border: 1px solid {PALETTE['border_light']}; border-radius: 10px; padding: 10px; }}
            QLabel {{ border: none; }}
        """)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setSpacing(10)

        # Search Box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث سريع بالاسم، الرقم القومي، رقم القضية، أو الحكم...")
        self.search_input.textChanged.connect(self.search_timer.start)
        self.search_input.returnPressed.connect(self.load_data)
        filter_layout.addWidget(self.search_input, 3)

        # Administration Filter
        self.admin_filter = QComboBox()
        self.admin_filter.addItem("جميع الإدارات", None)
        for adm in self.db.get_administrations(category="prisoners"):
            self.admin_filter.addItem(adm["name"], adm["id"])
        self.admin_filter.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.admin_filter, 2)

        # Case Type Filter — Standard Dropdown Menu
        self.case_filter = QComboBox()
        self.populate_case_types()
        self.case_filter.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.case_filter, 2)

        # Criminal Status Filter
        self.status_filter = QComboBox()
        self.status_filter.addItem("جميع المواقف الجنائية", None)
        for st in PRISONER_STATUSES:
            self.status_filter.addItem(st, st)
        self.status_filter.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.status_filter, 2)

        # Clear Filters
        clear_btn = QPushButton("مسح التصفية")
        clear_btn.setObjectName("SecondaryBtn")
        clear_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_btn)

        main_layout.addWidget(filter_card)

        # Action Toolbar
        toolbar_layout = QHBoxLayout()

        self.count_badge = QLabel("إجمالي المسجونين: 0")
        self.count_badge.setStyleSheet(f"font-weight: bold; color: {PALETTE['danger']}; background: {PALETTE['danger_bg']}; border: 1px solid #FECACA; border-radius: 6px; padding: 6px 12px;")
        toolbar_layout.addWidget(self.count_badge)

        toolbar_layout.addStretch()

        view_btn = QPushButton("👁️ بيان حالة الموظف")
        view_btn.setObjectName("PrimaryBtn")
        view_btn.clicked.connect(self.show_selected_statement)
        toolbar_layout.addWidget(view_btn)

        edit_btn = QPushButton("✏️ تعديل بيانات السجل")
        edit_btn.setObjectName("WarningBtn")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFBEB;
                color: #D97706;
                border: 2px solid #F59E0B;
                border-radius: 6px;
                font-weight: bold;
                padding: 6px 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #FEF3C7;
            }
        """)
        edit_btn.clicked.connect(self.edit_selected_record)
        toolbar_layout.addWidget(edit_btn)

        add_btn = QPushButton("➕ إضافة سجل مسجون / قضية")
        add_btn.setObjectName("SecondaryBtn")
        add_btn.clicked.connect(self.open_add_dialog)
        toolbar_layout.addWidget(add_btn)

        scan_btn = QPushButton("📷 مسح ضوئي لمستند")
        scan_btn.setObjectName("SecondaryBtn")
        scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #1E40AF;
                border: 2px solid #3B82F6;
                border-radius: 6px;
                font-weight: bold;
                padding: 6px 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #DBEAFE;
            }
        """)
        scan_btn.clicked.connect(self.open_scan_dialog)
        toolbar_layout.addWidget(scan_btn)

        export_btn = QPushButton("📊 تصدير إلى Excel")
        export_btn.setObjectName("SecondaryBtn")
        export_btn.clicked.connect(self.export_to_excel)
        toolbar_layout.addWidget(export_btn)

        del_btn = QPushButton("🗑️ حذف السجل المحدد")
        del_btn.setObjectName("DangerBtn")
        del_btn.clicked.connect(self.delete_selected)
        toolbar_layout.addWidget(del_btn)

        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self.load_data)
        toolbar_layout.addWidget(refresh_btn)

        main_layout.addLayout(toolbar_layout)

        # Data Table
        self.table_view = KeyCatchingTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._set_column_widths()
        self.table_view.doubleClicked.connect(self.on_row_double_clicked)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.on_table_context_menu)
        self.table_view.delete_requested.connect(self.delete_selected)
        main_layout.addWidget(self.table_view)

    def _set_column_widths(self):
        widths = [50, 220, 135, 130, 160, 95, 120, 130, 140, 160, 110, 150]
        for idx, w in enumerate(widths):
            self.table_view.setColumnWidth(idx, w)

    def populate_case_types(self):
        self.case_filter.blockSignals(True)
        self.case_filter.clear()
        self.case_filter.addItem("جميع أنواع القضايا", None)
        for ct in self.db.get_case_types(category="prisoners"):
            self.case_filter.addItem(str(ct["name"]), ct["id"])
        self.case_filter.blockSignals(False)

    def load_data(self):
        self.search_timer.stop()
        query = self.search_input.text().strip()
        admin_id = self.admin_filter.currentData()
        case_id = self.case_filter.currentData()
        status = self.status_filter.currentData()

        records = self.db.search_prisoners(
            query=query, admin_id=admin_id, case_type_id=case_id, status=status, limit=5000
        )
        self.model.update_data(records)
        self.count_badge.setText(f"إجمالي المسجونين والقضايا: {len(records):,}")

    def on_filter_changed(self):
        self.load_data()

    def refresh_combos(self):
        curr_admin = self.admin_filter.currentData()
        curr_case = self.case_filter.currentData()

        self.admin_filter.blockSignals(True)
        self.case_filter.blockSignals(True)

        self.admin_filter.clear()
        self.admin_filter.addItem("جميع الإدارات", None)
        for adm in self.db.get_administrations(category="prisoners"):
            self.admin_filter.addItem(adm["name"], adm["id"])

        self.admin_filter.blockSignals(False)
        self.populate_case_types()
        if curr_case:
            idx_c = self.case_filter.findData(curr_case)
            if idx_c >= 0:
                self.case_filter.setCurrentIndex(idx_c)

    def clear_filters(self):
        self.search_input.clear()
        self.admin_filter.setCurrentIndex(0)
        self.case_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.load_data()

    def open_add_dialog(self):
        dlg = AddPrisonerDialog(self.db, self)
        if dlg.exec():
            self.load_data()
            self.data_changed_signal.emit()

    def open_scan_dialog(self):
        from ui.smart_scan_dialog import SmartScanDialog
        dlg = SmartScanDialog(self.db, default_record_type="prisoner", parent=self)
        dlg.record_added_signal.connect(self.load_data)
        dlg.record_added_signal.connect(self.data_changed_signal.emit)
        dlg.exec()

    def on_row_double_clicked(self, index):
        row_data = self.model.get_row(index.row())
        if row_data:
            self.open_statement_for_row(row_data)

    def open_statement_for_row(self, row_data):
        dlg = RecordDetailsDialog(row_data, record_type="prisoners", db_manager=self.db, parent=self)
        dlg.exec()

    def show_selected_statement(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار موظف من الجدول لعرض بيان الحالة الخاص به.")
            return
        row_data = self.model.get_row(indexes[0].row())
        if row_data:
            self.open_statement_for_row(row_data)

    def edit_selected_record(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار موظف من الجدول لتعديل بياناته.")
            return
        row_data = self.model.get_row(indexes[0].row())
        if row_data:
            self.edit_record_for_row(row_data)

    def edit_record_for_row(self, row_data):
        from ui.record_dialog import EditPrisonerDialog
        dlg = EditPrisonerDialog(row_data, db_manager=self.db, parent=self)
        if dlg.exec():
            self.load_data()
            if hasattr(self, "data_changed_signal") and self.data_changed_signal:
                self.data_changed_signal.emit()

    def on_table_context_menu(self, pos):
        """Right-click context menu on row: allows deleting, editing, viewing, and copying."""
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return
        row_data = self.model.get_row(index.row())
        if not row_data:
            return

        menu = QMenu(self)
        menu.setLayoutDirection(Qt.RightToLeft)

        emp_name = row_data.get("full_name", "")
        title_action = menu.addAction(f"👤 {emp_name}")
        title_action.setEnabled(False)
        menu.addSeparator()

        edit_action = menu.addAction("✏️ تعديل بيانات هذا السجل")
        edit_action.triggered.connect(lambda: self.edit_record_for_row(row_data))

        view_action = menu.addAction("👁️ عرض بيان حالة الموظف")
        view_action.triggered.connect(lambda: self.open_statement_for_row(row_data))

        del_action = menu.addAction("🗑️ مسح / حذف هذا السجل نهائياً")
        del_action.triggered.connect(lambda: self.confirm_and_delete_row(row_data))

        menu.addSeparator()

        copy_name = menu.addAction("📋 نسخ اسم الموظف")
        copy_name.triggered.connect(lambda: QApplication.clipboard().setText(str(emp_name)))

        copy_nid = menu.addAction("📋 نسخ الرقم القومي")
        copy_nid.triggered.connect(lambda: QApplication.clipboard().setText(str(row_data.get("national_id") or "")))

        menu.exec(self.table_view.viewport().mapToGlobal(pos))

    def confirm_and_delete_row(self, row_data):
        deleted = prompt_smart_delete(self, self.db, "PrisonerRecords", row_data)
        if deleted:
            self.load_data()
            self.data_changed_signal.emit()

    def delete_selected(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد السجل المراد حذفه من الجدول أولاً.")
            return

        row_idx = indexes[0].row()
        row_data = self.model.get_row(row_idx)
        if not row_data:
            return

        self.confirm_and_delete_row(row_data)

    def export_to_excel(self):
        if not self.model._data:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات ظاهرة في الجدول لتصديرها.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "تصدير قائمة المسجونين إلى Excel",
            "قائمة_المسجونين_مديرية_التعليم.xlsx",
            "Excel Files (*.xlsx)"
        )
        if save_path:
            try:
                from excel_exporter import export_records_to_excel
                columns_config = [
                    ("record_number", "م", 8),
                    ("full_name", "الاسم رباعي", 30),
                    ("national_id", "الرقم القومي", 20),
                    ("administration_name", "الإدارة التعليمية", 22),
                    ("school", "جهة العمل / المدرسة", 25),
                    ("case_number", "رقم القضية", 25),
                    ("case_type_name", "نوع القضية", 20),
                    ("court_ruling", "الحكم الصادر", 20),
                    ("current_status", "الوضع الراهن", 22),
                    ("release_date", "تاريخ الإفراج", 22),
                    ("housing_location", "مكان التسكين", 25),
                    ("phone", "الهاتف", 16)
                ]
                export_records_to_excel(
                    file_path=save_path,
                    title="كشف بيانات المسجونين والأحكام القضائية - مديرية التربية والتعليم بالإسكندرية",
                    records=self.model._data,
                    columns_config=columns_config
                )
                QMessageBox.information(self, "نجاح التصدير", f"تم تصدير {len(self.model._data)} سجل بنجاح كامل وبتنسيق معتمد إلى:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر تصدير الملف: {str(e)}")
