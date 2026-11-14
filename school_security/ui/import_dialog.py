# -*- coding: utf-8 -*-
"""
Excel Import Dialog for School Security Management System.
Features:
- Single-file and Multi-file Bulk Selection (select dozens of Excel files at once!)
- Real-time pre-inspection and summary of schools and guards across all chosen files
- Mode selection (Add and Update, Add New, Update Existing, Skip)
- Progress tracking and live console logging
- Asynchronous non-freezing QThread execution
"""
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFileDialog, QRadioButton,
    QButtonGroup, QGroupBox, QMessageBox, QFrame, QListWidget
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
        self.selected_files: List[str] = []

        self.setWindowTitle("📥 استيراد كشوف تأمين المدارس وحراس الأمن (Excel Bulk Import)")
        self.resize(750, 680)
        self.setLayoutDirection(Qt.RightToLeft)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

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
            "يمكنك الآن اختيار ملف واحد أو عدة ملفات إكسيل دفعة واحدة. يقوم النظام بفحص كافة الملفات، "
            "ومطابقة الأعمدة آلياً، وتحديث بيانات المدارس وربط حراس الأمن بمدارسهم دفعة واحدة دون تجميد."
        )
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("font-size: 12px; color: #475569;")
        t_lay.addWidget(lbl_h)
        t_lay.addWidget(lbl_sub)
        layout.addWidget(title_card)

        # 1. File Selection Group (Multi-file enabled)
        grp_file = QGroupBox("📁 ملفات الإكسيل المصدر (يمكنك تحديد ملف أو عدة ملفات دفعة واحدة)")
        f_lay = QVBoxLayout(grp_file)
        f_lay.setSpacing(8)

        top_h = QHBoxLayout()
        self.lbl_file_count = QLabel("لم يتم تحديد أي ملفات حتى الآن...")
        self.lbl_file_count.setStyleSheet(
            "color: #64748B; font-style: italic; background: #F8FAFC; border: 1px dashed #CBD5E1; padding: 6px 12px; border-radius: 6px;"
        )
        top_h.addWidget(self.lbl_file_count, 1)

        self.btn_browse = QPushButton("📂 استعراض واختيار ملفات...")
        self.btn_browse.setObjectName("PrimaryBtn")
        self.btn_browse.setMinimumHeight(34)
        self.btn_browse.setToolTip("تحديد ملف أو عدة ملفات إكسيل معاً عبر نافذة الاختيار")
        self.btn_browse.clicked.connect(self.browse_files)
        top_h.addWidget(self.btn_browse)

        self.btn_add_more = QPushButton("➕ إضافة ملفات أخرى")
        self.btn_add_more.setObjectName("SecondaryBtn")
        self.btn_add_more.setMinimumHeight(34)
        self.btn_add_more.setEnabled(False)
        self.btn_add_more.setToolTip("إضافة ملفات إضافية إلى القائمة الحالية")
        self.btn_add_more.clicked.connect(self.add_more_files)
        top_h.addWidget(self.btn_add_more)

        self.btn_clear_list = QPushButton("🗑️ تفريغ")
        self.btn_clear_list.setObjectName("DangerBtn")
        self.btn_clear_list.setMinimumHeight(34)
        self.btn_clear_list.setEnabled(False)
        self.btn_clear_list.setToolTip("مسح القائمة الحالية لاختيار ملفات أخرى")
        self.btn_clear_list.clicked.connect(self.clear_files_list)
        top_h.addWidget(self.btn_clear_list)

        f_lay.addLayout(top_h)

        # Files List Widget
        self.files_list_widget = QListWidget()
        self.files_list_widget.setFixedHeight(85)
        self.files_list_widget.setStyleSheet("""
            QListWidget {
                background: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #F1F5F9;
            }
            QListWidget::item:hover {
                background: #EFF6FF;
            }
        """)
        f_lay.addWidget(self.files_list_widget)
        layout.addWidget(grp_file)

        # 2. Import Modes Group
        grp_mode = QGroupBox("⚙️ وضع المعالجة وقرار التكرار")
        m_lay = QVBoxLayout(grp_mode)
        m_lay.setSpacing(6)

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
        p_lay.setSpacing(6)

        self.status_lbl = QLabel("جاهز وفي انتظار اختيار الملفات...")
        self.status_lbl.setStyleSheet("font-weight: bold; color: #334155;")
        p_lay.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        p_lay.addWidget(self.progress_bar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(125)
        self.log_area.setPlaceholderText("ستظهر هنا تفاصيل فحص أوراق العمل وسجل المعالجة...")
        self.log_area.setStyleSheet(
            "background: #0F172A; color: #F8FAFC; font-family: Consolas, monospace; font-size: 11px; padding: 6px; border-radius: 6px;"
        )
        p_lay.addWidget(self.log_area)
        layout.addWidget(grp_prog)

        # 4. Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_clear_reimport = QPushButton("🔄 مسح الكل وإعادة الاستيراد")
        self.btn_clear_reimport.setObjectName("DangerBtn")
        self.btn_clear_reimport.setMinimumHeight(40)
        self.btn_clear_reimport.setEnabled(False)
        self.btn_clear_reimport.setToolTip("مسح كافة سجلات المدارس والحراس الحالية وإعادة استيراد هذه الملفات من الصفر")
        self.btn_clear_reimport.clicked.connect(self.clear_and_reimport)
        btn_bar.addWidget(self.btn_clear_reimport)

        btn_bar.addStretch()

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

    @property
    def selected_file(self) -> str:
        """Backwards compatibility property returning the first selected file."""
        return self.selected_files[0] if self.selected_files else ""

    def set_file_path(self, file_path: str):
        """Sets a single file path (backwards compatibility)."""
        if file_path:
            self.set_file_paths([file_path])

    def set_file_paths(self, file_paths: List[str]):
        """Sets the selected files list and initiates preview inspection."""
        valid_paths = [str(f) for f in file_paths if f and Path(f).exists()]
        if not valid_paths:
            self.clear_files_list()
            return

        self.selected_files = valid_paths
        self.files_list_widget.clear()

        for p in self.selected_files:
            try:
                sz_kb = Path(p).stat().st_size / 1024
                self.files_list_widget.addItem(f"📄 {Path(p).name}  ({sz_kb:.1f} KB)")
            except Exception:
                self.files_list_widget.addItem(f"📄 {Path(p).name}")

        count = len(self.selected_files)
        if count == 1:
            self.lbl_file_count.setText(f"📁 تم اختيار ملف واحد: {Path(self.selected_files[0]).name}")
        else:
            self.lbl_file_count.setText(f"📁 تم اختيار {count} ملفات إكسيل دفعة واحدة")

        self.lbl_file_count.setStyleSheet(
            "color: #1E3A8A; font-weight: bold; background: #EFF6FF; border: 1.5px solid #3B82F6; padding: 6px 12px; border-radius: 6px;"
        )
        self.btn_add_more.setEnabled(True)
        self.btn_clear_list.setEnabled(True)

        self._inspect_and_preview_files()

    def browse_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "اختر ملفات بيانات تأمين المدارس (يمكنك تحديد عدة ملفات دفعة واحدة)",
            "",
            "Excel Files (*.xlsx *.xlsm *.xlsb *.xls);;All Files (*.*)"
        )
        if not file_paths:
            return
        self.set_file_paths(file_paths)

    def add_more_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "إضافة ملفات إكسيل أخرى إلى القائمة",
            "",
            "Excel Files (*.xlsx *.xlsm *.xlsb *.xls);;All Files (*.*)"
        )
        if not file_paths:
            return
        existing_set = set(self.selected_files)
        new_files = [f for f in file_paths if f not in existing_set]
        if new_files:
            self.set_file_paths(self.selected_files + new_files)

    def clear_files_list(self):
        self.selected_files = []
        self.files_list_widget.clear()
        self.lbl_file_count.setText("لم يتم تحديد أي ملفات حتى الآن...")
        self.lbl_file_count.setStyleSheet(
            "color: #64748B; font-style: italic; background: #F8FAFC; border: 1px dashed #CBD5E1; padding: 6px 12px; border-radius: 6px;"
        )
        self.btn_add_more.setEnabled(False)
        self.btn_clear_list.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_clear_reimport.setEnabled(False)
        self.status_lbl.setText("تم تفريغ القائمة. يرجى اختيار ملفات للاستيراد.")
        self.log_area.clear()

    def _inspect_and_preview_files(self):
        self.log_area.clear()
        total_files = len(self.selected_files)
        self.log_area.append(f"📁 بدء فحص عدد ({total_files}) ملفات إكسيل مختارة...")

        total_schools_found = 0
        total_guards_found = 0
        valid_files_count = 0

        for idx, f_path in enumerate(self.selected_files, 1):
            fname = Path(f_path).name
            try:
                importer = SchoolSecurityExcelImporter(f_path)
                schools = importer.parse_schools()
                guards = importer.parse_guards()
                s_count = len(schools)
                g_count = len(guards)
                total_schools_found += s_count
                total_guards_found += g_count
                valid_files_count += 1
                self.log_area.append(f"  [{idx}/{total_files}] ✅ {fname}: {s_count} مدرسة، {g_count} حارس")
            except Exception as e:
                self.log_area.append(f"  [{idx}/{total_files}] ⚠️ {fname}: تعذر القراءة ({e})")

        self.log_area.append(
            f"\n📊 إجمالي المكتشف: {total_schools_found} مدرسة | {total_guards_found} حارس أمن عبر {valid_files_count} ملف صالح."
        )

        if total_schools_found > 0 or total_guards_found > 0:
            self.status_lbl.setText(f"جاهز للاستيراد: {total_schools_found} مدرسة و {total_guards_found} حارس عبر {total_files} ملف.")
            self.btn_start.setEnabled(True)
            self.btn_clear_reimport.setEnabled(True)
        else:
            self.status_lbl.setText("لم يتم العثور على أية سجلات مطابقة في الملفات المحددة.")
            self.btn_start.setEnabled(False)
            self.btn_clear_reimport.setEnabled(False)

    def clear_and_reimport(self):
        if not self.selected_files:
            return

        total_files = len(self.selected_files)
        reply = QMessageBox.warning(
            self,
            "تأكيد مسح البيانات وإعادة الاستيراد",
            f"هل أنت متأكد من رغبتك في مسح كافة سجلات المدارس والحراس الحالية نهائياً من قاعدة البيانات، ثم إعادة استيراد جميع الملفات المحددة ({total_files} ملف) بالكامل من الصفر؟\n\nلا يمكن التراجع عن هذه الخطوة.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.db.clear_all_security_data()
            self.log_area.append("🗑️ تم مسح كافة بيانات تأمين المدارس والحراس السابقة بنجاح.")
            self.start_import(forced_mode="add_and_update")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل مسح البيانات السابقة:\n{e}")

    def start_import(self, forced_mode: Optional[str] = None):
        if not self.selected_files:
            return

        if forced_mode:
            mode = forced_mode
        else:
            mode = "add_and_update"
            if self.rad_add_new.isChecked():
                mode = "add_new"
            elif self.rad_update_only.isChecked():
                mode = "update_existing"
            elif self.rad_skip_all.isChecked():
                mode = "skip_duplicates"

        self.btn_start.setEnabled(False)
        self.btn_clear_reimport.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.btn_add_more.setEnabled(False)
        self.btn_clear_list.setEnabled(False)
        self.progress_bar.setValue(2)
        self.status_lbl.setText(f"جاري استيراد {len(self.selected_files)} ملفات في الخلفية...")

        self.worker = SchoolSecurityImportWorker(self.db, self.selected_files, mode)
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
        self.status_lbl.setText("اكتمل الاستيراد بنجاح تام لكافة الملفات!")
        self.btn_start.setEnabled(True)
        self.btn_clear_reimport.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.btn_add_more.setEnabled(True)
        self.btn_clear_list.setEnabled(True)

        self.log_area.append("\n" + result.summary_message())
        self.import_completed.emit()
        QMessageBox.information(self, "نجاح الاستيراد الجماعي", result.summary_message())
        self.accept()

    def on_worker_failed(self, err_msg: str):
        self.progress_bar.setValue(0)
        self.status_lbl.setText("فشلت عملية الاستيراد!")
        self.btn_start.setEnabled(True)
        self.btn_clear_reimport.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.btn_add_more.setEnabled(True)
        self.btn_clear_list.setEnabled(True)
        self.log_area.append(f"\n❌ خطأ فادح: {err_msg}")
        QMessageBox.critical(self, "فشل الاستيراد", f"حدث خطأ أثناء حفظ البيانات:\n{err_msg}")
