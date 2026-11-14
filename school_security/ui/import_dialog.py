# -*- coding: utf-8 -*-
"""
Excel Import Dialog for School Security Management System.
Features:
- File selection and preview of detected sheets
- Mode selection (Add and Update, Add New, Update Existing, Skip)
- Progress tracking and live console logging
- Asynchronous non-freezing QThread execution
"""
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFileDialog, QRadioButton,
    QButtonGroup, QGroupBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal

from ..database import SchoolSecurityDatabaseManager
from ..services.excel_importer import SchoolSecurityExcelImporter
from ..services.import_worker import SchoolSecurityImportWorker
from ..models import ImportResult


class SchoolSecurityImportDialog(QDialog):
    import_completed = Signal()

    def __init__(self, db_manager: SchoolSecurityDatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.worker: Optional[SchoolSecurityImportWorker] = None
        self.selected_file: str = ""

        self.setWindowTitle("📥 استيراد كشوف تأمين المدارس وحراس الأمن (Excel Bulk Import)")
        self.resize(720, 620)
        self.setLayoutDirection(Qt.RightToLeft)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title Card
        title_card = QFrame()
        title_card.setStyleSheet("""
            QFrame {
                background-color: #EFF6FF;
                border: 1.5px solid #BFDBFE;
                border-radius: 10px;
                padding: 12px;
                border-right: 5px solid #1E40AF;
            }
        """)
        t_lay = QVBoxLayout(title_card)
        t_lay.setSpacing(4)
        lbl_h = QLabel("📥 استيراد كشوف تأمين المدارس وبيان حراس الأمن آلياً")
        lbl_h.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E3A8A;")
        lbl_sub = QLabel(
            "يقوم النظام بفحص أوراق العمل ومطابقة الأعمدة آلياً، وقراءة وتحديث بيانات المدارس "
            "وربط حراس الأمن بمدارسهم مع الحفاظ الكامل على سلامة البيانات."
        )
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("font-size: 12px; color: #475569;")
        t_lay.addWidget(lbl_h)
        t_lay.addWidget(lbl_sub)
        layout.addWidget(title_card)

        # 1. File Selection Group
        grp_file = QGroupBox("📁 ملف الإكسيل المصدر")
        f_lay = QHBoxLayout(grp_file)
        self.lbl_file = QLabel("لم يتم اختيار أي ملف حتى الآن...")
        self.lbl_file.setStyleSheet("color: #64748B; font-style: italic; background: #F8FAFC; border: 1px dashed #CBD5E1; padding: 8px 12px; border-radius: 6px;")
        f_lay.addWidget(self.lbl_file, 1)

        self.btn_browse = QPushButton("استعراض الملف...")
        self.btn_browse.setObjectName("SecondaryBtn")
        self.btn_browse.setMinimumHeight(36)
        self.btn_browse.clicked.connect(self.browse_file)
        f_lay.addWidget(self.btn_browse)
        layout.addWidget(grp_file)

        # 2. Import Modes Group
        grp_mode = QGroupBox("⚙️ وضع المعالجة وقرار التكرار")
        m_lay = QVBoxLayout(grp_mode)
        m_lay.setSpacing(8)

        self.btn_group = QButtonGroup(self)
        self.rad_add_update = QRadioButton("🔄 إضافة المدارس والحراس الجدد وتحديث المسجلين مسبقاً (موصى به)")
        self.rad_add_new = QRadioButton("➕ إضافة السجلات الجديدة فقط وتخطي المسجل مسبقاً دون تعديل")
        self.rad_update_only = QRadioButton("✏️ تحديث بيانات المسجلين مسبقاً فقط بالبيانات الأحدث")
        self.rad_skip_all = QRadioButton("⏭️ تخطي واستثناء أي سجل مكرر")

        self.rad_add_update.setChecked(True)
        self.btn_group.addButton(self.rad_add_update)
        self.btn_group.addButton(self.rad_add_new)
        self.btn_group.addButton(self.rad_update_only)
        self.btn_group.addButton(self.rad_skip_all)

        m_lay.addWidget(self.rad_add_update)
        m_lay.addWidget(self.rad_add_new)
        m_lay.addWidget(self.rad_update_only)
        m_lay.addWidget(self.rad_skip_all)
        layout.addWidget(grp_mode)

        # 3. Progress and Log Group
        grp_prog = QGroupBox("📊 حالة المعالجة وسجل العمليات")
        p_lay = QVBoxLayout(grp_prog)
        p_lay.setSpacing(8)

        self.status_lbl = QLabel("جاهز وفي انتظار اختيار الملف...")
        self.status_lbl.setStyleSheet("font-weight: bold; color: #334155;")
        p_lay.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        p_lay.addWidget(self.progress_bar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(120)
        self.log_area.setPlaceholderText("ستظهر هنا تفاصيل فحص أوراق العمل وسجل المعالجة...")
        self.log_area.setStyleSheet("background: #0F172A; color: #F8FAFC; font-family: Consolas, monospace; font-size: 11px; padding: 6px; border-radius: 6px;")
        p_lay.addWidget(self.log_area)

        layout.addWidget(grp_prog)

        # 4. Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_start = QPushButton("🚀 بدء عملية الاستيراد الآن")
        self.btn_start.setObjectName("PrimaryBtn")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_import)
        btn_bar.addWidget(self.btn_start, 1)

        self.btn_cancel = QPushButton("إغلاق")
        self.btn_cancel.setObjectName("SecondaryBtn")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.clicked.connect(self.close)
        btn_bar.addWidget(self.btn_cancel)

        layout.addLayout(btn_bar)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف بيانات تأمين المدارس",
            "",
            "Excel Files (*.xlsx *.xlsm *.xlsb);;All Files (*.*)"
        )
        if not file_path:
            return

        self.selected_file = file_path
        self.lbl_file.setText(Path(file_path).name)
        self.lbl_file.setStyleSheet("color: #0F172A; font-weight: bold; background: #EFF6FF; border: 1.5px solid #3B82F6; padding: 8px 12px; border-radius: 6px;")

        self.log_area.append(f"📁 تم اختيار الملف: {Path(file_path).name}")
        self.log_area.append("⏳ جاري استكشاف أوراق العمل ومطابقة الأعمدة...")

        try:
            importer = SchoolSecurityExcelImporter(file_path)
            sch_sheet = importer.schools_sheet_name or "غير محدد"
            grd_sheet = importer.guards_sheet_name or "غير محدد"

            self.log_area.append(f"✅ تم التعرف على ورقة المدارس: «{sch_sheet}»")
            self.log_area.append(f"✅ تم التعرف على ورقة الحراس: «{grd_sheet}»")

            schools_count = len(importer.parse_schools())
            guards_count = len(importer.parse_guards())

            self.log_area.append(f"📊 عدد سجلات المدارس المكتشفة: {schools_count:,}")
            self.log_area.append(f"📊 عدد سجلات الحراس المكتشفة: {guards_count:,}")

            self.status_lbl.setText(f"جاهز للاستيراد: تم العثور على {schools_count} مدرسة و {guards_count} حارس.")
            self.btn_start.setEnabled(True)

        except Exception as e:
            self.log_area.append(f"❌ خطأ أثناء قراءة الملف: {e}")
            QMessageBox.critical(self, "خطأ في قراءة الملف", f"تعذر قراءة ملف الإكسيل:\n{e}")
            self.btn_start.setEnabled(False)

    def start_import(self):
        if not self.selected_file:
            return

        mode = "add_and_update"
        if self.rad_add_new.isChecked():
            mode = "add_new"
        elif self.rad_update_only.isChecked():
            mode = "update_existing"
        elif self.rad_skip_all.isChecked():
            mode = "skip_duplicates"

        self.btn_start.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.progress_bar.setValue(5)
        self.status_lbl.setText("جاري تنفيذ الاستيراد والربط في الخلفية...")

        self.worker = SchoolSecurityImportWorker(self.db, self.selected_file, mode)
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.failed_signal.connect(self.on_worker_failed)
        self.worker.start()

    def on_worker_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.status_lbl.setText(msg)
        self.log_area.append(f"[{val}%] {msg}")

    def on_worker_finished(self, result: ImportResult):
        self.progress_bar.setValue(100)
        self.status_lbl.setText("اكتمل الاستيراد بنجاح تام!")
        self.btn_start.setEnabled(True)
        self.btn_browse.setEnabled(True)

        self.log_area.append("\n" + result.summary_message())
        self.import_completed.emit()
        QMessageBox.information(self, "نجاح الاستيراد", result.summary_message())
        self.accept()

    def on_worker_failed(self, err_msg: str):
        self.progress_bar.setValue(0)
        self.status_lbl.setText("فشلت عملية الاستيراد!")
        self.btn_start.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.log_area.append(f"\n❌ خطأ فادح: {err_msg}")
        QMessageBox.critical(self, "فشل الاستيراد", f"حدث خطأ أثناء حفظ البيانات:\n{err_msg}")
