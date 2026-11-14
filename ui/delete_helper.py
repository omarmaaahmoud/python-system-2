"""
Delete Helper Module — Provides smart, comprehensive deletion dialogs
that handle single record deletion as well as complete employee purges across all sheets.
"""
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QMessageBox, QWidget, QTableView
)
from PySide6.QtCore import Qt, Signal
from config import PALETTE
from database import DatabaseManager


class KeyCatchingTableView(QTableView):
    """QTableView subclass that catches the keyboard Delete key to delete selected rows."""
    delete_requested = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_requested.emit()
        else:
            super().keyPressEvent(event)


class MultiRecordDeleteDialog(QDialog):
    """Dialog shown when an employee has multiple records (e.g. duplicate or in both tables)."""
    
    ACTION_CANCEL = 0
    ACTION_DELETE_ALL = 1
    ACTION_DELETE_SINGLE = 2

    def __init__(self, parent: Optional[QWidget], info: Dict[str, Any], current_table_name: str):
        super().__init__(parent)
        self.info = info
        self.current_table_name = current_table_name
        self.chosen_action = self.ACTION_CANCEL
        self.setWindowTitle("⚠️ تنبيه: خيارات حذف سجلات الموظف")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedWidth(520)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Frame
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #FEF2F2;
                border: 1.5px solid #FCA5A5;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        h_layout = QVBoxLayout(header)
        h_layout.setSpacing(6)

        title = QLabel("⚠️ الموظف مسجل له أكثر من سجل في النظام!")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #991B1B; border: none;")
        h_layout.addWidget(title)

        emp_name = self.info.get("name", "")
        nid = self.info.get("national_id", "")
        details_txt = f"• الاسم: {emp_name}\n• الرقم القومي: {nid if nid and nid != '0' else 'بدون رقم قومي (0)'}"
        details_lbl = QLabel(details_txt)
        details_lbl.setStyleSheet("font-size: 13px; color: #1E293B; font-weight: 600; border: none;")
        h_layout.addWidget(details_lbl)

        # Counts Breakdown
        ex_cnt = self.info.get("excluded", 0)
        pr_cnt = self.info.get("prisoners", 0)
        tot = self.info.get("total", 0)
        counts_txt = (
            f"إجمالي السجلات المسجلة لهذا الموظف: ({tot}) سجلات:\n"
            f"  - سجلات المستبعدين: {ex_cnt}\n"
            f"  - سجلات المسجونين والقضايا: {pr_cnt}"
        )
        counts_lbl = QLabel(counts_txt)
        counts_lbl.setStyleSheet("font-size: 12px; color: #475569; border: none; padding-top: 4px;")
        h_layout.addWidget(counts_lbl)

        layout.addWidget(header)

        # Prompt question
        q_lbl = QLabel("ما هو الإجراء الذي تريد اتخاذه الآن؟")
        q_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #0F172A;")
        layout.addWidget(q_lbl)

        # Button 1: Delete All (Purge)
        btn_all = QPushButton("❌  حذف الموظف نهائياً بجميع سجلاته من النظام (مستبعدين ومسجونين)")
        btn_all.setObjectName("DangerBtn")
        btn_all.setMinimumHeight(44)
        btn_all.setStyleSheet("""
            QPushButton#DangerBtn {
                background-color: #DC2626; color: white; font-weight: bold; font-size: 13px;
                border-radius: 8px; border: none; padding: 10px 14px; text-align: right;
            }
            QPushButton#DangerBtn:hover { background-color: #B91C1C; }
        """)
        btn_all.clicked.connect(self._choose_all)
        layout.addWidget(btn_all)

        sub_all = QLabel("💡 سيتم مسح الموظف تماماً من قاعدة البيانات والشيت ولن يظهر في أي شاشة أو قائمة.")
        sub_all.setStyleSheet("font-size: 11px; color: #64748B; margin-bottom: 6px; padding-right: 10px;")
        layout.addWidget(sub_all)

        # Button 2: Delete Single Record
        tbl_label = "قرار الاستبعاد الحالي فقط" if self.current_table_name == "ExcludedRecords" else "سجل القضية الحالي فقط"
        btn_single = QPushButton(f"🗑️  حذف {tbl_label}")
        btn_single.setObjectName("SecondaryBtn")
        btn_single.setMinimumHeight(42)
        btn_single.setStyleSheet("""
            QPushButton#SecondaryBtn {
                background-color: #F1F5F9; color: #334155; font-weight: bold; font-size: 13px;
                border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px 14px; text-align: right;
            }
            QPushButton#SecondaryBtn:hover { background-color: #E2E8F0; }
        """)
        btn_single.clicked.connect(self._choose_single)
        layout.addWidget(btn_single)

        sub_single = QLabel("💡 سيتم حذف السجل الحالي فقط مع الإبقاء على باقي سجلات الموظف الأخرى كما هي.")
        sub_single.setStyleSheet("font-size: 11px; color: #64748B; margin-bottom: 6px; padding-right: 10px;")
        layout.addWidget(sub_single)

        # Cancel Button
        btn_cancel = QPushButton("إلغاء الأمر")
        btn_cancel.setMinimumHeight(38)
        btn_cancel.setStyleSheet("""
            background: transparent; color: #64748B; border: 1px solid #E2E8F0;
            border-radius: 6px; font-size: 12px;
        """)
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

    def _choose_all(self):
        self.chosen_action = self.ACTION_DELETE_ALL
        self.accept()

    def _choose_single(self):
        self.chosen_action = self.ACTION_DELETE_SINGLE
        self.accept()


def prompt_smart_delete(
    parent: QWidget, 
    db: DatabaseManager, 
    table_name: str, 
    row_data: Dict[str, Any]
) -> bool:
    """
    Executes a smart deletion workflow:
    - Checks if the employee has multiple records.
    - If multiple records: gives the user a clear choice to delete all records or just this one.
    - If single record: asks for standard confirmation.
    - Cleans up orphan employee if single record is removed.
    - Returns True if any deletion occurred, False if cancelled.
    """
    rec_id = row_data.get("id")
    if not rec_id:
        QMessageBox.warning(parent, "تنبيه", "تعذر تحديد معرّف السجل المراد حذفه.")
        return False

    emp_id = row_data.get("employee_id")
    if not emp_id:
        # Fetch employee_id from DB
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(f"SELECT employee_id FROM {table_name} WHERE id = ?;", (rec_id,))
                r = cur.fetchone()
                if r:
                    emp_id = r["employee_id"]
        except Exception:
            pass

    # If we have an employee_id, check their total records across all tables
    emp_info = None
    if emp_id:
        try:
            emp_info = db.get_employee_records_count(emp_id)
        except Exception:
            emp_info = None

    full_name = row_data.get("full_name") or (emp_info.get("name") if emp_info else "الموظف المحدد")

    # Case 1: Multiple records exist for this employee
    if emp_info and emp_info.get("total", 0) > 1:
        dlg = MultiRecordDeleteDialog(parent, emp_info, table_name)
        if dlg.exec() != QDialog.Accepted or dlg.chosen_action == MultiRecordDeleteDialog.ACTION_CANCEL:
            return False

        if dlg.chosen_action == MultiRecordDeleteDialog.ACTION_DELETE_ALL:
            try:
                db.delete_employee_completely(emp_id)
                QMessageBox.information(
                    parent,
                    "✅ تم الحذف النهائي",
                    f"تم مسح الموظف «{full_name}» وجميع سجلاته ({emp_info['total']} سجل) نهائياً من الشيت والنظام."
                )
                return True
            except Exception as e:
                QMessageBox.critical(parent, "خطأ", f"تعذر حذف الموظف: {str(e)}")
                return False

        elif dlg.chosen_action == MultiRecordDeleteDialog.ACTION_DELETE_SINGLE:
            try:
                db.delete_record(table_name, rec_id, delete_orphan_employee=False)
                rem = emp_info["total"] - 1
                QMessageBox.information(
                    parent,
                    "✅ تم مسح السجل",
                    f"تم مسح هذا السجل فقط للموظف «{full_name}».\n(متبقي له {rem} سجل في النظام)."
                )
                return True
            except Exception as e:
                QMessageBox.critical(parent, "خطأ", f"تعذر حذف السجل: {str(e)}")
                return False

    # Case 2: Only 1 record (or employee_id unknown)
    table_label = "قرار الاستبعاد" if table_name == "ExcludedRecords" else "سجل المسجون / القضية"
    reply = QMessageBox.question(
        parent,
        "تأكيد الحذف النهائي",
        f"هل أنت متأكد من مسح وحذف {table_label} الخاص بالموظف:\n«{full_name}»\nنهائياً من قاعدة البيانات والشيت؟",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    if reply != QMessageBox.Yes:
        return False

    try:
        if emp_id:
            # Purge completely so both record and employee are cleaned
            db.delete_employee_completely(emp_id)
        else:
            db.delete_record(table_name, rec_id, delete_orphan_employee=True)

        QMessageBox.information(
            parent,
            "✅ تم المسح بنجاح",
            f"تم مسح سجل «{full_name}» نهائياً من قاعدة البيانات والشيت."
        )
        return True
    except Exception as e:
        QMessageBox.critical(parent, "خطأ", f"تعذر حذف السجل: {str(e)}")
        return False
