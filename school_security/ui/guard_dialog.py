# -*- coding: utf-8 -*-
"""
Security Guard Add/Edit and School Assignment Dialog.
"""
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QTextEdit, QPushButton, QGroupBox,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal

from ..services.guard_service import GuardService
from ..services.school_service import SchoolService


class GuardDialog(QDialog):
    data_saved = Signal()

    def __init__(
        self,
        guard_service: GuardService,
        school_service: SchoolService,
        guard_id: Optional[int] = None,
        parent=None
    ):
        super().__init__(parent)
        self.guard_service = guard_service
        self.school_service = school_service
        self.guard_id = guard_id

        title = "تعديل بيانات حارس أمن" if guard_id else "إضافة حارس أمن جديد"
        self.setWindowTitle(title)
        self.resize(550, 480)
        self.setLayoutDirection(Qt.RightToLeft)

        self.init_ui()
        if guard_id:
            self.load_guard_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Guard Information Group
        grp_guard = QGroupBox("👤 بيانات حارس الأمن")
        g1 = QGridLayout(grp_guard)
        g1.setSpacing(12)

        g1.addWidget(QLabel("اسم الحارس: *"), 0, 0)
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("الاسم رباعي أو ثلاثي")
        g1.addWidget(self.txt_name, 0, 1)

        g1.addWidget(QLabel("الرقم القومي (14 رقم):"), 1, 0)
        self.txt_nid = QLineEdit()
        self.txt_nid.setMaxLength(14)
        self.txt_nid.setPlaceholderText("14 رقماً")
        g1.addWidget(self.txt_nid, 1, 1)

        g1.addWidget(QLabel("رقم الهاتف المحمول:"), 2, 0)
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("01xxxxxxxxx")
        g1.addWidget(self.txt_phone, 2, 1)

        layout.addWidget(grp_guard)

        # 2. Assignment Group
        grp_assign = QGroupBox("🏫 التكليف والمدرسة المعين بها")
        g2 = QGridLayout(grp_assign)
        g2.setSpacing(12)

        g2.addWidget(QLabel("المدرسة المكلف بها:"), 0, 0)
        self.combo_school = QComboBox()
        self.combo_school.addItem("— بدون تكليف حالي —", None)
        
        # Populate schools
        all_schools = self.school_service.get_schools()
        for s in all_schools:
            display_text = f"{s['school_name']} ({s['administration']})"
            self.combo_school.addItem(display_text, s["school_id"])
        
        g2.addWidget(self.combo_school, 0, 1)

        g2.addWidget(QLabel("عنوان المدرسة / التكليف:"), 1, 0)
        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("العنوان المسجل في الكشف")
        g2.addWidget(self.txt_address, 1, 1)

        layout.addWidget(grp_assign)

        # 3. Notes Group
        grp_notes = QGroupBox("📝 ملاحظات إضافية")
        gn = QVBoxLayout(grp_notes)
        self.txt_notes = QTextEdit()
        self.txt_notes.setFixedHeight(65)
        gn.addWidget(self.txt_notes)
        layout.addWidget(grp_notes)

        # Action buttons
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self.btn_save = QPushButton("💾 حفظ البيانات")
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.setMinimumHeight(38)
        self.btn_save.clicked.connect(self.save_guard)
        btn_bar.addWidget(self.btn_save)

        btn_cancel = QPushButton("إلغاء الأمر")
        btn_cancel.setObjectName("SecondaryBtn")
        btn_cancel.setMinimumHeight(38)
        btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(btn_cancel)

        layout.addLayout(btn_bar)

    def load_guard_data(self):
        guard = self.guard_service.get_guard_by_id(self.guard_id)
        if not guard:
            return

        self.txt_name.setText(guard.get("guard_name", ""))
        self.txt_nid.setText(guard.get("national_id", "") if guard.get("national_id") != "0" else "")
        self.txt_phone.setText(guard.get("phone", ""))
        self.txt_notes.setText(guard.get("notes", ""))

        assignments = guard.get("assignments", [])
        if assignments:
            first = assignments[0]
            target_sid = first.get("school_id")
            for i in range(self.combo_school.count()):
                if self.combo_school.itemData(i) == target_sid:
                    self.combo_school.setCurrentIndex(i)
                    break
            self.txt_address.setText(first.get("address", ""))

    def save_guard(self):
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "حقل مطلوب", "يرجى كتابة اسم الحارس للمتابعة.")
            self.txt_name.setFocus()
            return

        nid = self.txt_nid.text().strip() or "0"
        if nid != "0" and len(nid) != 14:
            reply = QMessageBox.question(
                self,
                "تنبيه الرقم القومي",
                f"الرقم القومي المدخل يتكون من ({len(nid)}) أرقام وليس 14 رقماً.\nهل تريد المتابعة وحفظه على أي حال؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.txt_nid.setFocus()
                return

        phone = self.txt_phone.text().strip()
        notes = self.txt_notes.toPlainText().strip()
        school_id = self.combo_school.currentData()
        address = self.txt_address.text().strip()

        if self.guard_id:
            self.guard_service.update_guard(
                guard_id=self.guard_id,
                guard_name=name,
                national_id=nid,
                phone=phone,
                notes=notes,
                school_id=school_id,
                address=address
            )
        else:
            self.guard_service.add_guard(
                guard_name=name,
                national_id=nid,
                phone=phone,
                notes=notes,
                school_id=school_id,
                address=address
            )

        self.data_saved.emit()
        self.accept()

