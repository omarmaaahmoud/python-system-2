from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QPushButton, QTableView, QHeaderView, QMessageBox, 
    QFileDialog, QFrame, QMenu, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer
import pandas as pd
from config import PALETTE
from database import DatabaseManager
from ui.table_models import EmployeesTableModel
from ui.record_dialog import AddEmployeeDialog

class EmployeesView(QWidget):
    """Basic Data / Educational Personnel Directory View."""
    data_changed_signal = Signal()

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.model = EmployeesTableModel([])
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

        # Filter Card
        filter_card = QFrame()
        filter_card.setStyleSheet(f"""
            QFrame {{ background-color: {PALETTE['surface']}; border: 1px solid {PALETTE['border_light']}; border-radius: 10px; padding: 10px; }}
            QLabel {{ border: none; }}
        """)
        filter_layout = QHBoxLayout(filter_card)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث سريع بالاسم، الرقم القومي، جهة العمل، أو الإدارة...")
        self.search_input.textChanged.connect(self.search_timer.start)
        self.search_input.returnPressed.connect(self.load_data)
        filter_layout.addWidget(self.search_input, 3)

        self.admin_filter = QComboBox()
        self.admin_filter.addItem("جميع الإدارات التعليمية", None)
        for adm in self.db.get_administrations():
            self.admin_filter.addItem(adm["name"], adm["id"])
        self.admin_filter.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.admin_filter, 2)

        clear_btn = QPushButton("مسح التصفية")
        clear_btn.setObjectName("SecondaryBtn")
        clear_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_btn)

        main_layout.addWidget(filter_card)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.count_badge = QLabel("إجمالي العاملين: 0")
        self.count_badge.setStyleSheet(f"font-weight: bold; color: {PALETTE['primary']}; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 6px 12px;")
        toolbar_layout.addWidget(self.count_badge)

        toolbar_layout.addStretch()

        add_btn = QPushButton("➕ إضافة موظف جديد")
        add_btn.setObjectName("SecondaryBtn")
        add_btn.clicked.connect(self.open_add_dialog)
        toolbar_layout.addWidget(add_btn)

        export_btn = QPushButton("📊 تصدير إلى Excel")
        export_btn.setObjectName("SecondaryBtn")
        export_btn.clicked.connect(self.export_to_excel)
        toolbar_layout.addWidget(export_btn)

        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self.load_data)
        toolbar_layout.addWidget(refresh_btn)

        main_layout.addLayout(toolbar_layout)

        # Table
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._set_column_widths()
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.on_table_context_menu)
        main_layout.addWidget(self.table_view)

    def _set_column_widths(self):
        widths = [50, 240, 140, 140, 180, 100, 110, 110]
        for idx, w in enumerate(widths):
            self.table_view.setColumnWidth(idx, w)

    def load_data(self):
        self.search_timer.stop()
        query = self.search_input.text().strip()
        admin_id = self.admin_filter.currentData()
        employees = self.db.search_employees(query=query, admin_id=admin_id, limit=2000)
        self.model.update_data(employees)
        self.count_badge.setText(f"إجمالي الموظفين المسجلين: {len(employees):,}")

    def clear_filters(self):
        self.search_input.clear()
        self.admin_filter.setCurrentIndex(0)
        self.load_data()

    def open_add_dialog(self):
        dlg = AddEmployeeDialog(self.db, self)
        if dlg.exec():
            self.load_data()
            self.data_changed_signal.emit()

    def on_table_context_menu(self, pos):
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

        del_action = menu.addAction("🗑️ مسح / حذف بيانات هذا الموظف نهائياً")
        del_action.triggered.connect(lambda: self.confirm_and_delete_employee(row_data))

        menu.addSeparator()

        copy_name = menu.addAction("📋 نسخ اسم الموظف")
        copy_name.triggered.connect(lambda: QApplication.clipboard().setText(str(emp_name)))

        copy_nid = menu.addAction("📋 نسخ الرقم القومي")
        copy_nid.triggered.connect(lambda: QApplication.clipboard().setText(str(row_data.get("national_id") or "")))

        menu.exec(self.table_view.viewport().mapToGlobal(pos))

    def confirm_and_delete_employee(self, row_data: dict):
        emp_name = row_data.get("full_name", "")
        reply = QMessageBox.question(
            self,
            "تأكيد مسح الموظف",
            f"تحذير: هل أنت متأكد من مسح الموظف:\n«{emp_name}»\nوجميع سجلاته المرتبطة به نهائياً من قاعدة البيانات؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_record("Employees", row_data["id"])
                QMessageBox.information(self, "تم المسح", f"تم مسح بيانات «{emp_name}» بنجاح.")
                self.load_data()
                self.data_changed_signal.emit()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر حذف الموظف: {str(e)}")

    def export_to_excel(self):
        if not self.model._data:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات ظاهرة في الجدول لتصديرها.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "تصدير البيانات الأساسية إلى Excel",
            "قاعدة_بيانات_العاملين_بالمديرية.xlsx",
            "Excel Files (*.xlsx)"
        )
        if save_path:
            try:
                df = pd.DataFrame(self.model._data)
                rename_map = {
                    "full_name": "الاسم رباعي",
                    "national_id": "الرقم القومي",
                    "administration_name": "الإدارة التعليمية",
                    "school": "جهة العمل / المدرسة",
                    "phone": "رقم الهاتف",
                    "excluded_count": "عدد قرارات الاستبعاد",
                    "prisoner_count": "عدد قضايا الحبس"
                }
                export_cols = [k for k in rename_map.keys() if k in df.columns]
                df = df[export_cols].rename(columns=rename_map)
                df.to_excel(save_path, index=False, engine="openpyxl")
                QMessageBox.information(self, "نجاح التصدير", f"تم تصدير {len(df)} موظف بنجاح إلى:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر تصدير الملف: {str(e)}")
