from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QTabWidget, QTableView, QHeaderView, 
    QFrame, QMenu, QApplication, QMessageBox, QFileDialog, QCompleter
)
from PySide6.QtCore import Qt, QTimer, Signal
from config import PALETTE
from database import DatabaseManager
from ui.table_models import ExcludedTableModel, PrisonersTableModel
from ui.record_dialog import RecordDetailsDialog
from ui.delete_helper import prompt_smart_delete
import pandas as pd


class KeyCatchingTableView(QTableView):
    """QTableView subclass that handles keyboard Delete key to delete records directly."""
    delete_requested = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_requested.emit()
        else:
            super().keyPressEvent(event)


class AdvancedSearchView(QWidget):
    """Unified Advanced Instant Search & Filter View."""
    data_changed_signal = Signal()

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.excluded_model = ExcludedTableModel([])
        self.prisoners_model = PrisonersTableModel([])
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # Search & Filter Card
        filter_card = QFrame()
        filter_card.setStyleSheet(f"""
            QFrame {{ 
                background-color: {PALETTE['surface']}; 
                border: 1px solid {PALETTE['border_light']}; 
                border-radius: 12px; 
                padding: 14px; 
            }}
            QLabel {{ border: none; }}
        """)
        card_v = QVBoxLayout(filter_card)
        card_v.setSpacing(10)

        # Title Row
        title_row = QHBoxLayout()
        title_lbl = QLabel("🔍  محرك البحث الشامل والمتقدم (بحث بالإسم، الرقم القومي، ونوع القضية)")
        title_lbl.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {PALETTE['primary']}; border: none;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        help_tip = QLabel("💡 يمكنك كتابة أي كلمة من نوع القضية في خانة القضايا للبحث الفوري")
        help_tip.setStyleSheet("font-size: 11px; color: #64748B; border: none;")
        title_row.addWidget(help_tip)
        card_v.addLayout(title_row)

        # Debounce Timer for lightning-fast search on low-end machines
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(200)
        self.search_timer.timeout.connect(self.execute_search)

        # Row 1: Search Inputs
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        # 1. Name / National ID input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("👤 اكتب اسم الموظف أو الرقم القومي...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                font-size: 13px; padding: 8px 12px;
                border: 1.5px solid #CBD5E1; border-radius: 8px;
                background-color: #FFFFFF; color: #0F172A;
            }
            QLineEdit:focus { border-color: #2563EB; }
        """)
        self.search_input.textChanged.connect(self.search_timer.start)
        self.search_input.returnPressed.connect(self.execute_search)
        row1.addWidget(self.search_input, 4)

        # 2. Case Type Filter — Standard Dropdown Menu
        self.case_filter = QComboBox()
        self.populate_case_types()
        self.case_filter.currentIndexChanged.connect(self.execute_search)
        row1.addWidget(self.case_filter, 3)

        # 3. Administration Filter
        self.admin_filter = QComboBox()
        self.admin_filter.setStyleSheet("""
            QComboBox {
                font-size: 13px; padding: 6px 10px;
                border: 1.5px solid #CBD5E1; border-radius: 8px;
                background-color: #FFFFFF; color: #0F172A;
                min-height: 24px;
            }
            QComboBox:focus { border-color: #2563EB; }
        """)
        self.admin_filter.addItem("🏢 جميع الإدارات التعليمية", None)
        for adm in self.db.get_administrations():
            self.admin_filter.addItem(adm["name"], adm["id"])
        self.admin_filter.currentIndexChanged.connect(self.execute_search)
        row1.addWidget(self.admin_filter, 3)

        # 4. Clear Filters Button
        clear_btn = QPushButton("🔄 مسح الفلاتر")
        clear_btn.setObjectName("SecondaryBtn")
        clear_btn.setMinimumHeight(38)
        clear_btn.clicked.connect(self.clear_search)
        row1.addWidget(clear_btn)

        card_v.addLayout(row1)
        main_layout.addWidget(filter_card)

        # Results Toolbar: Actions & Summary Badges
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.summary_badge = QLabel("نتائج البحث: 0 مستبعد | 0 مسجون")
        self.summary_badge.setStyleSheet(f"""
            font-weight: bold; color: {PALETTE['primary']}; 
            background: #EFF6FF; border: 1px solid #BFDBFE; 
            border-radius: 6px; padding: 6px 14px; font-size: 13px;
        """)
        toolbar.addWidget(self.summary_badge)

        toolbar.addStretch()

        del_btn = QPushButton("🗑️ حذف السجل المحدد")
        del_btn.setObjectName("DangerBtn")
        del_btn.setStyleSheet("""
            QPushButton#DangerBtn {
                background-color: #DC2626; color: white; font-weight: bold; font-size: 12px;
                border-radius: 6px; border: none; padding: 6px 14px;
            }
            QPushButton#DangerBtn:hover { background-color: #B91C1C; }
        """)
        del_btn.clicked.connect(self.delete_selected)
        toolbar.addWidget(del_btn)

        export_btn = QPushButton("📊 تصدير نتائج البحث (Excel)")
        export_btn.setObjectName("SecondaryBtn")
        export_btn.clicked.connect(self.export_search_results)
        toolbar.addWidget(export_btn)

        main_layout.addLayout(toolbar)

        # Tab Widget for unified results
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                background: white;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #F1F5F9;
                color: #475569;
                font-weight: 600;
                padding: 10px 24px;
                margin-left: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #1E40AF;
                border-top: 3px solid #1E40AF;
            }
        """)

        # Tab 1: Excluded Table
        self.excluded_table = KeyCatchingTableView()
        self.excluded_table.setModel(self.excluded_model)
        self.excluded_table.setSelectionBehavior(QTableView.SelectRows)
        self.excluded_table.setSelectionMode(QTableView.SingleSelection)
        self.excluded_table.setAlternatingRowColors(True)
        self.excluded_table.verticalHeader().setVisible(False)
        self.excluded_table.horizontalHeader().setStretchLastSection(True)
        self.excluded_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._set_excluded_column_widths(self.excluded_table)
        self.excluded_table.doubleClicked.connect(self.on_excluded_double_clicked)
        self.excluded_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.excluded_table.customContextMenuRequested.connect(self.on_excluded_context_menu)
        self.excluded_table.delete_requested.connect(self.delete_selected)
        self.tabs.addTab(self.excluded_table, "سجلات المستبعدين (0)")

        # Tab 2: Prisoners Table
        self.prisoners_table = KeyCatchingTableView()
        self.prisoners_table.setModel(self.prisoners_model)
        self.prisoners_table.setSelectionBehavior(QTableView.SelectRows)
        self.prisoners_table.setSelectionMode(QTableView.SingleSelection)
        self.prisoners_table.setAlternatingRowColors(True)
        self.prisoners_table.verticalHeader().setVisible(False)
        self.prisoners_table.horizontalHeader().setStretchLastSection(True)
        self.prisoners_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._set_prisoner_column_widths(self.prisoners_table)
        self.prisoners_table.doubleClicked.connect(self.on_prisoner_double_clicked)
        self.prisoners_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.prisoners_table.customContextMenuRequested.connect(self.on_prisoner_context_menu)
        self.prisoners_table.delete_requested.connect(self.delete_selected)
        self.tabs.addTab(self.prisoners_table, "سجلات المسجونين والقضايا (0)")

        main_layout.addWidget(self.tabs, 1)

        self.execute_search()

    def populate_case_types(self):
        """Populates the case types dropdown combo box."""
        self.case_filter.blockSignals(True)
        self.case_filter.clear()
        self.case_filter.addItem("⚖️ جميع أنواع القضايا", None)
        
        for ct in self.db.get_case_types():
            self.case_filter.addItem(str(ct["name"]), ct["id"])

        self.case_filter.blockSignals(False)

    def _set_excluded_column_widths(self, table: QTableView):
        widths = [50, 220, 135, 130, 160, 95, 130, 130, 130, 105, 130, 200]
        for idx, w in enumerate(widths):
            table.setColumnWidth(idx, w)

    def _set_prisoner_column_widths(self, table: QTableView):
        widths = [50, 220, 135, 130, 160, 95, 120, 130, 140, 160, 110, 150]
        for idx, w in enumerate(widths):
            table.setColumnWidth(idx, w)

    def load_data(self):
        """Alias so external components calling load_data() on parent work seamlessly."""
        self.execute_search()

    def execute_search(self):
        self.search_timer.stop()
        q = self.search_input.text().strip()
        admin_id = self.admin_filter.currentData()
        case_id = self.case_filter.currentData()

        res = self.db.unified_search(
            query=q, 
            case_type_id=case_id, 
            admin_id=admin_id
        )
        excluded = res["excluded"]
        prisoners = res["prisoners"]

        self.excluded_model.update_data(excluded)
        self.prisoners_model.update_data(prisoners)

        self.tabs.setTabText(0, f"🚫 سجلات المستبعدين ({len(excluded):,})")
        self.tabs.setTabText(1, f"⚖️ سجلات المسجونين والقضايا ({len(prisoners):,})")
        self.summary_badge.setText(f"نتائج البحث: {len(excluded):,} مستبعد | {len(prisoners):,} مسجون")

        # Auto-switch to tab that has results if current active tab is empty
        if len(excluded) > 0 and len(prisoners) == 0 and self.tabs.currentIndex() == 1:
            self.tabs.setCurrentIndex(0)
        elif len(prisoners) > 0 and len(excluded) == 0 and self.tabs.currentIndex() == 0:
            self.tabs.setCurrentIndex(1)

    def refresh_combos(self):
        curr_admin = self.admin_filter.currentData()
        curr_case = self.case_filter.currentData()

        self.admin_filter.blockSignals(True)
        self.admin_filter.clear()
        self.admin_filter.addItem("🏢 جميع الإدارات التعليمية", None)
        for adm in self.db.get_administrations():
            self.admin_filter.addItem(adm["name"], adm["id"])

        idx = self.admin_filter.findData(curr_admin)
        if idx >= 0:
            self.admin_filter.setCurrentIndex(idx)
        self.admin_filter.blockSignals(False)

        self.populate_case_types()
        if curr_case is not None:
            idx_c = self.case_filter.findData(curr_case)
            if idx_c >= 0:
                self.case_filter.setCurrentIndex(idx_c)

    def set_focus_field(self, field_type: str):
        """Allows switching focus programmatically from Dashboard buttons."""
        if field_type == "name_nid":
            self.search_input.setFocus()
            self.search_input.selectAll()
        elif field_type == "case_type":
            self.case_filter.setFocus()
            self.case_filter.showPopup()

    def clear_search(self):
        self.search_input.clear()
        self.case_filter.setCurrentIndex(0)
        self.admin_filter.setCurrentIndex(0)
        self.execute_search()

    def on_excluded_double_clicked(self, index):
        row_data = self.excluded_model.get_row(index.row())
        if row_data:
            dlg = RecordDetailsDialog(row_data, record_type="excluded", db_manager=self.db, parent=self)
            dlg.exec()

    def on_prisoner_double_clicked(self, index):
        row_data = self.prisoners_model.get_row(index.row())
        if row_data:
            dlg = RecordDetailsDialog(row_data, record_type="prisoners", db_manager=self.db, parent=self)
            dlg.exec()

    def delete_selected(self):
        """Deletes the selected row from whichever tab is currently active."""
        if self.tabs.currentIndex() == 0:
            indexes = self.excluded_table.selectionModel().selectedRows()
            if not indexes:
                QMessageBox.warning(self, "تنبيه", "يرجى تحديد السجل المراد حذفه من جدول المستبعدين أولاً.")
                return
            row_data = self.excluded_model.get_row(indexes[0].row())
            if row_data:
                self.confirm_and_delete_record("ExcludedRecords", row_data)
        else:
            indexes = self.prisoners_table.selectionModel().selectedRows()
            if not indexes:
                QMessageBox.warning(self, "تنبيه", "يرجى تحديد السجل المراد حذفه من جدول المسجونين أولاً.")
                return
            row_data = self.prisoners_model.get_row(indexes[0].row())
            if row_data:
                self.confirm_and_delete_record("PrisonerRecords", row_data)

    def confirm_and_delete_record(self, table_name: str, row_data: dict):
        """Uses smart deletion helper to offer full purge or single record delete."""
        deleted = prompt_smart_delete(self, self.db, table_name, row_data)
        if deleted:
            self.execute_search()
            self.data_changed_signal.emit()

    def on_excluded_context_menu(self, pos):
        index = self.excluded_table.indexAt(pos)
        if not index.isValid():
            return
        row_data = self.excluded_model.get_row(index.row())
        if not row_data:
            return

        menu = QMenu(self)
        menu.setLayoutDirection(Qt.RightToLeft)

        emp_name = row_data.get("full_name", "")
        title_action = menu.addAction(f"👤 {emp_name}")
        title_action.setEnabled(False)
        menu.addSeparator()

        del_action = menu.addAction("🗑️ مسح / حذف هذا السجل أو الموظف نهائياً")
        del_action.triggered.connect(lambda: self.confirm_and_delete_record("ExcludedRecords", row_data))

        view_action = menu.addAction("👁️ عرض بيان حالة الموظف")
        view_action.triggered.connect(lambda: RecordDetailsDialog(row_data, record_type="excluded", db_manager=self.db, parent=self).exec())

        menu.addSeparator()

        copy_name = menu.addAction("📋 نسخ اسم الموظف")
        copy_name.triggered.connect(lambda: QApplication.clipboard().setText(str(emp_name)))

        copy_nid = menu.addAction("📋 نسخ الرقم القومي")
        copy_nid.triggered.connect(lambda: QApplication.clipboard().setText(str(row_data.get("national_id") or "")))

        menu.exec(self.excluded_table.viewport().mapToGlobal(pos))

    def on_prisoner_context_menu(self, pos):
        index = self.prisoners_table.indexAt(pos)
        if not index.isValid():
            return
        row_data = self.prisoners_model.get_row(index.row())
        if not row_data:
            return

        menu = QMenu(self)
        menu.setLayoutDirection(Qt.RightToLeft)

        emp_name = row_data.get("full_name", "")
        title_action = menu.addAction(f"👤 {emp_name}")
        title_action.setEnabled(False)
        menu.addSeparator()

        del_action = menu.addAction("🗑️ مسح / حذف هذا السجل أو الموظف نهائياً")
        del_action.triggered.connect(lambda: self.confirm_and_delete_record("PrisonerRecords", row_data))

        view_action = menu.addAction("👁️ عرض بيان حالة الموظف")
        view_action.triggered.connect(lambda: RecordDetailsDialog(row_data, record_type="prisoners", db_manager=self.db, parent=self).exec())

        menu.addSeparator()

        copy_name = menu.addAction("📋 نسخ اسم الموظف")
        copy_name.triggered.connect(lambda: QApplication.clipboard().setText(str(emp_name)))

        copy_nid = menu.addAction("📋 نسخ الرقم القومي")
        copy_nid.triggered.connect(lambda: QApplication.clipboard().setText(str(row_data.get("national_id") or "")))

        menu.exec(self.prisoners_table.viewport().mapToGlobal(pos))

    def export_search_results(self):
        """Exports the results of both search tabs to a single multi-sheet Excel file."""
        ex_data = self.excluded_model._data
        pr_data = self.prisoners_model._data

        if not ex_data and not pr_data:
            QMessageBox.warning(self, "تنبيه", "لا توجد نتائج بحث ظاهرة لتصديرها.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ نتائج البحث في ملف إكسيل", 
            "نتائج_البحث_الشامل.xlsx", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                if ex_data:
                    df_ex = pd.DataFrame([{
                        "م": r.get("record_number") or (i + 1),
                        "الاسم": r.get("full_name"),
                        "الرقم القومي": r.get("national_id") or "0",
                        "الإدارة التعليمية": r.get("administration_name"),
                        "المدرسة / جهة العمل": r.get("school"),
                        "الوظيفة الحالية": r.get("current_job"),
                        "الوظيفة المرشح لها": r.get("nominee_job"),
                        "جهة الاستبعاد": r.get("exclusion_entity"),
                        "تاريخ الاستبعاد": r.get("exclusion_date"),
                        "نوع القضية": r.get("case_type_name"),
                        "سبب الاستبعاد": r.get("exclusion_reason"),
                        "الهاتف": r.get("phone")
                    } for i, r in enumerate(ex_data)])
                    df_ex.to_excel(writer, sheet_name="سجلات المستبعدين", index=False)

                if pr_data:
                    df_pr = pd.DataFrame([{
                        "م": r.get("record_number") or (i + 1),
                        "الاسم": r.get("full_name"),
                        "الرقم القومي": r.get("national_id") or "0",
                        "الإدارة التعليمية": r.get("administration_name"),
                        "المدرسة / جهة العمل": r.get("school"),
                        "نوع القضية": r.get("case_type_name"),
                        "رقم القضية": r.get("case_number"),
                        "الحكم القضائي": r.get("court_ruling"),
                        "الموقف الحالي": r.get("current_status"),
                        "تاريخ الإفراج": r.get("release_date"),
                        "محل الإقامة": r.get("housing_location"),
                        "الهاتف": r.get("phone")
                    } for i, r in enumerate(pr_data)])
                    df_pr.to_excel(writer, sheet_name="سجلات المسجونين", index=False)

            QMessageBox.information(
                self, "✅ تم التصدير بنجاح", 
                f"تم حفظ نتائج البحث ({len(ex_data)} مستبعد، {len(pr_data)} مسجون) في الملف:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر حفظ ملف Excel:\n{str(e)}")
