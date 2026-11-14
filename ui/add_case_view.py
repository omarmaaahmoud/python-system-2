"""
Manage Case Types View — allows the user to:
  • See all existing case types in a table
  • Add a new case type name (it appears in all dropdowns across the app)
  • Delete a case type
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QMenu, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from config import PALETTE
from database import DatabaseManager


class ManageCaseTypesView(QWidget):
    """Page for adding / viewing / deleting case types."""
    data_changed_signal = Signal()

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 22, 24, 24)

        # ---------- Page Title ----------
        title = QLabel("📋  إدارة أنواع القضايا والمخالفات")
        title.setStyleSheet(f"""
            font-size: 20px; font-weight: bold;
            color: {PALETTE['primary_dark']};
            padding-bottom: 2px;
        """)
        main_layout.addWidget(title)

        subtitle = QLabel("أضف نوع قضية جديد وسيظهر تلقائياً في جميع القوائم المنسدلة بالبرنامج (سجلات المستبعدين، المسجونين، والبحث الشامل).")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 13px; color: #64748B; margin-bottom: 4px;")
        main_layout.addWidget(subtitle)

        # ---------- Add new case type card ----------
        add_card = QFrame()
        add_card.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['surface']};
                border: 1px solid {PALETTE['border_light']};
                border-radius: 12px;
                padding: 14px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        add_layout = QHBoxLayout(add_card)
        add_layout.setSpacing(12)

        add_icon = QLabel("➕")
        add_icon.setStyleSheet("font-size: 22px; border: none;")
        add_icon.setFixedWidth(30)
        add_layout.addWidget(add_icon)

        add_label = QLabel("اسم نوع القضية الجديدة:")
        add_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #334155; border: none;")
        add_label.setFixedWidth(170)
        add_layout.addWidget(add_label)

        self.new_case_input = QLineEdit()
        self.new_case_input.setPlaceholderText("مثال: تزوير في محرر رسمي، إتلاف ممتلكات عامة...")
        self.new_case_input.setMinimumHeight(42)
        self.new_case_input.setStyleSheet("""
            background-color: #FFFFFF; color: #0F172A;
            border: 1.5px solid #CBD5E1; border-radius: 8px;
            padding: 6px 14px; font-size: 14px;
        """)
        self.new_case_input.returnPressed.connect(self.add_case_type)
        add_layout.addWidget(self.new_case_input, 1)

        add_btn = QPushButton("➕  إضافة نوع قضية")
        add_btn.setObjectName("PrimaryBtn")
        add_btn.setMinimumHeight(42)
        add_btn.setMinimumWidth(160)
        add_btn.clicked.connect(self.add_case_type)
        add_layout.addWidget(add_btn)

        main_layout.addWidget(add_card)

        # ---------- Toolbar ----------
        toolbar = QHBoxLayout()

        self.count_label = QLabel("إجمالي أنواع القضايا: 0")
        self.count_label.setStyleSheet(f"""
            font-weight: bold; color: {PALETTE['primary']};
            background: #EFF6FF; border: 1px solid #BFDBFE;
            border-radius: 6px; padding: 6px 14px; font-size: 13px;
        """)
        toolbar.addWidget(self.count_label)

        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)

        main_layout.addLayout(toolbar)

        # ---------- Table of existing case types ----------
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["#", "اسم نوع القضية / المخالفة", "عدد السجلات المرتبطة"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 160)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_context_menu)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                gridline-color: #F1F5F9;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px 12px;
            }
            QTableWidget::item:selected {
                background-color: #DBEAFE;
                color: #1E3A8A;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                color: #334155;
                font-weight: bold;
                font-size: 13px;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #E2E8F0;
            }
        """)
        main_layout.addWidget(self.table, 1)

    # -------------------------------------------------------- Data
    def load_data(self):
        """Load all case types with their record counts."""
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT ct.id, ct.name,
                    (SELECT COUNT(*) FROM ExcludedRecords er WHERE er.case_type_id = ct.id) +
                    (SELECT COUNT(*) FROM PrisonerRecords pr WHERE pr.case_type_id = ct.id) AS total_records
                FROM CaseTypes ct
                ORDER BY ct.name ASC;
            """)
            rows = cur.fetchall()
            conn.close()

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                # #
                num_item = QTableWidgetItem(str(i + 1))
                num_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, num_item)

                # Name
                name_item = QTableWidgetItem(str(row["name"]))
                name_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                name_item.setData(Qt.UserRole, row["id"])  # Store id for deletion
                self.table.setItem(i, 1, name_item)

                # Count
                cnt = row["total_records"]
                cnt_item = QTableWidgetItem(f"{cnt:,}")
                cnt_item.setTextAlignment(Qt.AlignCenter)
                if cnt > 0:
                    cnt_item.setForeground(Qt.darkGreen)
                else:
                    cnt_item.setForeground(Qt.gray)
                self.table.setItem(i, 2, cnt_item)

            self.count_label.setText(f"إجمالي أنواع القضايا المسجلة: {len(rows)}")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر تحميل أنواع القضايا:\n{str(e)}")

    def add_case_type(self):
        """Add a new case type."""
        name = self.new_case_input.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة اسم نوع القضية أولاً.")
            self.new_case_input.setFocus()
            return

        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            # Check if already exists
            cur.execute("SELECT id FROM CaseTypes WHERE name = ? COLLATE NOCASE;", (name,))
            existing = cur.fetchone()
            if existing:
                conn.close()
                QMessageBox.warning(self, "تنبيه", f"نوع القضية «{name}» موجود بالفعل في قاعدة البيانات.")
                self.new_case_input.selectAll()
                self.new_case_input.setFocus()
                return

            cur.execute("INSERT INTO CaseTypes (name) VALUES (?);", (name,))
            conn.commit()
            conn.close()

            QMessageBox.information(
                self, "✅ تم الإضافة بنجاح",
                f"تم إضافة نوع القضية:\n«{name}»\nوسيظهر الآن في جميع القوائم المنسدلة بالبرنامج."
            )

            self.new_case_input.clear()
            self.load_data()
            self.data_changed_signal.emit()

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر إضافة نوع القضية:\n{str(e)}")

    def on_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        name_item = self.table.item(row, 1)
        if not name_item:
            return

        ct_name = name_item.text()
        ct_id = name_item.data(Qt.UserRole)

        menu = QMenu(self)
        menu.setLayoutDirection(Qt.RightToLeft)

        title_action = menu.addAction(f"📋 {ct_name}")
        title_action.setEnabled(False)
        menu.addSeparator()

        del_action = menu.addAction("🗑️ حذف نوع القضية نهائياً")
        del_action.triggered.connect(lambda: self.confirm_delete(ct_id, ct_name))

        copy_action = menu.addAction("📋 نسخ اسم القضية")
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(ct_name))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def confirm_delete(self, ct_id: int, ct_name: str):
        # Check if case type has records
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM ExcludedRecords WHERE case_type_id = ?) +
                    (SELECT COUNT(*) FROM PrisonerRecords WHERE case_type_id = ?) AS cnt;
            """, (ct_id, ct_id))
            cnt = cur.fetchone()["cnt"]
            conn.close()

            if cnt > 0:
                QMessageBox.warning(
                    self, "تحذير",
                    f"لا يمكن حذف نوع القضية «{ct_name}»\nلأنها مرتبطة بـ {cnt} سجل.\n\nيجب حذف السجلات المرتبطة أولاً."
                )
                return

        except Exception:
            pass

        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل أنت متأكد من حذف نوع القضية:\n«{ct_name}»\nنهائياً من قاعدة البيانات؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                conn = self.db.get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM CaseTypes WHERE id = ?;", (ct_id,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "تم الحذف", f"تم حذف نوع القضية «{ct_name}» بنجاح.")
                self.load_data()
                self.data_changed_signal.emit()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر حذف نوع القضية:\n{str(e)}")

    def refresh_combos(self):
        """Compatibility — reload data."""
        self.load_data()
