import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QProgressBar, QTextEdit, QComboBox, QGroupBox, 
    QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
from config import PALETTE
from excel_importer import ExcelImporter, ImportResult
from database import DatabaseManager
from generate_sample_data import generate_sample_excel
from ui.admin_mapping_dialog import SmartAdminMappingDialog
from typing import Optional, Dict

class ImportWorkerThread(QThread):
    progress = Signal(int, str)
    finished_import = Signal(object)
    failed = Signal(str)

    def __init__(self, importer: ExcelImporter, file_path: str, mode: str, admin_mapping: Optional[Dict[str, str]] = None):
        super().__init__()
        self.importer = importer
        self.file_path = file_path
        self.mode = mode
        self.admin_mapping = admin_mapping

    def run(self):
        try:
            def on_progress(pct: int, msg: str):
                self.progress.emit(pct, msg)

            result = self.importer.import_excel_file(
                self.file_path, 
                progress_callback=on_progress,
                target_mode=self.mode,
                admin_mapping=self.admin_mapping
            )
            self.finished_import.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class ExcelImportDialog(QDialog):
    """Modern Excel Import Modal Dialog with Async Worker & Progress Bar."""
    data_imported_signal = Signal()

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.importer = ExcelImporter(db_manager)
        self.selected_file_path = ""
        self.worker = None

        self.setWindowTitle("استيراد بيانات من ملف إكسيل (Excel Bulk Import)")
        self.resize(620, 500)
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title Header
        title_label = QLabel("استيراد سجلات العاملين، المستبعدين، والمسجونين")
        title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {PALETTE['primary']};")
        layout.addWidget(title_label)

        desc_label = QLabel(
            "يمكنك استيراد ملف إكسيل يحتوي على أوراق عمل متعددة (مستبعدين / مسجونين) "
            "أو ورقة عمل واحدة. سيقوم النظام بمطابقة الأعمدة آلياً وفحص التكرارات بدون توقف."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc_label)

        # File Selection Frame
        file_group = QGroupBox("اختيار الملف")
        file_layout = QVBoxLayout(file_group)

        file_h_layout = QHBoxLayout()
        self.file_path_label = QLabel("لم يتم تحديد أي ملف حتى الآن...")
        self.file_path_label.setStyleSheet("color: #64748B; font-style: italic; border: 1px dashed #CBD5E1; padding: 8px; border-radius: 6px; background: #F8FAFC;")
        file_h_layout.addWidget(self.file_path_label, 1)

        browse_btn = QPushButton("📁 استعراض الملف...")
        browse_btn.setObjectName("SecondaryBtn")
        browse_btn.clicked.connect(self.browse_file)
        file_h_layout.addWidget(browse_btn)

        file_layout.addLayout(file_h_layout)

        # Mode Selection
        mode_h_layout = QHBoxLayout()
        mode_label = QLabel("نمط الاستيراد:")
        mode_label.setStyleSheet("font-weight: 600;")
        mode_h_layout.addWidget(mode_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("كشف تلقائي حسب أسماء الأوراق والأعمدة (موصى به)", "auto")
        self.mode_combo.addItem("استيراد كبيانات مستبعدين فقط", "excluded")
        self.mode_combo.addItem("استيراد كبيانات مسجونين فقط", "prisoners")
        mode_h_layout.addWidget(self.mode_combo, 1)

        file_layout.addLayout(mode_h_layout)
        layout.addWidget(file_group)

        # Progress Section
        progress_group = QGroupBox("حالة المعالجة ومجريات الاستيراد")
        progress_layout = QVBoxLayout(progress_group)

        self.status_label = QLabel("في انتظار بدء الاستيراد...")
        self.status_label.setStyleSheet(f"color: {PALETTE['text_muted']}; font-weight: 600;")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(110)
        self.log_text.setPlaceholderText("ستظهر هنا تفاصيل السجلات المعالجة وأية أخطاء أو تنبيهات...")
        progress_layout.addWidget(self.log_text)

        layout.addWidget(progress_group)

        # Bottom Buttons
        btn_layout = QHBoxLayout()

        sample_btn = QPushButton("📄 إنشاء نموذج إكسيل تجريبي جاهز")
        sample_btn.setObjectName("SecondaryBtn")
        sample_btn.setToolTip("إنشاء ملف إكسيل يحتوي على أوراق عمل منسقة للاستبعاد والسجن للتجربة الفورية")
        sample_btn.clicked.connect(self.create_template_excel)
        btn_layout.addWidget(sample_btn)

        reimport_btn = QPushButton("🔄 مسح الكل وإعادة الاستيراد")
        reimport_btn.setObjectName("DangerBtn")
        reimport_btn.setToolTip("مسح جميع البيانات من قاعدة البيانات ثم استيراد الملف المحدد من جديد")
        reimport_btn.clicked.connect(self.clear_and_reimport)
        btn_layout.addWidget(reimport_btn)

        btn_layout.addStretch()

        self.import_btn = QPushButton("🚀 بدء الاستيراد الفوري")
        self.import_btn.setObjectName("PrimaryBtn")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.start_import)
        btn_layout.addWidget(self.import_btn)

        close_btn = QPushButton("إغلاق")
        close_btn.setObjectName("SecondaryBtn")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف الإكسيل",
            "",
            "Excel Files (*.xlsx *.xls *.xlsb);;All Files (*.*)"
        )
        if file_path:
            self.selected_file_path = file_path
            self.file_path_label.setText(Path(file_path).name)
            self.file_path_label.setStyleSheet("color: #0F172A; font-weight: bold; border: 1px solid #93C5FD; padding: 8px; border-radius: 6px; background: #EFF6FF;")
            self.import_btn.setEnabled(True)
            self.status_label.setText("الملف محدد وجاهز للاستيراد.")

    def create_template_excel(self):
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ نموذج الإكسيل التجريبي",
            "نموذج_بيانات_المستبعدين_والمسجونين.xlsx",
            "Excel Files (*.xlsx)"
        )
        if save_path:
            try:
                generate_sample_excel(save_path)
                QMessageBox.information(
                    self, 
                    "تم الحفظ بنجاح", 
                    f"تم إنشاء نموذج الإكسيل النموذجي بنجاح في المسار:\n{save_path}\nيمكنك الآن تعديله أو استيراده مباشرة."
                )
                self.selected_file_path = save_path
                self.file_path_label.setText(Path(save_path).name)
                self.file_path_label.setStyleSheet("color: #0F172A; font-weight: bold; border: 1px solid #93C5FD; padding: 8px; border-radius: 6px; background: #EFF6FF;")
                self.import_btn.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر إنشاء الملف: {str(e)}")

    def start_import(self):
        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد ملف إكسيل صالح أولاً.")
            return

        mode = self.mode_combo.currentData()

        # Step 1: Scan for Administrations in Excel file
        self.status_label.setText("جاري فحص الإدارات بالملف...")
        detected_admins = self.importer.scan_administrations(self.selected_file_path, mode)

        admin_mapping = None
        if detected_admins:
            existing_rows = self.db.get_administrations()
            existing_names = [r["name"] for r in existing_rows]

            # Open Smart Mapping Dialog
            mapping_dialog = SmartAdminMappingDialog(detected_admins, existing_names, self)
            if mapping_dialog.exec() != QDialog.Accepted:
                self.status_label.setText("تم إلغاء الاستيراد من قبل المستخدم.")
                return
            admin_mapping = mapping_dialog.get_mappings()

        self.import_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("جاري تهيئة عملية الاستيراد...")
        self.log_text.clear()

        self.worker = ImportWorkerThread(self.importer, self.selected_file_path, mode, admin_mapping)
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished_import.connect(self.on_worker_finished)
        self.worker.failed.connect(self.on_worker_failed)
        self.worker.start()

    def on_worker_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_label.setText(msg)

    def on_worker_finished(self, result: ImportResult):
        self.import_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        summary = result.summary_arabic()
        self.status_label.setText("اكتمل الاستيراد بنجاح!")
        self.log_text.setText(summary)

        self.data_imported_signal.emit()

        if result.success:
            QMessageBox.information(self, "نجاح الاستيراد", summary)
        else:
            QMessageBox.warning(self, "تنبيه الاستيراد", summary)

    def on_worker_failed(self, error_msg: str):
        self.import_btn.setEnabled(True)
        self.status_label.setText("حدث خطأ أثناء الاستيراد.")
        self.log_text.setText(f"خطأ: {error_msg}")
        QMessageBox.critical(self, "خطأ بالاستيراد", f"فشلت عملية الاستيراد:\n{error_msg}")

    def clear_and_reimport(self):
        """Clears ALL data from the database then starts a fresh import."""
        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد ملف إكسيل أولاً قبل إعادة الاستيراد.")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد مسح وإعادة الاستيراد",
            "⚠️ تحذير هام:\n\n"
            "سيتم مسح جميع البيانات الحالية من قاعدة البيانات نهائياً\n"
            "(موظفين، مستبعدين، مسجونين)\n"
            "ثم إعادة استيراد البيانات من الملف المحدد.\n\n"
            "هل أنت متأكد من المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                self.status_label.setText("جاري مسح قاعدة البيانات بالكامل...")
                self.log_text.setText("⏳ جاري مسح جميع السجلات القديمة...\n")
                self.db.clear_all_data()
                self.log_text.append("✅ تم مسح قاعدة البيانات بنجاح.\n")
                self.log_text.append("🔄 جاري بدء الاستيراد من جديد...\n")
                # Start import
                self.start_import()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر مسح قاعدة البيانات:\n{str(e)}")
