import io
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QTextEdit, QFileDialog, QMessageBox,
    QScrollArea, QFrame, QSplitter, QProgressBar, QInputDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PySide6.QtGui import QPixmap, QImage, QIcon, QTransform, QKeySequence, QShortcut
from PySide6.QtCore import Qt, Signal, QByteArray, QBuffer

from config import LOGO_PATH, DEFAULT_ADMINISTRATIONS, DEFAULT_CASE_TYPES, PRISONER_STATUSES
from database import DatabaseManager
from ai_vision_extractor import (
    extract_record_from_image, get_saved_api_key, save_api_key, has_active_ai_engine
)


class ImageViewer(QGraphicsView):
    """Interactive Document Image Viewer with zoom, pan, and rotation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item: Optional[QGraphicsPixmapItem] = None
        self.current_zoom = 1.0
        self.current_rotation = 0
        self.original_pixmap: Optional[QPixmap] = None

        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #1E293B;
                border: 1.5px solid #334155;
                border-radius: 8px;
            }
        """)

    def set_image(self, pixmap: QPixmap):
        self.original_pixmap = pixmap
        self.scene.clear()
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.setSceneRect(self.pixmap_item.boundingRect())
        self.reset_view()

    def zoom_in(self):
        self.scale(1.2, 1.2)
        self.current_zoom *= 1.2

    def zoom_out(self):
        self.scale(0.833, 0.833)
        self.current_zoom *= 0.833

    def rotate_90(self):
        self.rotate(90)
        self.current_rotation = (self.current_rotation + 90) % 360

    def reset_view(self):
        self.resetTransform()
        self.current_zoom = 1.0
        self.current_rotation = 0
        if self.original_pixmap and not self.original_pixmap.isNull():
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)


class SmartScanDialog(QDialog):
    """
    Split-screen intelligent document scan and verification dialog.
    Image on the right with pan/zoom; extracted editable fields on the left.
    """
    record_added_signal = Signal()

    def __init__(self, db: DatabaseManager, default_record_type: str = "excluded", parent=None):
        super().__init__(parent)
        self.db = db
        self.default_record_type = default_record_type
        self.current_image_bytes: Optional[bytes] = None
        self.current_mime_type = "image/jpeg"

        self.setWindowTitle("📷 المسح الضوئي الذكي للمستندات الحكومية — مراجعة وتدقيق قبل الحفظ")
        self.resize(1200, 780)
        self.setMinimumSize(950, 650)
        self.setLayoutDirection(Qt.RightToLeft)
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        self.init_ui()

        # Keyboard shortcut for paste
        paste_sc = QShortcut(QKeySequence("Ctrl+V"), self)
        paste_sc.activated.connect(self.paste_from_clipboard)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # 1. Header Banner
        header = QHBoxLayout()
        header.setSpacing(12)

        if LOGO_PATH.exists():
            emblem = QLabel()
            pix = QPixmap(str(LOGO_PATH)).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            emblem.setPixmap(pix)
            header.addWidget(emblem)

        title_v = QVBoxLayout()
        title_v.setSpacing(2)
        t1 = QLabel("مديرية التربية والتعليم بالإسكندرية — وحدة المسح الضوئي المحلي")
        t1.setStyleSheet("color: #64748B; font-size: 11px; font-weight: bold;")
        t2 = QLabel("استخراج وتدقيق بيانات المستندات والقرارات الرسمية قبل الحفظ (أوفلاين)")
        t2.setStyleSheet("color: #1E40AF; font-size: 15px; font-weight: bold;")
        title_v.addWidget(t1)
        title_v.addWidget(t2)
        header.addLayout(title_v)

        header.addStretch()

        # Engine Status Badge & API Settings Button
        self.engine_badge = QLabel()
        self.update_engine_badge()
        header.addWidget(self.engine_badge)

        self.api_key_btn = QPushButton("⚙️ إعدادات الذكاء الاصطناعي (API Key)")
        self.api_key_btn.setCursor(Qt.PointingHandCursor)
        self.api_key_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #1E293B;
                border: 1.5px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #94A3B8;
            }
        """)
        self.api_key_btn.clicked.connect(self.open_api_settings_dialog)
        header.addWidget(self.api_key_btn)

        main_layout.addLayout(header)

        # 2. Main Splitter (Right: Image Viewer | Left: Verification Form)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #CBD5E1;
                width: 3px;
            }
        """)

        # --- Right Panel: Image Viewer & Toolbar ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 6, 0)
        right_layout.setSpacing(8)

        img_toolbar = QHBoxLayout()
        img_toolbar.setSpacing(6)

        open_btn = QPushButton("📁 اختيار صورة")
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E40AF;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        open_btn.clicked.connect(self.open_image_file)
        img_toolbar.addWidget(open_btn)

        paste_btn = QPushButton("📋 لصق من الحافظة (Ctrl+V)")
        paste_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        paste_btn.clicked.connect(self.paste_from_clipboard)
        img_toolbar.addWidget(paste_btn)

        img_toolbar.addStretch()

        zoom_in_btn = QPushButton("➕")
        zoom_in_btn.setToolTip("تكبير")
        zoom_in_btn.setFixedSize(32, 32)
        zoom_in_btn.clicked.connect(lambda: self.image_viewer.zoom_in())
        img_toolbar.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("➖")
        zoom_out_btn.setToolTip("تصغير")
        zoom_out_btn.setFixedSize(32, 32)
        zoom_out_btn.clicked.connect(lambda: self.image_viewer.zoom_out())
        img_toolbar.addWidget(zoom_out_btn)

        rotate_btn = QPushButton("🔄")
        rotate_btn.setToolTip("تدوير 90 درجة")
        rotate_btn.setFixedSize(32, 32)
        rotate_btn.clicked.connect(lambda: self.image_viewer.rotate_90())
        img_toolbar.addWidget(rotate_btn)

        reset_btn = QPushButton("⏹️")
        reset_btn.setToolTip("إعادة ضبط العرض")
        reset_btn.setFixedSize(32, 32)
        reset_btn.clicked.connect(lambda: self.image_viewer.reset_view())
        img_toolbar.addWidget(reset_btn)

        right_layout.addLayout(img_toolbar)

        self.image_viewer = ImageViewer()
        right_layout.addWidget(self.image_viewer, 1)

        # Drop instruction banner
        self.drop_hint = QLabel("💡 يمكنك سحب وإفلات صورة المستند هنا، أو الضغط على Ctrl+V للصق صورة مصورة.")
        self.drop_hint.setStyleSheet("color: #64748B; font-size: 11px;")
        self.drop_hint.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.drop_hint)

        splitter.addWidget(right_panel)

        # --- Left Panel: Extracted Fields Review & Verification Form ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(6, 0, 0, 0)
        left_layout.setSpacing(8)

        # Processing Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #93C5FD;
                border-radius: 4px;
                text-align: center;
                height: 14px;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
            }
        """)
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)

        # Status badge
        self.status_badge = QLabel("يرجى اختيار صورة المستند لبدء الاستخراج والتدقيق...")
        self.status_badge.setStyleSheet("""
            QLabel {
                background-color: #F8FAFC;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        left_layout.addWidget(self.status_badge)

        # Form Scroll Area
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setStyleSheet("QScrollArea { border: 1.5px solid #CBD5E1; border-radius: 8px; background: #FFFFFF; }")

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(14, 14, 14, 14)
        form_layout.setSpacing(10)

        # Record Type Selector
        type_h = QHBoxLayout()
        type_lbl = QLabel("نوع السجل المستخرج:")
        type_lbl.setStyleSheet("font-weight: bold; color: #1E40AF; font-size: 13px;")
        type_h.addWidget(type_lbl)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["قرار استبعاد موظف / معلم", "قضية حبس موظف"])
        if self.default_record_type == "prisoner":
            self.type_combo.setCurrentIndex(1)
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        type_h.addWidget(self.type_combo, 1)
        form_layout.addLayout(type_h)

        # Field: Full Name
        form_layout.addWidget(QLabel("الاسم الكامل (رباعي) *: "))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم الموظف كما هو مدون في المستند")
        self.name_input.textChanged.connect(self.check_duplicate_live)
        form_layout.addWidget(self.name_input)

        # Field: National ID
        nid_h = QHBoxLayout()
        nid_lbl = QLabel("الرقم القومي (14 رقم):")
        nid_lbl.setStyleSheet("font-weight: bold;")
        self.nid_warn_icon = QLabel("")
        self.nid_warn_icon.setStyleSheet("color: #D97706; font-size: 12px; font-weight: bold;")
        nid_h.addWidget(nid_lbl)
        nid_h.addWidget(self.nid_warn_icon)
        nid_h.addStretch()
        form_layout.addLayout(nid_h)

        self.nid_input = QLineEdit()
        self.nid_input.setPlaceholderText("14 رقماً قومياً (أو 0 إذا لم يوجد)")
        self.nid_input.setMaxLength(14)
        self.nid_input.textChanged.connect(self.on_nid_text_changed)
        form_layout.addWidget(self.nid_input)

        # Live Duplicate Warning Banner
        self.dup_banner = QLabel("")
        self.dup_banner.setWordWrap(True)
        self.dup_banner.setStyleSheet("""
            background-color: #FEF3C7;
            color: #92400E;
            border: 1.5px solid #F59E0B;
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 12px;
            font-weight: bold;
        """)
        self.dup_banner.hide()
        form_layout.addWidget(self.dup_banner)

        # Field: Administration & School
        adm_sch_h = QHBoxLayout()
        adm_sch_h.setSpacing(10)

        adm_v = QVBoxLayout()
        adm_v.addWidget(QLabel("الإدارة التعليمية:"))
        self.admin_combo = QComboBox()
        self.admin_combo.addItem("غير محدد", None)
        for adm in self.db.get_administrations():
            self.admin_combo.addItem(adm["name"], adm["id"])
        adm_v.addWidget(self.admin_combo)
        adm_sch_h.addLayout(adm_v, 1)

        sch_v = QVBoxLayout()
        sch_v.addWidget(QLabel("المدرسة / جهة العمل:"))
        self.school_input = QLineEdit()
        self.school_input.setPlaceholderText("اسم المدرسة أو الإدارة التابع لها")
        sch_v.addWidget(self.school_input)
        adm_sch_h.addLayout(sch_v, 1)

        form_layout.addLayout(adm_sch_h)

        # --- Excluded Specific Group ---
        self.excluded_group = QWidget()
        ex_layout = QVBoxLayout(self.excluded_group)
        ex_layout.setContentsMargins(0, 0, 0, 0)
        ex_layout.setSpacing(8)

        jobs_h = QHBoxLayout()
        curr_v = QVBoxLayout()
        curr_v.addWidget(QLabel("الوظيفة الحالية:"))
        self.current_job_input = QLineEdit()
        curr_v.addWidget(self.current_job_input)
        jobs_h.addLayout(curr_v, 1)

        nom_v = QVBoxLayout()
        nom_v.addWidget(QLabel("الوظيفة المرشح لها:"))
        self.nominee_job_input = QLineEdit()
        nom_v.addWidget(self.nominee_job_input)
        jobs_h.addLayout(nom_v, 1)
        ex_layout.addLayout(jobs_h)

        entity_date_h = QHBoxLayout()
        ent_v = QVBoxLayout()
        ent_v.addWidget(QLabel("جهة الاستبعاد:"))
        self.exclusion_entity_input = QLineEdit()
        ent_v.addWidget(self.exclusion_entity_input)
        entity_date_h.addLayout(ent_v, 1)

        date_v = QVBoxLayout()
        date_v.addWidget(QLabel("تاريخ قرار الاستبعاد:"))
        self.exclusion_date_input = QLineEdit()
        self.exclusion_date_input.setPlaceholderText("YYYY-MM-DD")
        date_v.addWidget(self.exclusion_date_input)
        entity_date_h.addLayout(date_v, 1)
        ex_layout.addLayout(entity_date_h)

        ex_layout.addWidget(QLabel("سبب الاستبعاد / ملخص القرار:"))
        self.exclusion_reason_input = QLineEdit()
        ex_layout.addWidget(self.exclusion_reason_input)

        form_layout.addWidget(self.excluded_group)

        # --- Prisoner Specific Group ---
        self.prisoner_group = QWidget()
        pr_layout = QVBoxLayout(self.prisoner_group)
        pr_layout.setContentsMargins(0, 0, 0, 0)
        pr_layout.setSpacing(8)

        case_ruling_h = QHBoxLayout()
        cnum_v = QVBoxLayout()
        cnum_v.addWidget(QLabel("رقم القضية:"))
        self.case_number_input = QLineEdit()
        cnum_v.addWidget(self.case_number_input)
        case_ruling_h.addLayout(cnum_v, 1)

        ruling_v = QVBoxLayout()
        ruling_v.addWidget(QLabel("الحكم الصادر:"))
        self.court_ruling_input = QLineEdit()
        ruling_v.addWidget(self.court_ruling_input)
        case_ruling_h.addLayout(ruling_v, 1)
        pr_layout.addLayout(case_ruling_h)

        status_rel_h = QHBoxLayout()
        stat_v = QVBoxLayout()
        stat_v.addWidget(QLabel("الوضع الراهن:"))
        self.current_status_combo = QComboBox()
        self.current_status_combo.setEditable(True)
        self.current_status_combo.addItems(PRISONER_STATUSES)
        stat_v.addWidget(self.current_status_combo)
        status_rel_h.addLayout(stat_v, 1)

        reldate_v = QVBoxLayout()
        reldate_v.addWidget(QLabel("تاريخ الإفراج (إن وجد):"))
        self.release_date_input = QLineEdit()
        self.release_date_input.setPlaceholderText("YYYY-MM-DD")
        reldate_v.addWidget(self.release_date_input)
        status_rel_h.addLayout(reldate_v, 1)
        pr_layout.addLayout(status_rel_h)

        pr_layout.addWidget(QLabel("مكان التسكين / السجن:"))
        self.housing_input = QLineEdit()
        pr_layout.addWidget(self.housing_input)

        form_layout.addWidget(self.prisoner_group)

        # Common: Case Type Dropdown
        form_layout.addWidget(QLabel("نوع القضية / التصنيف:"))
        self.case_type_combo = QComboBox()
        self.case_type_combo.setEditable(True)
        self.case_type_combo.addItem("غير محدد", None)
        for ct in self.db.get_case_types():
            self.case_type_combo.addItem(ct["name"], ct["id"])
        form_layout.addWidget(self.case_type_combo)

        # Raw Extracted Text View (collapsible)
        form_layout.addWidget(QLabel("النص الكامل للمستند كما قرأه المسح الضوئي (للتدقيق والمقارنة):"))
        self.raw_text_view = QTextEdit()
        self.raw_text_view.setFixedHeight(110)
        self.raw_text_view.setPlaceholderText("سيظهر هنا النص الكامل للمستند...")
        form_layout.addWidget(self.raw_text_view)

        form_scroll.setWidget(form_widget)
        left_layout.addWidget(form_scroll, 1)

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.save_btn = QPushButton("✅ اعتماد وحفظ السجل في المنظومة")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 10px 18px;
            }
            QPushButton:hover { background-color: #15803D; }
        """)
        self.save_btn.clicked.connect(self.save_verified_record)
        btn_bar.addWidget(self.save_btn, 1)

        re_extract_btn = QPushButton("🔄 إعادة الاستخراج")
        re_extract_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                font-weight: bold;
                border-radius: 6px;
                padding: 9px 14px;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        re_extract_btn.clicked.connect(self.trigger_ai_extraction)
        btn_bar.addWidget(re_extract_btn)

        close_btn = QPushButton("إلغاء")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8FAFC;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 9px 14px;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        close_btn.clicked.connect(self.reject)
        btn_bar.addWidget(close_btn)

        left_layout.addLayout(btn_bar)

        splitter.addWidget(left_panel)

        # Set initial splitter ratio: 45% right (image), 55% left (form)
        splitter.setSizes([500, 650])
        main_layout.addWidget(splitter, 1)

        self.on_type_changed(self.type_combo.currentIndex())

    def on_type_changed(self, idx: int):
        if idx == 0:  # Excluded
            self.excluded_group.show()
            self.prisoner_group.hide()
        else:  # Prisoner
            self.excluded_group.hide()
            self.prisoner_group.show()

    def on_nid_text_changed(self):
        nid = self.nid_input.text().strip()
        if not nid or nid == "0":
            self.nid_warn_icon.setText("⚠️ غير مسجل")
        elif len(nid) < 14:
            self.nid_warn_icon.setText(f"⚠️ غير مكتمل ({len(nid)} من 14 رقماً)")
        else:
            self.nid_warn_icon.setText("✅ مكتمل (14 رقماً)")
        self.check_duplicate_live()

    def check_duplicate_live(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip()
        has_nid = bool(nid and nid != "0" and len(nid) >= 6)
        if len(name) >= 3 or has_nid:
            matches = self.db.check_duplicate_employee(name, nid)
            if matches:
                m = matches[0]
                status_list = []
                if m.get("exclusions"):
                    status_list.append(f"{len(m['exclusions'])} قرار استبعاد")
                if m.get("prisoners"):
                    status_list.append(f"{len(m['prisoners'])} قضية حبس")
                st_text = f" ({' و '.join(status_list)})" if status_list else ""
                matched_nid = str(m.get("national_id") or "غير مسجل").strip()
                self.dup_banner.setText(
                    f"⚠️ تنبيه تشابه في قاعدة البيانات: [الاسم: {m['full_name']} | القومي: {matched_nid} | إدارة: {m['administration_name']}]{st_text}"
                )
                self.dup_banner.show()
                return
        self.dup_banner.hide()

    # No API key needed — offline OCR

    def open_image_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختيار صورة المستند الرسمي",
            "",
            "ملفات الصور (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)"
        )
        if file_path:
            self.load_image_from_path(file_path)

    def load_image_from_path(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "خطأ", "تعذر قراءة ملف الصورة المحدد.")
            return

        with open(path, "rb") as f:
            self.current_image_bytes = f.read()

        suffix = Path(path).suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        self.current_mime_type = mime_map.get(suffix, "image/jpeg")

        self.image_viewer.set_image(pixmap)
        self.trigger_ai_extraction()

    def paste_from_clipboard(self):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QBuffer.WriteOnly)
            pixmap.save(buffer, "JPEG", quality=95)
            self.current_image_bytes = bytes(byte_array.data())
            self.current_mime_type = "image/jpeg"
            self.image_viewer.set_image(pixmap)
            self.trigger_ai_extraction()
        else:
            QMessageBox.information(self, "تنبيه", "لا توجد صورة في الحافظة للصقها. يرجى التقاط صورة للشاشة أولاً (Win+Shift+S) أو نسخ صورة.")

    def update_engine_badge(self):
        if has_active_ai_engine():
            self.engine_badge.setText("⚡ ذكاء اصطناعي فائق (Gemini AI) نشط — يقرأ خط اليد")
            self.engine_badge.setStyleSheet("""
                QLabel {
                    background-color: #F0FDF4;
                    color: #15803D;
                    border: 1.5px solid #86EFAC;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
        else:
            self.engine_badge.setText("🔒 مسح محلي (أوفلاين) — للمستندات المطبوعة")
            self.engine_badge.setStyleSheet("""
                QLabel {
                    background-color: #EFF6FF;
                    color: #1D4ED8;
                    border: 1.5px solid #93C5FD;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)

    def open_api_settings_dialog(self):
        current_key = get_saved_api_key()
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        dlg = QDialog(self)
        dlg.setWindowTitle("🔑 إعدادات الذكاء الاصطناعي لقراءة الخط اليدوي")
        dlg.resize(520, 280)
        dlg.setLayoutDirection(Qt.RightToLeft)

        l = QVBoxLayout(dlg)
        l.setContentsMargins(18, 16, 18, 16)
        l.setSpacing(12)

        info = QLabel(
            "⚡ لتفعيل قراءة خط اليد والمستندات المصورة بدقة 100%:\n"
            "يمكنك استخدام مفتاح Google Gemini المجاني بالكامل بدون أي رسوم.\n"
            "1. اضغط على الزر بالأسفل لفتح صفحة المفاتيح في Google AI Studio.\n"
            "2. اضغط 'Create API Key' والصقه في الخانة التالية."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #334155; font-size: 12px; line-height: 1.4;")
        l.addWidget(info)

        open_link_btn = QPushButton("🌐 فتح موقع Google AI Studio للحصول على المفتاح مجاناً")
        open_link_btn.setStyleSheet("""
            QPushButton {
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #DBEAFE; }
        """)
        open_link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://aistudio.google.com/app/apikey")))
        l.addWidget(open_link_btn)

        key_input = QLineEdit()
        key_input.setPlaceholderText("الصق مفتاح API هنا (يبدأ بـ AIzaSy...)")
        key_input.setText(current_key)
        key_input.setStyleSheet("padding: 8px; border: 1.5px solid #CBD5E1; border-radius: 6px; font-size: 13px;")
        l.addWidget(key_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        save_btn = QPushButton("💾 حفظ وتفعيل")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover { background-color: #15803D; }
        """)
        def do_save():
            new_key = key_input.text().strip()
            save_api_key(new_key)
            self.update_engine_badge()
            dlg.accept()
            QMessageBox.information(
                self, "تم التحديث",
                "✅ تم تفعيل محرك الذكاء الاصطناعي الفائق بنجاح!" if new_key else "🔒 تم إلغاء المفتاح والعودة للمحرك المحلي (الأوفلاين)."
            )
        save_btn.clicked.connect(do_save)
        btn_row.addWidget(save_btn)

        if current_key:
            clear_btn = QPushButton("🗑️ مسح المفتاح (العودة للأوفلاين)")
            clear_btn.setStyleSheet("color: #DC2626; padding: 8px 12px; font-weight: bold;")
            def do_clear():
                save_api_key("")
                self.update_engine_badge()
                dlg.accept()
                QMessageBox.information(self, "تم المسح", "🔒 تم مسح المفتاح وسيعمل البرنامج محلياً (أوفلاين).")
            clear_btn.clicked.connect(do_clear)
            btn_row.addWidget(clear_btn)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)

        l.addLayout(btn_row)
        dlg.exec()

    def trigger_ai_extraction(self):
        if not self.current_image_bytes:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار صورة مستند أولاً.")
            return

        self.progress_bar.show()
        is_cloud = has_active_ai_engine()
        engine_txt = "بالذكاء الاصطناعي الفائق (Gemini AI)" if is_cloud else "بالمسح الضوئي المحلي (أوفلاين)"
        self.status_badge.setText(f"⏳ جاري فحص المستند واستخراج البيانات {engine_txt}...")
        self.status_badge.setStyleSheet("background-color: #EFF6FF; color: #1E40AF; border: 1px solid #93C5FD; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        self.setEnabled(False)

        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()

        try:
            data = extract_record_from_image(
                self.current_image_bytes,
                mime_type=self.current_mime_type
            )
            self.populate_fields(data)
            used = data.get("engine_used", "المحرك الذكي")
            self.status_badge.setText(f"🟢 تم استخراج البيانات بنجاح بواسطة [{used}] — يرجى التدقيق والمقارنة بالصورة.")
            self.status_badge.setStyleSheet("background-color: #F0FDF4; color: #16A34A; border: 1px solid #86EFAC; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        except Exception as e:
            self.status_badge.setText("❌ فشل استخراج البيانات من المستند.")
            self.status_badge.setStyleSheet("background-color: #FEF2F2; color: #DC2626; border: 1px solid #FCA5A5; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
            QMessageBox.critical(self, "خطأ في الاستخراج", f"حدث خطأ أثناء فحص الصورة:\n{str(e)}")
        finally:
            self.progress_bar.hide()
            self.setEnabled(True)

    def populate_fields(self, data: Dict[str, Any]):
        # Record Type
        rec_type = data.get("record_type", "excluded")
        if rec_type in ["prisoner", "prisoners", "حبس"]:
            self.type_combo.setCurrentIndex(1)
        else:
            self.type_combo.setCurrentIndex(0)

        # Basic Info
        self.name_input.setText(str(data.get("full_name") or ""))

        nid = str(data.get("national_id") or "0").strip()
        if nid in ["None", "null", "nan", ""]:
            nid = "0"
        self.nid_input.setText(nid)

        # Administration Matching
        adm_name = str(data.get("administration_name") or "").strip()
        if adm_name:
            for idx in range(self.admin_combo.count()):
                if self.admin_combo.itemText(idx) in adm_name or adm_name in self.admin_combo.itemText(idx):
                    self.admin_combo.setCurrentIndex(idx)
                    break

        self.school_input.setText(str(data.get("school") or ""))

        # Excluded specific
        self.current_job_input.setText(str(data.get("current_job") or ""))
        self.nominee_job_input.setText(str(data.get("nominee_job") or ""))
        self.exclusion_entity_input.setText(str(data.get("exclusion_entity") or ""))
        self.exclusion_date_input.setText(str(data.get("exclusion_date") or ""))
        self.exclusion_reason_input.setText(str(data.get("exclusion_reason") or ""))

        # Prisoner specific
        self.case_number_input.setText(str(data.get("case_number") or ""))
        self.court_ruling_input.setText(str(data.get("court_ruling") or ""))
        curr_stat = str(data.get("current_status") or "").strip()
        if curr_stat:
            self.current_status_combo.setCurrentText(curr_stat)
        self.release_date_input.setText(str(data.get("release_date") or ""))
        self.housing_input.setText(str(data.get("housing_location") or ""))

        # Case Type Matching
        case_name = str(data.get("case_type_name") or "").strip()
        if case_name:
            for idx in range(self.case_type_combo.count()):
                if case_name in self.case_type_combo.itemText(idx):
                    self.case_type_combo.setCurrentIndex(idx)
                    break
            else:
                self.case_type_combo.setCurrentText(case_name)

        # Raw Text
        self.raw_text_view.setPlainText(str(data.get("full_extracted_text") or ""))

    def save_verified_record(self):
        name = self.name_input.text().strip()
        nid = self.nid_input.text().strip() or "0"

        if not name:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الموظف على الأقل للمتابعة.")
            return

        # Check duplicate prompt
        matches = self.db.check_duplicate_employee(name, nid)
        if matches:
            m = matches[0]
            matched_nid = str(m.get("national_id") or "غير مسجل").strip()
            details = [
                f"• الاسم المسجل: {m['full_name']}",
                f"• الرقم القومي: {matched_nid}",
                f"• الإدارة: {m['administration_name']}",
                f"• المدرسة: {m['school']}"
            ]
            msg = "⚠️ إنذار: تم العثور على تشابه في بيانات الموظف (الاسم أو الرقم القومي)!\n\n"
            msg += "\n".join(details) + "\n\n"
            msg += "هل أنت متأكد من رغبتك في اعتماد وحفظ هذا السجل للموظف نفسه؟"
            reply = QMessageBox.question(
                self, "تأكيد إضافة سجل مع تشابه بيانات",
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Resolve Case Type
        case_type_id = self.case_type_combo.currentData()
        case_type_text = self.case_type_combo.currentText().strip()
        if not case_type_id and case_type_text and case_type_text != "غير محدد":
            case_type_id = self.db.add_case_type(case_type_text)

        admin_id = self.admin_combo.currentData()

        # Save to DB based on selected record type
        is_prisoner = (self.type_combo.currentIndex() == 1)

        try:
            if not is_prisoner:
                record_data = {
                    "full_name": name,
                    "national_id": nid,
                    "administration_id": admin_id,
                    "school": self.school_input.text().strip(),
                    "case_type_id": case_type_id,
                    "current_job": self.current_job_input.text().strip(),
                    "nominee_job": self.nominee_job_input.text().strip(),
                    "exclusion_entity": self.exclusion_entity_input.text().strip(),
                    "exclusion_date": self.exclusion_date_input.text().strip(),
                    "exclusion_reason": self.exclusion_reason_input.text().strip(),
                }
                self.db.add_excluded_record(record_data)
            else:
                record_data = {
                    "full_name": name,
                    "national_id": nid,
                    "administration_id": admin_id,
                    "school": self.school_input.text().strip(),
                    "case_type_id": case_type_id,
                    "case_number": self.case_number_input.text().strip(),
                    "court_ruling": self.court_ruling_input.text().strip(),
                    "current_status": self.current_status_combo.currentText().strip(),
                    "release_date": self.release_date_input.text().strip(),
                    "housing_location": self.housing_input.text().strip(),
                }
                self.db.add_prisoner_record(record_data)

            QMessageBox.information(
                self, "تم الحفظ بنجاح",
                f"✅ تم تدقيق واعتماد وحفظ سجل ({'المحبوس' if is_prisoner else 'المستبعد'}) بنجاح في المنظومة!"
            )
            self.record_added_signal.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطأ في الحفظ", f"تعذر حفظ السجل في قاعدة البيانات:\n{str(e)}")
