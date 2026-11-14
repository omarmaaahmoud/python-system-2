# -*- coding: utf-8 -*-
"""
School Details and Add/Edit Dialog.
Organized into clear visual sections (QGroupBoxes) with support for associated security guards.
Features executive government badge headers, balanced grids, and high-visibility data display.
"""
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QTextEdit, QPushButton, QGroupBox,
    QScrollArea, QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon, QColor, QBrush

from ..services.school_service import SchoolService
from ..services.guard_service import GuardService
from ..config import DEFAULT_ADMINISTRATIONS, DEFAULT_AFFILIATIONS


class SchoolDialog(QDialog):
    data_saved = Signal()

    def __init__(
        self,
        school_service: SchoolService,
        guard_service: GuardService,
        school_id: Optional[int] = None,
        read_only: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.school_service = school_service
        self.guard_service = guard_service
        self.school_id = school_id
        self.read_only = read_only

        title = "بيانات مدرسة — عرض التفاصيل" if read_only else ("تعديل بيانات مدرسة" if school_id else "إضافة مدرسة جديدة")
        self.setWindowTitle(title)
        self.resize(920, 800)
        self.setMinimumSize(850, 680)
        self.setLayoutDirection(Qt.RightToLeft)

        self.init_ui()
        if school_id:
            self.load_school_data()

    def init_ui(self):
        self.setObjectName("SchoolDialog")
        self.setStyleSheet("""
            QDialog#SchoolDialog {
                background-color: #F1F5F9;
            }
            QScrollArea {
                background-color: #F1F5F9;
                border: none;
            }
            #DialogContainer {
                background-color: #F1F5F9;
            }
            QGroupBox {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 10px;
                margin-top: 26px;
                padding-top: 22px;
                padding-bottom: 14px;
                padding-left: 16px;
                padding-right: 16px;
                font-size: 13px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                right: 16px;
                padding: 4px 14px;
                background-color: #1E40AF;
                color: #FFFFFF;
                border-radius: 6px;
                font-weight: 800;
                font-size: 12px;
            }
            QLabel {
                color: #334155;
                font-weight: 600;
                font-size: 12px;
                background: transparent;
            }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 7px;
                padding: 6px 10px;
                font-size: 13px;
                color: #0F172A;
                min-height: 22px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 2px solid #2563EB;
                background-color: #F8FAFC;
            }
            QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                color: #0F172A;
                font-weight: 600;
            }
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                gridline-color: #E2E8F0;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1E3A8A;
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px;
                border: none;
                font-size: 12px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container.setObjectName("DialogContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(16)

        # 1. Basic Information
        grp_basic = QGroupBox("🏫 البيانات الأساسية للمنشأة التعليمية")
        g1 = QGridLayout(grp_basic)
        g1.setSpacing(12)
        g1.setColumnStretch(1, 1)
        g1.setColumnStretch(3, 1)

        lbl_admin = QLabel("الإدارة التعليمية:")
        g1.addWidget(lbl_admin, 0, 0)
        self.combo_admin = QComboBox()
        self.combo_admin.addItems(DEFAULT_ADMINISTRATIONS)
        g1.addWidget(self.combo_admin, 0, 1)

        lbl_sname = QLabel("اسم المدرسة: *")
        g1.addWidget(lbl_sname, 0, 2)
        self.txt_school_name = QLineEdit()
        self.txt_school_name.setPlaceholderText("أدخل الاسم الرسمي للمدرسة")
        g1.addWidget(self.txt_school_name, 0, 3)

        lbl_affil = QLabel("التبعية / المرحلة:")
        g1.addWidget(lbl_affil, 1, 0)
        self.combo_affil = QComboBox()
        self.combo_affil.setEditable(True)
        self.combo_affil.addItems(DEFAULT_AFFILIATIONS)
        g1.addWidget(self.combo_affil, 1, 1)

        lbl_rooms = QLabel("عدد الفصول:")
        g1.addWidget(lbl_rooms, 1, 2)
        self.txt_classrooms = QLineEdit()
        self.txt_classrooms.setPlaceholderText("عدد الفصول التعليمية")
        g1.addWidget(self.txt_classrooms, 1, 3)

        lbl_gates = QLabel("عدد البوابات:")
        g1.addWidget(lbl_gates, 2, 0)
        self.txt_gates = QLineEdit()
        self.txt_gates.setPlaceholderText("عدد بوابات ومنافذ المدرسة")
        g1.addWidget(self.txt_gates, 2, 1)

        layout.addWidget(grp_basic)

        # 2. School Management & Security Officer
        grp_mgmt = QGroupBox("👔 القيادة المدرسية ومسؤولو الأمن")
        g2 = QGridLayout(grp_mgmt)
        g2.setSpacing(12)
        g2.setColumnStretch(1, 1)
        g2.setColumnStretch(3, 1)

        g2.addWidget(QLabel("مدير المدرسة:"), 0, 0)
        self.txt_manager = QLineEdit()
        self.txt_manager.setPlaceholderText("اسم مدير المدرسة")
        g2.addWidget(self.txt_manager, 0, 1)

        g2.addWidget(QLabel("تليفون المدير:"), 0, 2)
        self.txt_manager_phone = QLineEdit()
        self.txt_manager_phone.setPlaceholderText("رقم تليفون المدير")
        g2.addWidget(self.txt_manager_phone, 0, 3)

        g2.addWidget(QLabel("مسؤول الأمن بالمدرسة:"), 1, 0)
        self.txt_sec_officer = QLineEdit()
        self.txt_sec_officer.setPlaceholderText("اسم مسؤول الأمن بالمدرسة")
        g2.addWidget(self.txt_sec_officer, 1, 1)

        g2.addWidget(QLabel("تليفون مسؤول الأمن:"), 1, 2)
        self.txt_sec_phone = QLineEdit()
        self.txt_sec_phone.setPlaceholderText("رقم هاتف مسؤول الأمن")
        g2.addWidget(self.txt_sec_phone, 1, 3)

        layout.addWidget(grp_mgmt)

        # 3. Fire Safety
        grp_fire = QGroupBox("🧯 منظومة الحماية من أخطار الحريق")
        g3 = QGridLayout(grp_fire)
        g3.setSpacing(12)
        g3.setColumnStretch(1, 1)
        g3.setColumnStretch(3, 1)

        g3.addWidget(QLabel("إجمالي عدد الطفايات:"), 0, 0)
        self.txt_extinguishers = QLineEdit()
        g3.addWidget(self.txt_extinguishers, 0, 1)

        g3.addWidget(QLabel("نوع الطفاية:"), 0, 2)
        self.txt_ext_type = QLineEdit()
        g3.addWidget(self.txt_ext_type, 0, 3)

        g3.addWidget(QLabel("وزن الطفاية:"), 1, 0)
        self.txt_ext_weight = QLineEdit()
        g3.addWidget(self.txt_ext_weight, 1, 1)

        g3.addWidget(QLabel("خطوط الحريق المفعلة:"), 1, 2)
        self.txt_active_lines = QLineEdit()
        g3.addWidget(self.txt_active_lines, 1, 3)

        g3.addWidget(QLabel("خطوط غير مفعلة:"), 2, 0)
        self.txt_inactive_lines = QLineEdit()
        g3.addWidget(self.txt_inactive_lines, 2, 1)

        g3.addWidget(QLabel("خراطيم صالحة:"), 2, 2)
        self.txt_valid_hoses = QLineEdit()
        g3.addWidget(self.txt_valid_hoses, 2, 3)

        g3.addWidget(QLabel("خراطيم غير صالحة:"), 3, 0)
        self.txt_invalid_hoses = QLineEdit()
        g3.addWidget(self.txt_invalid_hoses, 3, 1)

        g3.addWidget(QLabel("عدد جرادل الرمل:"), 3, 2)
        self.txt_buckets = QLineEdit()
        g3.addWidget(self.txt_buckets, 3, 3)

        layout.addWidget(grp_fire)

        # 4. Cameras
        grp_cam = QGroupBox("📹 منظومة كاميرات المراقبة")
        g4 = QGridLayout(grp_cam)
        g4.setSpacing(12)
        g4.setColumnStretch(1, 1)
        g4.setColumnStretch(3, 1)

        g4.addWidget(QLabel("كاميرات تعمل:"), 0, 0)
        self.txt_working_cam = QLineEdit()
        g4.addWidget(self.txt_working_cam, 0, 1)

        g4.addWidget(QLabel("كاميرات معطلة:"), 0, 2)
        self.txt_broken_cam = QLineEdit()
        g4.addWidget(self.txt_broken_cam, 0, 3)

        g4.addWidget(QLabel("شركة الصيانة المسؤولة:"), 1, 0)
        self.txt_cam_company = QLineEdit()
        g4.addWidget(self.txt_cam_company, 1, 1, 1, 3)

        layout.addWidget(grp_cam)

        # 5. Associated Security Guards
        grp_guards = QGroupBox("🛡️ حراس الأمن المكلفون بالمدرسة")
        g5 = QVBoxLayout(grp_guards)
        g5.setContentsMargins(12, 16, 12, 12)
        g5.setSpacing(8)

        self.table_guards = QTableWidget(0, 4)
        self.table_guards.setHorizontalHeaderLabels(["م", "اسم الحارس", "الرقم القومي", "رقم الهاتف"])
        self.table_guards.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_guards.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_guards.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table_guards.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table_guards.setColumnWidth(2, 180)  # Full width for 14 digits without cut-off
        self.table_guards.setColumnWidth(3, 150)  # Full width for phone number
        self.table_guards.verticalHeader().setVisible(False)
        self.table_guards.setFixedHeight(140)
        g5.addWidget(self.table_guards)

        layout.addWidget(grp_guards)

        # 6. Notes
        grp_notes = QGroupBox("📝 الملاحظات والتوصيات")
        gn = QVBoxLayout(grp_notes)
        gn.setContentsMargins(12, 16, 12, 12)
        self.txt_notes = QTextEdit()
        self.txt_notes.setFixedHeight(70)
        self.txt_notes.setPlaceholderText("أدخل أي ملاحظات إضافية حول أمان وتجهيزات المدرسة...")
        gn.addWidget(self.txt_notes)
        layout.addWidget(grp_notes)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        # Actions
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        if not self.read_only:
            self.btn_save = QPushButton("💾 حفظ البيانات")
            self.btn_save.setObjectName("PrimaryBtn")
            self.btn_save.setMinimumHeight(40)
            self.btn_save.clicked.connect(self.save_school)
            btn_bar.addWidget(self.btn_save)

        btn_close = QPushButton("إغلاق")
        btn_close.setObjectName("SecondaryBtn")
        btn_close.setMinimumHeight(40)
        btn_close.clicked.connect(self.close)
        btn_bar.addWidget(btn_close)

        main_layout.addLayout(btn_bar)

        if self.read_only:
            for w_type in (QLineEdit, QTextEdit, QComboBox):
                for widget in container.findChildren(w_type):
                    widget.setEnabled(False)

    def load_school_data(self):
        school = self.school_service.get_school_by_id(self.school_id)
        if not school:
            return

        self.combo_admin.setCurrentText(school.get("administration", ""))
        self.txt_school_name.setText(school.get("school_name", ""))
        self.combo_affil.setCurrentText(school.get("affiliation", ""))
        self.txt_classrooms.setText(school.get("classrooms_count", ""))
        self.txt_gates.setText(school.get("gates_count", ""))

        self.txt_manager.setText(school.get("manager_name", ""))
        self.txt_manager_phone.setText(school.get("manager_phone", ""))
        self.txt_sec_officer.setText(school.get("security_officer_name", ""))
        self.txt_sec_phone.setText(school.get("security_officer_phone", ""))

        self.txt_extinguishers.setText(school.get("fire_extinguishers_count", ""))
        self.txt_ext_type.setText(school.get("fire_extinguisher_type", ""))
        self.txt_ext_weight.setText(school.get("fire_extinguisher_weight", ""))
        self.txt_active_lines.setText(school.get("activated_fire_lines", ""))
        self.txt_inactive_lines.setText(school.get("inactive_fire_lines", ""))
        self.txt_valid_hoses.setText(school.get("valid_fire_hoses", ""))
        self.txt_invalid_hoses.setText(school.get("invalid_fire_hoses", ""))
        self.txt_buckets.setText(school.get("buckets_count", ""))

        self.txt_working_cam.setText(school.get("working_cameras", ""))
        self.txt_broken_cam.setText(school.get("non_working_cameras", ""))
        self.txt_cam_company.setText(school.get("camera_maintenance_company", ""))
        self.txt_notes.setText(school.get("notes", ""))

        # Populate guards
        guards = school.get("assigned_guards", [])
        self.table_guards.setRowCount(len(guards))
        for r_idx, g in enumerate(guards):
            idx_item = QTableWidgetItem(str(r_idx + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            self.table_guards.setItem(r_idx, 0, idx_item)

            name_item = QTableWidgetItem(g.get("guard_name", ""))
            name_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_guards.setItem(r_idx, 1, name_item)

            nid_item = QTableWidgetItem(g.get("national_id", "—"))
            nid_item.setTextAlignment(Qt.AlignCenter)
            self.table_guards.setItem(r_idx, 2, nid_item)

            phone_item = QTableWidgetItem(g.get("phone", "—"))
            phone_item.setTextAlignment(Qt.AlignCenter)
            self.table_guards.setItem(r_idx, 3, phone_item)

    def save_school(self):
        name = self.txt_school_name.text().strip()
        if not name:
            QMessageBox.warning(self, "حقل مطلوب", "يرجى كتابة اسم المدرسة للمتابعة.")
            self.txt_school_name.setFocus()
            return

        data = {
            "administration": self.combo_admin.currentText().strip(),
            "school_name": name,
            "affiliation": self.combo_affil.currentText().strip(),
            "classrooms_count": self.txt_classrooms.text().strip(),
            "gates_count": self.txt_gates.text().strip(),
            "manager_name": self.txt_manager.text().strip(),
            "manager_phone": self.txt_manager_phone.text().strip(),
            "security_officer_name": self.txt_sec_officer.text().strip(),
            "security_officer_phone": self.txt_sec_phone.text().strip(),
            "fire_extinguishers_count": self.txt_extinguishers.text().strip(),
            "fire_extinguisher_type": self.txt_ext_type.text().strip(),
            "fire_extinguisher_weight": self.txt_ext_weight.text().strip(),
            "activated_fire_lines": self.txt_active_lines.text().strip(),
            "inactive_fire_lines": self.txt_inactive_lines.text().strip(),
            "valid_fire_hoses": self.txt_valid_hoses.text().strip(),
            "invalid_fire_hoses": self.txt_invalid_hoses.text().strip(),
            "buckets_count": self.txt_buckets.text().strip(),
            "working_cameras": self.txt_working_cam.text().strip(),
            "non_working_cameras": self.txt_broken_cam.text().strip(),
            "camera_maintenance_company": self.txt_cam_company.text().strip(),
            "notes": self.txt_notes.toPlainText().strip()
        }

        if self.school_id:
            self.school_service.update_school(self.school_id, data)
        else:
            self.school_service.add_school(data)

        self.data_saved.emit()
        self.accept()
