# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QTextEdit, QPushButton, QDateEdit, QMessageBox, 
    QFormLayout, QGroupBox, QFrame, QFileDialog, QScrollArea, QWidget
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QDate
from config import PALETTE, PRISONER_STATUSES, LOGO_PATH
from database import DatabaseManager
from ui.delete_helper import prompt_smart_delete

EDIT_DIALOG_STYLE = """
    QDialog {
        background-color: #FFFFFF;
        color: #0F172A;
    }
    QScrollArea {
        background-color: #FFFFFF;
        border: none;
    }
    QWidget#ScrollContent {
        background-color: #FFFFFF;
    }
    QGroupBox {
        font-weight: bold;
        font-size: 13px;
        color: #1E40AF;
        border: 1.5px solid #93C5FD;
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 16px;
        background-color: #FFFFFF;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top right;
        padding: 0 8px;
        background-color: #FFFFFF;
        color: #1E40AF;
        font-weight: bold;
    }
    QLineEdit, QComboBox, QDateEdit, QTextEdit {
        background-color: #FFFFFF;
        color: #0F172A;
        border: 1.5px solid #93C5FD;
        border-radius: 6px;
        padding: 7px 10px;
        font-size: 13px;
        font-family: 'Segoe UI', Tahoma, Arial;
    }
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {
        border: 2px solid #2563EB;
        background-color: #FFFFFF;
    }
    /* QCalendarWidget Fix */
    QCalendarWidget {
        background-color: #FFFFFF;
        border: 1.5px solid #93C5FD;
        border-radius: 8px;
    }
    QCalendarWidget QWidget#qt_calendar_navigationbar {
        background-color: #1E40AF;
        min-height: 38px;
        border-top-left-radius: 7px;
        border-top-right-radius: 7px;
    }
    QCalendarWidget QToolButton {
        color: #FFFFFF;
        background-color: transparent;
        border: none;
        border-radius: 4px;
        font-size: 13px;
        font-weight: bold;
        padding: 4px 8px;
    }
    QCalendarWidget QToolButton:hover {
        background-color: #2563EB;
    }
    QCalendarWidget QHeaderView::section {
        background-color: #F1F5F9;
        color: #475569;
        font-size: 11px;
        font-weight: bold;
        padding: 3px 0px;
        border: none;
        border-bottom: 1px solid #CBD5E1;
    }
    QCalendarWidget QTableView,
    QCalendarWidget QTableView#qt_calendar_calendarview {
        background-color: #FFFFFF;
        border: none;
        selection-background-color: #2563EB;
        selection-color: #FFFFFF;
        outline: none;
    }
    QCalendarWidget QTableView::item,
    QCalendarWidget QTableView#qt_calendar_calendarview::item,
    QCalendarWidget QAbstractItemView::item {
        padding: 1px 0px;
        margin: 0px;
        border: none;
        border-bottom: none;
        font-size: 12px;
        font-weight: 500;
    }
    QCalendarWidget QTableView::item:hover,
    QCalendarWidget QTableView#qt_calendar_calendarview::item:hover,
    QCalendarWidget QAbstractItemView::item:hover {
        background-color: #EFF6FF;
        border-radius: 4px;
    }
    QCalendarWidget QTableView::item:selected,
    QCalendarWidget QTableView#qt_calendar_calendarview::item:selected,
    QCalendarWidget QAbstractItemView::item:selected {
        background-color: #2563EB;
        color: #FFFFFF;
        border-radius: 4px;
    }
"""

class AddExcludedDialog(QDialog):
    """Dialog to manually register a new Excluded Personnel record."""
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("إضافة قرار استبعاد جديد")
        self.resize(540, 580)
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("تسجيل استبعاد موظف / معلم جديد")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {PALETTE['primary']};")
        layout.addWidget(title)

        # Employee info group
        emp_group = QGroupBox("بيانات الموظف الأساسية")
        emp_form = QFormLayout(emp_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("الاسم رباعي كما في بطاقة الرقم القومي")
        self.name_input.textChanged.connect(self.check_duplicate_live)
        emp_form.addRow("الاسم الكامل *:", self.name_input)

        self.dup_warning_label = QLabel()
        self.dup_warning_label.setWordWrap(True)
        self.dup_warning_label.setStyleSheet("color: #991B1B; background-color: #FEF2F2; border: 1.5px solid #F87171; border-radius: 6px; padding: 6px 10px; font-size: 12px; font-weight: bold;")
        self.dup_warning_label.hide()
        emp_form.addRow("", self.dup_warning_label)

        self.nid_input = QLineEdit()
        self.nid_input.setPlaceholderText("14 رقم قومي")
        self.nid_input.setMaxLength(14)
        self.nid_input.textChanged.connect(self.check_duplicate_live)
        emp_form.addRow("الرقم القومي *:", self.nid_input)

        self.admin_combo = QComboBox()
        self.admin_combo.addItem("غير محدد", None)
        for adm in self.db.get_administrations():
            self.admin_combo.addItem(adm["name"], adm["id"])
        emp_form.addRow("الإدارة التعليمية:", self.admin_combo)

        self.school_input = QLineEdit()
        self.school_input.setPlaceholderText("اسم المدرسة أو الإدارة التابع لها")
        emp_form.addRow("جهة العمل / المدرسة:", self.school_input)

        layout.addWidget(emp_group)

        # Exclusion details group
        ex_group = QGroupBox("بيانات وقرار الاستبعاد")
        ex_form = QFormLayout(ex_group)

        self.current_job_input = QLineEdit()
        self.current_job_input.setPlaceholderText("مثال: معلم أول أ لغة عربية")
        ex_form.addRow("الوظيفة الحالية:", self.current_job_input)

        self.nominee_job_input = QLineEdit()
        self.nominee_job_input.setPlaceholderText("الوظيفة المرشح لها أو المنقول إليها")
        ex_form.addRow("الوظيفة المرشح لها:", self.nominee_job_input)

        self.case_type_combo = QComboBox()
        self.case_type_combo.addItem("غير محدد", None)
        for ct in self.db.get_case_types():
            self.case_type_combo.addItem(ct["name"], ct["id"])
        ex_form.addRow("نوع القضية / المخالفة:", self.case_type_combo)

        self.entity_input = QLineEdit()
        self.entity_input.setPlaceholderText("مثال: الأمن القومي / النيابة الإدارية / التفتيش")
        ex_form.addRow("جهة الاستبعاد:", self.entity_input)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        ex_form.addRow("تاريخ القرار / الاستبعاد:", self.date_input)

        self.reason_input = QTextEdit()
        self.reason_input.setFixedHeight(75)
        self.reason_input.setStyleSheet("background-color: #FFFFFF; color: #0F172A; border: 1.5px solid #CBD5E1; border-radius: 6px; padding: 6px; font-size: 13px;")
        self.reason_input.setPlaceholderText("تفاصيل وحيثيات سبب الاستبعاد...")
        ex_form.addRow("سبب الاستبعاد:", self.reason_input)

        layout.addWidget(ex_group)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 حفظ القرار")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self.save_record)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def check_duplicate_live(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip()
        has_nid = bool(nid and nid != "0" and not nid.startswith("مؤقت") and len(nid) >= 6)
        if len(name) >= 3 or has_nid:
            matches = self.db.check_duplicate_employee(name, nid)
            if matches:
                m = matches[0]
                status_list = []
                if m.get("exclusions"):
                    status_list.append(f"{len(m['exclusions'])} قرار استبعاد")
                if m.get("prisoners"):
                    status_list.append(f"{len(m['prisoners'])} قضية حبس")
                status_text = f" ({' و '.join(status_list)})" if status_list else ""

                matched_nid = str(m.get("national_id", "")).strip()
                if not matched_nid or matched_nid in ["0", "None", "nan"] or matched_nid.startswith("مؤقت"):
                    nid_str = "القومي: غير مسجل"
                else:
                    nid_str = f"القومي: {matched_nid}"

                match_type = "الاسم والرقم القومي" if (has_nid and (matched_nid == nid or matched_nid.startswith(nid)) and len(name) >= 3) else ("الرقم القومي" if (has_nid and (matched_nid == nid or matched_nid.startswith(nid))) else "الاسم")

                self.dup_warning_label.setText(
                    f"⚠️ إنذار تشابه ({match_type})! [{m['full_name']} | {nid_str} | إدارة: {m['administration_name']} - {m['school']}]{status_text}"
                )
                self.dup_warning_label.show()
                return
        self.dup_warning_label.hide()

    def save_record(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip() or "0"

        if not name:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الموظف على الأقل.")
            return

        # Check for duplicate employee warning
        matches = self.db.check_duplicate_employee(name, nid)
        if matches:
            m = matches[0]
            matched_nid = str(m.get("national_id", "")).strip()
            if not matched_nid or matched_nid in ["0", "None", "nan"]:
                matched_nid = "غير مسجل"
            details = [
                f"• الاسم: {m['full_name']}",
                f"• الرقم القومي: {matched_nid}",
                f"• الإدارة التعليمية: {m['administration_name']}",
                f"• جهة العمل: {m['school']}"
            ]
            if m.get("exclusions"):
                details.append(f"• قرارات الاستبعاد المسجلة له: {len(m['exclusions'])} قرار")
            if m.get("prisoners"):
                details.append(f"• قضايا الحبس المسجلة له: {len(m['prisoners'])} قضية")

            msg = "⚠️ إنذار: تم العثور على تشابه في بيانات الموظف (الاسم أو الرقم القومي)!\n\n"
            msg += "\n".join(details) + "\n\n"
            msg += "هل تريد بالتأكيد الاستمرار وحفظ هذا السجل لنفس الاسم/الموظف؟"

            reply = QMessageBox.question(
                self, "إنذار تشابه بيانات الموظف",
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        data = {
            "full_name": name,
            "national_id": nid,
            "administration_id": self.admin_combo.currentData(),
            "school": self.school_input.text().strip(),
            "phone": "",
            "current_job": self.current_job_input.text().strip(),
            "nominee_job": self.nominee_job_input.text().strip(),
            "case_type_id": self.case_type_combo.currentData(),
            "exclusion_entity": self.entity_input.text().strip(),
            "exclusion_date": self.date_input.date().toString("yyyy-MM-dd"),
            "exclusion_reason": self.reason_input.toPlainText().strip()
        }

        try:
            self.db.add_excluded_record(data)
            QMessageBox.information(self, "نجاح", "تم حفظ قرار الاستبعاد بنجاح.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر حفظ السجل: {str(e)}")


class AddPrisonerDialog(QDialog):
    """Dialog to manually register a new Prisoner/Legal Case record."""
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("إضافة سجل مسجون / قضية جنائية")
        self.resize(540, 580)
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("تسجيل بيانات مسجون / متهم في قضية")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {PALETTE['primary']};")
        layout.addWidget(title)

        # Employee info group
        emp_group = QGroupBox("بيانات الموظف الأساسية")
        emp_form = QFormLayout(emp_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("الاسم رباعي")
        self.name_input.textChanged.connect(self.check_duplicate_live)
        emp_form.addRow("الاسم الكامل *:", self.name_input)

        self.dup_warning_label = QLabel()
        self.dup_warning_label.setWordWrap(True)
        self.dup_warning_label.setStyleSheet("color: #991B1B; background-color: #FEF2F2; border: 1.5px solid #F87171; border-radius: 6px; padding: 6px 10px; font-size: 12px; font-weight: bold;")
        self.dup_warning_label.hide()
        emp_form.addRow("", self.dup_warning_label)

        self.nid_input = QLineEdit()
        self.nid_input.setPlaceholderText("الرقم القومي")
        self.nid_input.setMaxLength(14)
        self.nid_input.textChanged.connect(self.check_duplicate_live)
        emp_form.addRow("الرقم القومي *:", self.nid_input)

        self.admin_combo = QComboBox()
        self.admin_combo.addItem("غير محدد", None)
        for adm in self.db.get_administrations():
            self.admin_combo.addItem(adm["name"], adm["id"])
        emp_form.addRow("الإدارة التعليمية:", self.admin_combo)

        self.school_input = QLineEdit()
        self.school_input.setPlaceholderText("المدرسة / جهة العمل")
        emp_form.addRow("جهة العمل:", self.school_input)

        layout.addWidget(emp_group)

        # Prisoner details group
        pr_group = QGroupBox("بيانات القضية والحبس")
        pr_form = QFormLayout(pr_group)

        self.case_number_input = QLineEdit()
        self.case_number_input.setPlaceholderText("مثال: جنايات شرق 1245 لسنة 2023")
        pr_form.addRow("رقم القضية / المحضر:", self.case_number_input)

        self.case_type_combo = QComboBox()
        self.case_type_combo.addItem("غير محدد", None)
        for ct in self.db.get_case_types():
            self.case_type_combo.addItem(ct["name"], ct["id"])
        pr_form.addRow("نوع القضية والتهمة:", self.case_type_combo)

        self.status_combo = QComboBox()
        for st in PRISONER_STATUSES:
            self.status_combo.addItem(st, st)
        pr_form.addRow("الموقف الجنائي الحالي:", self.status_combo)

        self.court_ruling_input = QTextEdit()
        self.court_ruling_input.setFixedHeight(65)
        self.court_ruling_input.setStyleSheet("background-color: #FFFFFF; color: #0F172A; border: 1.5px solid #CBD5E1; border-radius: 6px; padding: 6px; font-size: 13px;")
        self.court_ruling_input.setPlaceholderText("منطوق حكم المحكمة أو قرار النيابة...")
        pr_form.addRow("منطوق الحكم / القرار:", self.court_ruling_input)

        self.release_date_input = QLineEdit()
        self.release_date_input.setPlaceholderText("مثال: 2028-10-15 أو قيد التحقيق")
        pr_form.addRow("تاريخ الإفراج المتوقع / الفعلي:", self.release_date_input)

        self.housing_input = QLineEdit()
        self.housing_input.setPlaceholderText("مكان التسكين (المدرسة / التوجيه / جهة العمل)")
        pr_form.addRow("مكان التسكين:", self.housing_input)

        layout.addWidget(pr_group)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 حفظ السجل الجنائي")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self.save_record)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def check_duplicate_live(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip()
        has_nid = bool(nid and nid != "0" and not nid.startswith("مؤقت") and len(nid) >= 6)
        if len(name) >= 3 or has_nid:
            matches = self.db.check_duplicate_employee(name, nid)
            if matches:
                m = matches[0]
                status_list = []
                if m.get("exclusions"):
                    status_list.append(f"{len(m['exclusions'])} قرار استبعاد")
                if m.get("prisoners"):
                    status_list.append(f"{len(m['prisoners'])} قضية حبس")
                status_text = f" ({' و '.join(status_list)})" if status_list else ""

                matched_nid = str(m.get("national_id", "")).strip()
                if not matched_nid or matched_nid in ["0", "None", "nan"] or matched_nid.startswith("مؤقت"):
                    nid_str = "القومي: غير مسجل"
                else:
                    nid_str = f"القومي: {matched_nid}"

                match_type = "الاسم والرقم القومي" if (has_nid and (matched_nid == nid or matched_nid.startswith(nid)) and len(name) >= 3) else ("الرقم القومي" if (has_nid and (matched_nid == nid or matched_nid.startswith(nid))) else "الاسم")

                self.dup_warning_label.setText(
                    f"⚠️ إنذار تشابه ({match_type})! [{m['full_name']} | {nid_str} | إدارة: {m['administration_name']} - {m['school']}]{status_text}"
                )
                self.dup_warning_label.show()
                return
        self.dup_warning_label.hide()

    def save_record(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip() or "0"

        if not name:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الموظف على الأقل.")
            return

        # Check for duplicate employee warning
        matches = self.db.check_duplicate_employee(name, nid)
        if matches:
            m = matches[0]
            matched_nid = str(m.get("national_id", "")).strip()
            if not matched_nid or matched_nid in ["0", "None", "nan"]:
                matched_nid = "غير مسجل"
            details = [
                f"• الاسم: {m['full_name']}",
                f"• الرقم القومي: {matched_nid}",
                f"• الإدارة التعليمية: {m['administration_name']}",
                f"• جهة العمل: {m['school']}"
            ]
            if m.get("exclusions"):
                details.append(f"• قرارات الاستبعاد المسجلة له: {len(m['exclusions'])} قرار")
            if m.get("prisoners"):
                details.append(f"• قضايا الحبس المسجلة له: {len(m['prisoners'])} قضية")

            msg = "⚠️ إنذار: تم العثور على تشابه في بيانات الموظف (الاسم أو الرقم القومي)!\n\n"
            msg += "\n".join(details) + "\n\n"
            msg += "هل تريد بالتأكيد الاستمرار وحفظ هذا السجل لنفس الاسم/الموظف؟"

            reply = QMessageBox.question(
                self, "إنذار تشابه بيانات الموظف",
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        data = {
            "full_name": name,
            "national_id": nid,
            "administration_id": self.admin_combo.currentData(),
            "school": self.school_input.text().strip(),
            "phone": "",
            "case_number": self.case_number_input.text().strip(),
            "case_type_id": self.case_type_combo.currentData(),
            "court_ruling": self.court_ruling_input.toPlainText().strip(),
            "current_status": self.status_combo.currentText(),
            "release_date": self.release_date_input.text().strip(),
            "housing_location": self.housing_input.text().strip()
        }

        try:
            self.db.add_prisoner_record(data)
            QMessageBox.information(self, "نجاح", "تم حفظ السجل بنجاح.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر حفظ السجل: {str(e)}")


class AddEmployeeDialog(QDialog):
    """Dialog to manually register a new employee/staff member (No phone number field)."""
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("إضافة موظف / معلم جديد")
        self.resize(500, 360)
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("تسجيل موظف جديد في قاعدة بيانات العاملين")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {PALETTE['primary']};")
        layout.addWidget(title)

        emp_group = QGroupBox("بيانات الموظف الأساسية (بدون رقم هاتف)")
        emp_form = QFormLayout(emp_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("الاسم رباعي كما في بطاقة الرقم القومي")
        self.name_input.textChanged.connect(self.check_duplicate_live)
        emp_form.addRow("الاسم الكامل *:", self.name_input)

        self.dup_warning_label = QLabel()
        self.dup_warning_label.setWordWrap(True)
        self.dup_warning_label.setStyleSheet("color: #991B1B; background-color: #FEF2F2; border: 1.5px solid #F87171; border-radius: 6px; padding: 6px 10px; font-size: 12px; font-weight: bold;")
        self.dup_warning_label.hide()
        emp_form.addRow("", self.dup_warning_label)

        self.nid_input = QLineEdit()
        self.nid_input.setPlaceholderText("14 رقم قومي")
        self.nid_input.setMaxLength(14)
        self.nid_input.textChanged.connect(self.check_duplicate_live)
        emp_form.addRow("الرقم القومي *:", self.nid_input)

        self.admin_combo = QComboBox()
        self.admin_combo.addItem("غير محدد", None)
        for adm in self.db.get_administrations():
            self.admin_combo.addItem(adm["name"], adm["id"])
        emp_form.addRow("الإدارة التعليمية:", self.admin_combo)

        self.school_input = QLineEdit()
        self.school_input.setPlaceholderText("اسم المدرسة أو جهة العمل التابع لها")
        emp_form.addRow("جهة العمل / المدرسة:", self.school_input)

        layout.addWidget(emp_group)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 حفظ بيانات الموظف")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self.save_employee)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def check_duplicate_live(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip()
        has_nid = bool(nid and nid != "0" and not nid.startswith("مؤقت") and len(nid) >= 6)
        if len(name) >= 3 or has_nid:
            matches = self.db.check_duplicate_employee(name, nid)
            if matches:
                m = matches[0]
                status_list = []
                if m.get("exclusions"):
                    status_list.append(f"{len(m['exclusions'])} قرار استبعاد")
                if m.get("prisoners"):
                    status_list.append(f"{len(m['prisoners'])} قضية حبس")
                status_text = f" ({' و '.join(status_list)})" if status_list else ""

                matched_nid = str(m.get("national_id", "")).strip()
                if not matched_nid or matched_nid in ["0", "None", "nan"] or matched_nid.startswith("مؤقت"):
                    nid_str = "القومي: غير مسجل"
                else:
                    nid_str = f"القومي: {matched_nid}"

                match_type = "الاسم والرقم القومي" if (has_nid and (matched_nid == nid or matched_nid.startswith(nid)) and len(name) >= 3) else ("الرقم القومي" if (has_nid and (matched_nid == nid or matched_nid.startswith(nid))) else "الاسم")

                self.dup_warning_label.setText(
                    f"⚠️ إنذار تشابه ({match_type})! [{m['full_name']} | {nid_str} | إدارة: {m['administration_name']} - {m['school']}]{status_text}"
                )
                self.dup_warning_label.show()
                return
        self.dup_warning_label.hide()

    def save_employee(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip() or "0"

        if not name:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الموظف على الأقل.")
            return

        # Check for duplicate employee warning
        matches = self.db.check_duplicate_employee(name, nid)
        if matches:
            m = matches[0]
            matched_nid = str(m.get("national_id", "")).strip()
            if not matched_nid or matched_nid in ["0", "None", "nan"]:
                matched_nid = "غير مسجل"
            details = [
                f"• الاسم: {m['full_name']}",
                f"• الرقم القومي: {matched_nid}",
                f"• الإدارة التعليمية: {m['administration_name']}",
                f"• جهة العمل: {m['school']}"
            ]
            if m.get("exclusions"):
                details.append(f"• قرارات الاستبعاد المسجلة له: {len(m['exclusions'])} قرار")
            if m.get("prisoners"):
                details.append(f"• قضايا الحبس المسجلة له: {len(m['prisoners'])} قضية")

            msg = "⚠️ إنذار: تم العثور على تشابه في بيانات الموظف (الاسم أو الرقم القومي)!\n\n"
            msg += "\n".join(details) + "\n\n"
            msg += "هل تريد بالتأكيد الاستمرار وتسجيل هذا الموظف مرة أخرى؟"

            reply = QMessageBox.question(
                self, "إنذار تشابه بيانات الموظف",
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        try:
            self.db.get_or_create_employee(
                full_name=name,
                national_id=nid,
                administration_id=self.admin_combo.currentData(),
                school=self.school_input.text().strip(),
                phone=""
            )
            QMessageBox.information(self, "نجاح", f"تم تسجيل الموظف «{name}» بنجاح.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر حفظ الموظف: {str(e)}")


class EditExcludedDialog(QDialog):
    """Dialog to edit an existing Excluded Personnel record with a clear warning."""
    def __init__(self, record_data: Dict[str, Any], db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.data = record_data
        self.db = db_manager
        emp_name = self.data.get("full_name", "")
        self.setWindowTitle(f"تعديل بيانات قرار استبعاد — {emp_name}")
        self.resize(580, 720)
        self.setLayoutDirection(Qt.RightToLeft)
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.setStyleSheet(EDIT_DIALOG_STYLE)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Scroll Area for Form Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(14)

        # 1. High-Visibility Warning Banner
        warn_box = QFrame()
        warn_box.setObjectName("WarningBanner")
        warn_box.setStyleSheet("""
            background-color: #FEF3C7;
            border: 2px solid #F59E0B;
            border-radius: 8px;
            padding: 10px 14px;
        """)
        warn_layout = QVBoxLayout(warn_box)
        warn_layout.setSpacing(4)
        warn_title = QLabel("⚠️ تحذير: أنت في وضع تعديل بيانات سجل مسجل مسبقاً بالنظام!")
        warn_title.setStyleSheet("color: #B45309; font-size: 14px; font-weight: bold;")
        warn_desc = QLabel("تنبيه: أي تغييرات ستقوم بحفظها ستعدل مباشرة السجلات الرسمية وبيانات الموظف وقرار الاستبعاد في قاعدة البيانات.")
        warn_desc.setStyleSheet("color: #92400E; font-size: 12px;")
        warn_desc.setWordWrap(True)
        warn_layout.addWidget(warn_title)
        warn_layout.addWidget(warn_desc)
        layout.addWidget(warn_box)

        # 2. Employee Info Group
        emp_group = QGroupBox("بيانات الموظف الأساسية")
        emp_form = QFormLayout(emp_group)

        self.name_input = QLineEdit()
        self.name_input.setText(str(self.data.get("full_name") or ""))
        emp_form.addRow("الاسم الكامل *:", self.name_input)

        self.nid_input = QLineEdit()
        nid_val = str(self.data.get("national_id") or "0").strip()
        if nid_val in ["None", "nan", "null"]:
            nid_val = "0"
        self.nid_input.setText(nid_val)
        self.nid_input.setMaxLength(14)
        emp_form.addRow("الرقم القومي *:", self.nid_input)

        self.admin_combo = QComboBox()
        self.admin_combo.addItem("غير محدد", None)
        curr_admin_id = self.data.get("admin_id") or self.data.get("administration_id")
        curr_admin_name = self.data.get("administration_name")
        selected_idx = 0
        for idx, adm in enumerate(self.db.get_administrations()):
            self.admin_combo.addItem(adm["name"], adm["id"])
            if curr_admin_id and adm["id"] == curr_admin_id:
                selected_idx = idx + 1
            elif not curr_admin_id and curr_admin_name and adm["name"] == curr_admin_name:
                selected_idx = idx + 1
        self.admin_combo.setCurrentIndex(selected_idx)
        emp_form.addRow("الإدارة التعليمية:", self.admin_combo)

        self.school_input = QLineEdit()
        self.school_input.setText(str(self.data.get("school") or ""))
        emp_form.addRow("جهة العمل / المدرسة:", self.school_input)

        layout.addWidget(emp_group)

        # 3. Exclusion Details Group
        ex_group = QGroupBox("بيانات وقرار الاستبعاد")
        ex_form = QFormLayout(ex_group)

        self.serial_input = QLineEdit()
        serial_val = str(self.data.get("record_number") or self.data.get("id") or "")
        self.serial_input.setText(serial_val)
        self.serial_input.setPlaceholderText("رقم المسلسل (م)")
        ex_form.addRow("رقم المسلسل (م):", self.serial_input)

        self.current_job_input = QLineEdit()
        self.current_job_input.setText(str(self.data.get("current_job") or ""))
        ex_form.addRow("الوظيفة الحالية:", self.current_job_input)

        self.nominee_job_input = QLineEdit()
        self.nominee_job_input.setText(str(self.data.get("nominee_job") or ""))
        ex_form.addRow("الوظيفة المرشح لها:", self.nominee_job_input)

        self.case_type_combo = QComboBox()
        self.case_type_combo.addItem("غير محدد", None)
        curr_case_id = self.data.get("case_type_id")
        curr_case_name = self.data.get("case_type_name")
        case_idx = 0
        for idx, ct in enumerate(self.db.get_case_types()):
            self.case_type_combo.addItem(ct["name"], ct["id"])
            if curr_case_id and ct["id"] == curr_case_id:
                case_idx = idx + 1
            elif not curr_case_id and curr_case_name and ct["name"] == curr_case_name:
                case_idx = idx + 1
        self.case_type_combo.setCurrentIndex(case_idx)
        ex_form.addRow("نوع القضية / المخالفة:", self.case_type_combo)

        self.entity_input = QLineEdit()
        self.entity_input.setText(str(self.data.get("exclusion_entity") or ""))
        ex_form.addRow("جهة الاستبعاد:", self.entity_input)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        raw_date = str(self.data.get("exclusion_date") or "").strip()
        parsed_date = QDate.fromString(raw_date, "yyyy-MM-dd")
        if parsed_date.isValid():
            self.date_input.setDate(parsed_date)
        else:
            self.date_input.setDate(QDate.currentDate())
        ex_form.addRow("تاريخ القرار / الاستبعاد:", self.date_input)

        self.reason_input = QTextEdit()
        self.reason_input.setFixedHeight(75)
        self.reason_input.setPlainText(str(self.data.get("exclusion_reason") or ""))
        ex_form.addRow("سبب الاستبعاد:", self.reason_input)

        layout.addWidget(ex_group)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # 4. Action Buttons (Fixed at bottom)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        save_btn = QPushButton("حفظ التعديلات 💾")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E40AF;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        save_btn.clicked.connect(self.save_modifications)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("إلغاء الأمر")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        main_layout.addLayout(btn_layout)

    def save_modifications(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip() or "0"

        if not name:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الموظف على الأقل.")
            return

        # Mandatory Warning & Confirmation prompt before applying changes
        confirm = QMessageBox.warning(
            self,
            "⚠️ تحذير: تأكيد تعديل البيانات",
            f"أنت على وشك تعديل بيانات السجل الخاص بالموظف:\n«{name}»\n\n"
            "تنبيه: سيتم استبدال البيانات القديمة بهذه البيانات الجديدة بشكل نهائي.\n"
            "هل أنت متأكد من حفظ وتطبيق هذه التعديلات؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        rec_num = None
        s_text = self.serial_input.text().strip()
        if s_text.isdigit():
            rec_num = int(s_text)

        update_data = {
            "full_name": name,
            "national_id": nid,
            "administration_id": self.admin_combo.currentData(),
            "school": self.school_input.text().strip(),
            "phone": self.data.get("phone", ""),
            "record_number": rec_num,
            "case_type_id": self.case_type_combo.currentData(),
            "current_job": self.current_job_input.text().strip(),
            "nominee_job": self.nominee_job_input.text().strip(),
            "exclusion_entity": self.entity_input.text().strip(),
            "exclusion_date": self.date_input.date().toString("yyyy-MM-dd"),
            "exclusion_reason": self.reason_input.toPlainText().strip()
        }

        rec_id = self.data.get("id")
        try:
            success = self.db.update_excluded_record(rec_id, update_data)
            if success:
                self.data.update(update_data)
                self.data["administration_name"] = self.admin_combo.currentText()
                self.data["case_type_name"] = self.case_type_combo.currentText()
                QMessageBox.information(self, "تم الحفظ بنجاح", "✅ تم حفظ وتحديث بيانات قرار الاستبعاد بنجاح.")
                self.accept()
            else:
                QMessageBox.critical(self, "خطأ", "تعذر العثور على السجل في قاعدة البيانات لتحديثه.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التعديل", f"تعذر تحديث السجل:\n{str(e)}")


class EditPrisonerDialog(QDialog):
    """Dialog to edit an existing Prisoner / Legal Case record with a clear warning."""
    def __init__(self, record_data: Dict[str, Any], db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.data = record_data
        self.db = db_manager
        emp_name = self.data.get("full_name", "")
        self.setWindowTitle(f"تعديل بيانات مسجون / قضية جنائية — {emp_name}")
        self.resize(580, 720)
        self.setLayoutDirection(Qt.RightToLeft)
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.setStyleSheet(EDIT_DIALOG_STYLE)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Scroll Area for Form Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(14)

        # 1. High-Visibility Warning Banner
        warn_box = QFrame()
        warn_box.setObjectName("WarningBanner")
        warn_box.setStyleSheet("""
            background-color: #FEF3C7;
            border: 2px solid #F59E0B;
            border-radius: 8px;
            padding: 10px 14px;
        """)
        warn_layout = QVBoxLayout(warn_box)
        warn_layout.setSpacing(4)
        warn_title = QLabel("⚠️ تحذير: أنت في وضع تعديل بيانات سجل مسجون مسجل بالنظام!")
        warn_title.setStyleSheet("color: #B45309; font-size: 14px; font-weight: bold;")
        warn_desc = QLabel("تنبيه: أي تغييرات ستقوم بحفظها ستعدل مباشرة السجلات القضائية وبيانات الموظف في قاعدة البيانات.")
        warn_desc.setStyleSheet("color: #92400E; font-size: 12px;")
        warn_desc.setWordWrap(True)
        warn_layout.addWidget(warn_title)
        warn_layout.addWidget(warn_desc)
        layout.addWidget(warn_box)

        # 2. Employee Info Group
        emp_group = QGroupBox("بيانات الموظف الأساسية")
        emp_form = QFormLayout(emp_group)

        self.name_input = QLineEdit()
        self.name_input.setText(str(self.data.get("full_name") or ""))
        emp_form.addRow("الاسم الكامل *:", self.name_input)

        self.nid_input = QLineEdit()
        nid_val = str(self.data.get("national_id") or "0").strip()
        if nid_val in ["None", "nan", "null"]:
            nid_val = "0"
        self.nid_input.setText(nid_val)
        self.nid_input.setMaxLength(14)
        emp_form.addRow("الرقم القومي *:", self.nid_input)

        self.admin_combo = QComboBox()
        self.admin_combo.addItem("غير محدد", None)
        curr_admin_id = self.data.get("admin_id") or self.data.get("administration_id")
        curr_admin_name = self.data.get("administration_name")
        selected_idx = 0
        for idx, adm in enumerate(self.db.get_administrations()):
            self.admin_combo.addItem(adm["name"], adm["id"])
            if curr_admin_id and adm["id"] == curr_admin_id:
                selected_idx = idx + 1
            elif not curr_admin_id and curr_admin_name and adm["name"] == curr_admin_name:
                selected_idx = idx + 1
        self.admin_combo.setCurrentIndex(selected_idx)
        emp_form.addRow("الإدارة التعليمية:", self.admin_combo)

        self.school_input = QLineEdit()
        self.school_input.setText(str(self.data.get("school") or ""))
        emp_form.addRow("جهة العمل / المدرسة:", self.school_input)

        layout.addWidget(emp_group)

        # 3. Prisoner Details Group
        pr_group = QGroupBox("بيانات القضية والحبس")
        pr_form = QFormLayout(pr_group)

        self.serial_input = QLineEdit()
        serial_val = str(self.data.get("record_number") or self.data.get("id") or "")
        self.serial_input.setText(serial_val)
        self.serial_input.setPlaceholderText("رقم المسلسل (م)")
        pr_form.addRow("رقم المسلسل (م):", self.serial_input)

        self.case_number_input = QLineEdit()
        self.case_number_input.setText(str(self.data.get("case_number") or ""))
        pr_form.addRow("رقم القضية / المحضر:", self.case_number_input)

        self.case_type_combo = QComboBox()
        self.case_type_combo.addItem("غير محدد", None)
        curr_case_id = self.data.get("case_type_id")
        curr_case_name = self.data.get("case_type_name")
        case_idx = 0
        for idx, ct in enumerate(self.db.get_case_types()):
            self.case_type_combo.addItem(ct["name"], ct["id"])
            if curr_case_id and ct["id"] == curr_case_id:
                case_idx = idx + 1
            elif not curr_case_id and curr_case_name and ct["name"] == curr_case_name:
                case_idx = idx + 1
        self.case_type_combo.setCurrentIndex(case_idx)
        pr_form.addRow("نوع القضية والتهمة:", self.case_type_combo)

        self.status_combo = QComboBox()
        curr_status = str(self.data.get("current_status") or "على رأس العمل")
        for st in PRISONER_STATUSES:
            self.status_combo.addItem(st, st)
        status_idx = self.status_combo.findText(curr_status)
        if status_idx >= 0:
            self.status_combo.setCurrentIndex(status_idx)
        pr_form.addRow("الموقف الجنائي الحالي:", self.status_combo)

        self.court_ruling_input = QTextEdit()
        self.court_ruling_input.setFixedHeight(65)
        self.court_ruling_input.setPlainText(str(self.data.get("court_ruling") or ""))
        pr_form.addRow("منطوق الحكم / القرار:", self.court_ruling_input)

        self.release_date_input = QLineEdit()
        self.release_date_input.setText(str(self.data.get("release_date") or ""))
        pr_form.addRow("تاريخ الإفراج المتوقع / الفعلي:", self.release_date_input)

        self.housing_input = QLineEdit()
        self.housing_input.setText(str(self.data.get("housing_location") or ""))
        pr_form.addRow("مكان التسكين:", self.housing_input)

        layout.addWidget(pr_group)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # 4. Action Buttons (Fixed at bottom)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        save_btn = QPushButton("حفظ التعديلات 💾")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E40AF;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        save_btn.clicked.connect(self.save_modifications)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("إلغاء الأمر")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        main_layout.addLayout(btn_layout)

    def save_modifications(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip() or "0"

        if not name:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الموظف على الأقل.")
            return

        # Mandatory Warning & Confirmation prompt before applying changes
        confirm = QMessageBox.warning(
            self,
            "⚠️ تحذير: تأكيد تعديل البيانات",
            f"أنت على وشك تعديل بيانات السجل الخاص بالمسجون / المتهم:\n«{name}»\n\n"
            "تنبيه: سيتم استبدال البيانات القديمة بهذه البيانات الجديدة بشكل نهائي.\n"
            "هل أنت متأكد من حفظ وتطبيق هذه التعديلات؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        rec_num = None
        s_text = self.serial_input.text().strip()
        if s_text.isdigit():
            rec_num = int(s_text)

        update_data = {
            "full_name": name,
            "national_id": nid,
            "administration_id": self.admin_combo.currentData(),
            "school": self.school_input.text().strip(),
            "phone": self.data.get("phone", ""),
            "record_number": rec_num,
            "case_number": self.case_number_input.text().strip(),
            "case_type_id": self.case_type_combo.currentData(),
            "court_ruling": self.court_ruling_input.toPlainText().strip(),
            "current_status": self.status_combo.currentText(),
            "release_date": self.release_date_input.text().strip(),
            "housing_location": self.housing_input.text().strip()
        }

        rec_id = self.data.get("id")
        try:
            success = self.db.update_prisoner_record(rec_id, update_data)
            if success:
                self.data.update(update_data)
                self.data["administration_name"] = self.admin_combo.currentText()
                self.data["case_type_name"] = self.case_type_combo.currentText()
                QMessageBox.information(self, "تم الحفظ بنجاح", "✅ تم حفظ وتحديث بيانات السجل الجنائي بنجاح.")
                self.accept()
            else:
                QMessageBox.critical(self, "خطأ", "تعذر العثور على السجل في قاعدة البيانات لتحديثه.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التعديل", f"تعذر تحديث السجل:\n{str(e)}")


class OfficialStatementCardDialog(QDialog):
    """Executive Egyptian Directorate Statement Card (بطاقة بيان حالة موظف).
    Accurately reproduces the official form layout with:
    - Prominent Serial Number 'م' box at top
    - Yellow label column on right (#FEF08A)
    - Bordered white value boxes with bold red text (#B91C1C)
    - Full fields in official governmental order
    - Actions: Edit record, Print statement, Export PDF, Delete record, Close
    """
    def __init__(self, record_data: Dict[str, Any], record_type: str = "excluded", db_manager: Optional[DatabaseManager] = None, parent=None):
        super().__init__(parent)
        self.data = record_data
        self.record_type = record_type
        self.db = db_manager
        self.setWindowTitle("بيان حالة موظف (تعديل وحذف) - مديرية التربية والتعليم بالإسكندرية")
        self.resize(580, 720)
        self.setLayoutDirection(Qt.RightToLeft)
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.init_ui()

    def _make_field_row(self, label_text: str, value_text: str, is_large_serial: bool = False) -> QHBoxLayout:
        """Builds a row with blue-themed governmental header and white bordered value box matching Image 1."""
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        # Right Label
        lbl = QLabel(label_text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedWidth(135)
        lbl.setFixedHeight(46 if not is_large_serial else 54)
        if is_large_serial:
            lbl.setStyleSheet("""
                background-color: #1E40AF;
                color: #FFFFFF;
                font-family: 'Segoe UI', Tahoma, Arial;
                font-weight: bold;
                font-size: 16px;
                border: 1.5px solid #1E40AF;
                border-radius: 6px;
                padding: 3px 6px;
            """)
        else:
            lbl.setStyleSheet("""
                background-color: #FFFFFF;
                color: #1E40AF;
                font-family: 'Segoe UI', Tahoma, Arial;
                font-weight: bold;
                font-size: 13px;
                border: 1.5px solid #93C5FD;
                border-radius: 6px;
                padding: 3px 6px;
            """)

        # Left Value Box
        clean_val = str(value_text).strip() if value_text is not None else ""
        if clean_val in ["", "None", "nan", "NaN", "null"]:
            clean_val = "—"

        val_box = QLabel(clean_val)
        val_box.setAlignment(Qt.AlignCenter)
        val_box.setFixedHeight(46 if not is_large_serial else 54)
        
        if is_large_serial:
            val_box.setStyleSheet("""
                background-color: #FFFFFF;
                color: #1E40AF;
                font-family: 'Segoe UI', Tahoma, Arial;
                font-weight: bold;
                font-size: 24px;
                border: 1.5px solid #93C5FD;
                border-radius: 6px;
                padding: 2px;
            """)
        else:
            val_box.setStyleSheet("""
                background-color: #FFFFFF;
                color: #0F172A;
                font-family: 'Segoe UI', Tahoma, Arial;
                font-weight: bold;
                font-size: 13px;
                border: 1.5px solid #93C5FD;
                border-radius: 6px;
                padding: 3px 8px;
            """)

        row_layout.addWidget(lbl)
        row_layout.addWidget(val_box, 1)
        return row_layout

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 16, 20, 16)

        # Official Government Directorate Banner with Emblem
        banner_h = QHBoxLayout()
        banner_h.setSpacing(12)
        if LOGO_PATH.exists():
            emblem_lbl = QLabel()
            pix = QPixmap(str(LOGO_PATH)).scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            emblem_lbl.setPixmap(pix)
            banner_h.addWidget(emblem_lbl)

        gov_v = QVBoxLayout()
        gov_title = QLabel("جمهورية مصر العربية — محافظة الإسكندرية")
        gov_title.setStyleSheet("color: #64748B; font-size: 11px; font-weight: bold;")
        dir_title = QLabel("مديرية التربية والتعليم بالإسكندرية — بيان حالة رسمي")
        dir_title.setStyleSheet("color: #1E40AF; font-size: 14px; font-weight: bold;")
        gov_v.addWidget(gov_title)
        gov_v.addWidget(dir_title)
        banner_h.addLayout(gov_v)
        banner_h.addStretch()
        main_layout.addLayout(banner_h)

        # Container card with subtle border matching Image 1
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1.5px solid #93C5FD;
                border-radius: 12px;
                padding: 14px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        # 1. Serial Number (م) at the top
        serial_val = self.data.get("record_number") or self.data.get("id") or "1"
        card_layout.addLayout(self._make_field_row("م", str(serial_val), is_large_serial=True))

        # 2. Common Fields
        nid_val = str(self.data.get("national_id", "")).strip()
        if not nid_val or "مؤقت" in nid_val or nid_val in ["None", "nan"]:
            nid_val = "0"
        card_layout.addLayout(self._make_field_row("الاسم", self.data.get("full_name", "")))
        if nid_val == "0":
            card_layout.addLayout(self._make_field_row("القومي", "⚠️ 0 (غير مسجل)"))
        elif len(nid_val) < 14:
            card_layout.addLayout(self._make_field_row("القومي", f"⚠️ {nid_val} (غير مكتمل)"))
        else:
            card_layout.addLayout(self._make_field_row("القومي", nid_val))
        card_layout.addLayout(self._make_field_row("الإدارة", self.data.get("administration_name", "")))
        card_layout.addLayout(self._make_field_row("المدرسة", self.data.get("school", "")))

        # 3. Category Specific Fields
        if self.record_type == "excluded":
            card_layout.addLayout(self._make_field_row("الوظيفة الحالية", self.data.get("current_job", "")))
            card_layout.addLayout(self._make_field_row("الوظيفة المرشح لها", self.data.get("nominee_job", "")))
            card_layout.addLayout(self._make_field_row("جهة الاستبعاد", self.data.get("exclusion_entity", "")))
            card_layout.addLayout(self._make_field_row("تاريخ الاستبعاد", self.data.get("exclusion_date", "")))
            card_layout.addLayout(self._make_field_row("سبب الاستبعاد", self.data.get("exclusion_reason", "")))
            card_layout.addLayout(self._make_field_row("نوع القضية", self.data.get("case_type_name", "")))
        else:
            card_layout.addLayout(self._make_field_row("رقم القضية", self.data.get("case_number", "")))
            card_layout.addLayout(self._make_field_row("الحكم الصادر", self.data.get("court_ruling", "")))
            card_layout.addLayout(self._make_field_row("الوضع الراهن", self.data.get("current_status", "")))
            card_layout.addLayout(self._make_field_row("تاريخ الإفراج", self.data.get("release_date", "")))
            card_layout.addLayout(self._make_field_row("مكان التسكين", self.data.get("housing_location", "")))
            card_layout.addLayout(self._make_field_row("نوع القضية", self.data.get("case_type_name", "")))

        main_layout.addWidget(card)

        # 4. Action Buttons matching Image 1
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        edit_btn = QPushButton("تعديل بيانات السجل ✏️")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFBEB;
                color: #D97706;
                border: 2px solid #F59E0B;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #FEF3C7;
            }
        """)
        edit_btn.clicked.connect(self.edit_current_record)
        btn_layout.addWidget(edit_btn)

        print_btn = QPushButton("معاينة وطباعة 🖨️")
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                border-color: #94A3B8;
            }
        """)
        print_btn.clicked.connect(self.print_statement)
        btn_layout.addWidget(print_btn)

        pdf_btn = QPushButton("تصدير PDF 📄")
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                border-color: #94A3B8;
            }
        """)
        pdf_btn.clicked.connect(self.export_pdf)
        btn_layout.addWidget(pdf_btn)

        del_btn = QPushButton("حذف السجل 🗑️")
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1.5px solid #FCA5A5;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
            }
        """)
        del_btn.clicked.connect(self.delete_current_record)
        btn_layout.addWidget(del_btn)

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E40AF;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        main_layout.addLayout(btn_layout)

    def edit_current_record(self):
        """Allows modifying this record directly with warning prompts."""
        if not self.db:
            return
        if self.record_type == "excluded":
            dlg = EditExcludedDialog(self.data, self.db, self)
        else:
            dlg = EditPrisonerDialog(self.data, self.db, self)

        if dlg.exec():
            # Refresh data and notify parent
            self.accept()
            if self.parent() and hasattr(self.parent(), "load_data"):
                self.parent().load_data()
            if self.parent() and hasattr(self.parent(), "execute_search"):
                self.parent().execute_search()
            if self.parent() and hasattr(self.parent(), "data_changed_signal"):
                self.parent().data_changed_signal.emit()

    def delete_current_record(self):
        """Allows deleting this record directly from the card dialog using smart delete."""
        if not self.db:
            return
        table = "ExcludedRecords" if self.record_type == "excluded" else "PrisonerRecords"
        deleted = prompt_smart_delete(self, self.db, table, self.data)
        if deleted:
            self.accept()
            if self.parent() and hasattr(self.parent(), "load_data"):
                self.parent().load_data()
            if self.parent() and hasattr(self.parent(), "execute_search"):
                self.parent().execute_search()
            if self.parent() and hasattr(self.parent(), "data_changed_signal"):
                self.parent().data_changed_signal.emit()

    def print_statement(self):
        """Shows printable statement dialog with visual preview, zoom, and print support."""
        try:
            from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout
            from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog

            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPageSize(QPageSize.A4))
            printer.setPageOrientation(QPageLayout.Portrait)

            html_content = self._generate_html_statement()

            def handle_paint(target_printer):
                doc = QTextDocument()
                paint_rect = target_printer.pageLayout().paintRect(QPageLayout.Point)
                doc.setPageSize(paint_rect.size())
                doc.setDocumentMargin(20)
                doc.setHtml(html_content)
                doc.print_(target_printer)

            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowTitle(f"معاينة وطباعة بيان حالة — {self.data.get('full_name')}")
            preview.resize(960, 800)
            preview.paintRequested.connect(handle_paint)
            preview.exec()
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الطباعة", f"تعذر فتح نافذة المعاينة والطباعة:\n{str(e)}")

    def export_pdf(self):
        """Exports the official statement directly to a PDF document."""
        emp_name = str(self.data.get("full_name", "موظف")).replace(" ", "_")
        default_filename = f"بيان_حالة_{emp_name}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ بيان الحالة كملف PDF",
            default_filename,
            "PDF Files (*.pdf)"
        )
        if not save_path:
            return

        try:
            from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout
            from PySide6.QtPrintSupport import QPrinter

            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(save_path)
            printer.setPageSize(QPageSize(QPageSize.A4))
            printer.setPageOrientation(QPageLayout.Portrait)

            doc = QTextDocument()
            doc.setDocumentMargin(25)
            doc.setHtml(self._generate_html_statement())
            doc.print_(printer)

            QMessageBox.information(
                self, "تم تصدير PDF بنجاح",
                f"تم حفظ بيان الحالة المعتمد كملف PDF بنجاح في:\n{save_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ في تصدير PDF", f"تعذر حفظ الملف:\n{str(e)}")

    def _generate_html_statement(self) -> str:
        rec_num = self.data.get("record_number") or self.data.get("id") or "1"
        is_exc = (self.record_type == "excluded")
        
        specific_rows = f"""
            <tr><td class="val">{self.data.get('current_job') or '—'}</td><td class="lbl">الوظيفة الحالية:</td></tr>
            <tr><td class="val">{self.data.get('nominee_job') or '—'}</td><td class="lbl">الوظيفة المرشح لها:</td></tr>
            <tr><td class="val">{self.data.get('exclusion_entity') or '—'}</td><td class="lbl">جهة الاستبعاد:</td></tr>
            <tr><td class="val">{self.data.get('exclusion_date') or '—'}</td><td class="lbl">تاريخ الاستبعاد:</td></tr>
            <tr><td class="val">{self.data.get('exclusion_reason') or '—'}</td><td class="lbl">سبب الاستبعاد:</td></tr>
            <tr><td class="val">{self.data.get('case_type_name') or '—'}</td><td class="lbl">نوع القضية:</td></tr>
        """ if is_exc else f"""
            <tr><td class="val">{self.data.get('case_number') or '—'}</td><td class="lbl">رقم القضية:</td></tr>
            <tr><td class="val">{self.data.get('court_ruling') or '—'}</td><td class="lbl">الحكم الصادر:</td></tr>
            <tr><td class="val">{self.data.get('current_status') or '—'}</td><td class="lbl">الوضع الراهن:</td></tr>
            <tr><td class="val">{self.data.get('release_date') or '—'}</td><td class="lbl">تاريخ الإفراج:</td></tr>
            <tr><td class="val">{self.data.get('housing_location') or '—'}</td><td class="lbl">مكان التسكين:</td></tr>
            <tr><td class="val">{self.data.get('case_type_name') or '—'}</td><td class="lbl">نوع القضية:</td></tr>
        """

        return f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; margin: 20px; color: #0F172A; direction: rtl; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; direction: rtl; }}
                td {{ padding: 9px 14px; border: 1.5px solid #94A3B8; font-size: 11pt; text-align: right; }}
                .lbl {{ width: 30%; background-color: #FEF08A; font-weight: bold; color: #854D0E; font-size: 11pt; }}
                .val {{ width: 70%; font-weight: bold; color: #1E293B; font-size: 11pt; }}
                .serial-box {{ font-size: 16pt; color: #DC2626; font-weight: bold; text-align: center; }}
            </style>
        </head>
        <body>
            <table>
                <tr>
                    <td class="val serial-box">{rec_num}</td>
                    <td class="lbl">رقم المسلسل (م):</td>
                </tr>
                <tr><td class="val">{self.data.get('full_name') or '—'}</td><td class="lbl">اسم الموظف / المعلم:</td></tr>
                <tr><td class="val">{'0' if not self.data.get('national_id') or 'مؤقت' in str(self.data.get('national_id')) else self.data.get('national_id')}</td><td class="lbl">الرقم القومي:</td></tr>
                <tr><td class="val">{self.data.get('administration_name') or '—'}</td><td class="lbl">الإدارة التعليمية:</td></tr>
                <tr><td class="val">{self.data.get('school') or '—'}</td><td class="lbl">جهة العمل / المدرسة:</td></tr>
                {specific_rows}
            </table>
        </body>
        </html>
        """

# Alias for backwards compatibility
RecordDetailsDialog = OfficialStatementCardDialog
