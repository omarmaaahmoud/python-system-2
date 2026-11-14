from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QFrame, QGridLayout, QScrollArea, 
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QButtonGroup
)
from PySide6.QtGui import QIcon, QPixmap
from datetime import datetime
from PySide6.QtCore import Qt, QDate, QTimer
from config import APP_NAME, APP_SUBTITLE, APP_VERSION, PALETTE, LOGO_PATH
from database import DatabaseManager
from ui.excluded_view import ExcludedView
from ui.prisoners_view import PrisonersView
from ui.add_case_view import ManageCaseTypesView
from ui.search_view import AdvancedSearchView
from ui.duplicate_names_view import DuplicateNamesView
from ui.import_dialog import ExcelImportDialog
from ui.smart_scan_dialog import SmartScanDialog

# System 2 Integration
from school_security.database import SchoolSecurityDatabaseManager
from school_security.ui.main_view import SchoolSecurityMainView


class ClickableCard(QFrame):
    """A QFrame that acts as a clickable card with hover effects."""
    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self._callback = callback
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._callback:
            self._callback()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """Main Application Window with Top-Level System Switcher, Dashboard, Sidebar Navigation, and Dynamic Subviews."""
    def __init__(self, db_manager: DatabaseManager, school_security_db: Optional[SchoolSecurityDatabaseManager] = None):
        super().__init__()
        self.db = db_manager
        self.school_security_db = school_security_db or SchoolSecurityDatabaseManager()

        self.setWindowTitle(f"{APP_NAME} - {APP_SUBTITLE}")
        self.resize(1340, 840)
        self.setMinimumSize(1080, 700)
        self.setLayoutDirection(Qt.RightToLeft)

        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        self.init_ui()
        self.refresh_dashboard_stats()

    def init_ui(self):
        # Central Main Widget with Top-Level Vertical Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # 1. Top-Level Dual-System Switcher Bar
        self.top_system_bar = self.create_system_switcher_bar()
        main_vbox.addWidget(self.top_system_bar)

        # 2. Master Stacked Widget for System 1 and System 2
        self.master_system_stack = QStackedWidget()

        # ========================================================
        # SYSTEM 1: Exclusions & Prisoners System Container
        # ========================================================
        self.system1_widget = QWidget()
        s1_layout = QHBoxLayout(self.system1_widget)
        s1_layout.setContentsMargins(0, 0, 0, 0)
        s1_layout.setSpacing(0)

        # 1. Sidebar Navigation
        self.sidebar = self.create_sidebar()
        s1_layout.addWidget(self.sidebar)

        # 2. Main Content Area (Header + QStackedWidget)
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header Bar
        header = self.create_header()
        content_layout.addWidget(header)

        # Stacked Widget for Page Views
        self.stack = QStackedWidget()

        # Build Subviews
        self.dashboard_view = self.create_dashboard_view()
        self.excluded_view = ExcludedView(self.db)
        self.prisoners_view = PrisonersView(self.db)
        self.add_case_view = ManageCaseTypesView(self.db)
        self.search_view = AdvancedSearchView(self.db)
        self.duplicates_view = DuplicateNamesView(self.db)

        # Connect signals for live synchronization
        self.excluded_view.data_changed_signal.connect(self.on_data_updated)
        self.prisoners_view.data_changed_signal.connect(self.on_data_updated)
        self.add_case_view.data_changed_signal.connect(self.on_data_updated)
        self.search_view.data_changed_signal.connect(self.on_data_updated)

        self.stack.addWidget(self.dashboard_view)    # Index 0
        self.stack.addWidget(self.excluded_view)     # Index 1
        self.stack.addWidget(self.prisoners_view)    # Index 2
        self.stack.addWidget(self.add_case_view)      # Index 3
        self.stack.addWidget(self.search_view)       # Index 4
        self.stack.addWidget(self.duplicates_view)   # Index 5

        content_layout.addWidget(self.stack, 1)
        s1_layout.addWidget(content_container, 1)

        # ========================================================
        # SYSTEM 2: School Security Management System Container
        # ========================================================
        self.system2_widget = SchoolSecurityMainView(self.school_security_db, parent=self)

        # Add both systems to Master Stack
        self.master_system_stack.addWidget(self.system1_widget)  # Index 0
        self.master_system_stack.addWidget(self.system2_widget)  # Index 1

        main_vbox.addWidget(self.master_system_stack, 1)

    def create_system_switcher_bar(self) -> QWidget:
        """Top-level selector bar allowing seamless switching between both independent systems."""
        bar = QFrame()
        bar.setObjectName("TopSystemSwitcherBar")
        bar.setFixedHeight(54)
        bar.setStyleSheet("""
            QFrame#TopSystemSwitcherBar {
                background-color: #0F172A;
                border-bottom: 2px solid #1E293B;
            }
            QPushButton.SystemTabBtn {
                font-family: 'Segoe UI', Tahoma, sans-serif;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 24px;
                border-radius: 8px 8px 0 0;
                border: none;
                margin-top: 6px;
                margin-right: 4px;
            }
            QPushButton.SystemTabBtn:checked {
                background-color: #1E40AF;
                color: #FFFFFF;
                border-bottom: 3px solid #F59E0B;
            }
            QPushButton.SystemTabBtn:!checked {
                background-color: transparent;
                color: #94A3B8;
            }
            QPushButton.SystemTabBtn:!checked:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #F1F5F9;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        # Directorate & Unified Portal Emblem Title
        left_h = QHBoxLayout()
        left_h.setSpacing(8)

        emblem_lbl = QLabel("🏛️  مديرية التربية والتعليم بالإسكندرية  |  المنظومة الرقمية الموحدة")
        emblem_lbl.setStyleSheet("color: #FCD34D; font-weight: 700; font-size: 12px;")
        left_h.addWidget(emblem_lbl)
        layout.addLayout(left_h)

        layout.addStretch()

        # System Selector Tabs
        tabs_h = QHBoxLayout()
        tabs_h.setSpacing(6)

        self.btn_sys1 = QPushButton("🏛️  بيانات المستبعدين والمسجونين")
        self.btn_sys1.setProperty("class", "SystemTabBtn")
        self.btn_sys1.setCheckable(True)
        self.btn_sys1.setChecked(True)
        self.btn_sys1.setCursor(Qt.PointingHandCursor)
        self.btn_sys1.clicked.connect(lambda: self.switch_system(0))
        tabs_h.addWidget(self.btn_sys1)

        self.btn_sys2 = QPushButton("🏫  منظومة تأمين المدارس وحراس الأمن")
        self.btn_sys2.setProperty("class", "SystemTabBtn")
        self.btn_sys2.setCheckable(True)
        self.btn_sys2.setChecked(False)
        self.btn_sys2.setCursor(Qt.PointingHandCursor)
        self.btn_sys2.clicked.connect(lambda: self.switch_system(1))
        tabs_h.addWidget(self.btn_sys2)

        layout.addLayout(tabs_h)

        return bar

    def switch_system(self, system_index: int):
        """Switch between System 1 (Exclusions/Prisoners) and System 2 (School Security)."""
        self.master_system_stack.setCurrentIndex(system_index)
        if system_index == 0:
            self.btn_sys1.setChecked(True)
            self.btn_sys2.setChecked(False)
            self.setWindowTitle(f"{APP_NAME} - {APP_SUBTITLE}")
        else:
            self.btn_sys1.setChecked(False)
            self.btn_sys2.setChecked(True)
            self.setWindowTitle("منظومة إدارة تأمين المدارس وحراس الأمن — مديرية التربية والتعليم بالإسكندرية")
            # Refresh System 2 dashboard
            if hasattr(self.system2_widget, "dashboard_view"):
                self.system2_widget.dashboard_view.load_data()

    def _make_nav_button(self, object_name: str, text: str) -> QPushButton:
        """Create a sidebar navigation button with proper objectName for QSS styling."""
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        btn.setCheckable(True)
        btn.setMinimumHeight(44)
        return btn

    def create_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(4)

        # Brand / Logo Frame
        logo_frame = QFrame()
        logo_frame.setObjectName("SidebarLogoFrame")
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(14, 16, 14, 14)
        logo_layout.setSpacing(6)
        logo_layout.setAlignment(Qt.AlignCenter)

        # Official Egyptian Government Directorate Emblem
        if LOGO_PATH.exists():
            emblem_lbl = QLabel()
            pix = QPixmap(str(LOGO_PATH))
            pix = pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            emblem_lbl.setPixmap(pix)
            emblem_lbl.setAlignment(Qt.AlignCenter)
            emblem_lbl.setStyleSheet("border: none; background: transparent; padding-bottom: 2px;")
            logo_layout.addWidget(emblem_lbl)

        badge = QLabel("🏛️  جمهورية مصر العربية")
        badge.setStyleSheet("color: #FCD34D; font-size: 12px; font-weight: bold;")
        badge.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(badge)

        app_title = QLabel(APP_NAME)
        app_title.setObjectName("SidebarAppTitle")
        app_title.setAlignment(Qt.AlignCenter)
        app_title.setWordWrap(True)
        logo_layout.addWidget(app_title)

        app_sub = QLabel(APP_SUBTITLE)
        app_sub.setObjectName("SidebarAppSubtitle")
        app_sub.setAlignment(Qt.AlignCenter)
        app_sub.setWordWrap(True)
        logo_layout.addWidget(app_sub)

        layout.addWidget(logo_frame)
        layout.addSpacing(6)

        self.sidebar_menu_stack = QStackedWidget()
        main_menu_page = QWidget()
        main_menu_layout = QVBoxLayout(main_menu_page)
        main_menu_layout.setContentsMargins(0, 0, 0, 0)
        main_menu_layout.setSpacing(4)
        layout.addWidget(self.sidebar_menu_stack, 1)

        # Nav Buttons — use objectNames that match the QSS selectors
        self.nav_buttons = []

        self.btn_nav_dash = self._make_nav_button("NavBtn_dashboard", "📊  لوحة المؤشرات والتحكم")
        self.btn_nav_dash.setChecked(True)
        self.btn_nav_dash.clicked.connect(lambda: self.switch_page(0, self.btn_nav_dash))
        main_menu_layout.addWidget(self.btn_nav_dash)
        self.nav_buttons.append(self.btn_nav_dash)

        self.btn_nav_excluded = self._make_nav_button("NavBtn_excluded", "🚫  سجلات المستبعدين")
        self.btn_nav_excluded.clicked.connect(lambda: self.switch_page(1, self.btn_nav_excluded))
        main_menu_layout.addWidget(self.btn_nav_excluded)
        self.nav_buttons.append(self.btn_nav_excluded)

        self.btn_nav_prisoners = self._make_nav_button("NavBtn_prisoners", "⚖️  سجلات المسجونين والقضايا")
        self.btn_nav_prisoners.clicked.connect(lambda: self.switch_page(2, self.btn_nav_prisoners))
        main_menu_layout.addWidget(self.btn_nav_prisoners)
        self.nav_buttons.append(self.btn_nav_prisoners)

        self.btn_nav_add_case = self._make_nav_button("NavBtn_addcase", "📋  إدارة أنواع القضايا")
        self.btn_nav_add_case.clicked.connect(lambda: self.switch_page(3, self.btn_nav_add_case))
        main_menu_layout.addWidget(self.btn_nav_add_case)
        self.nav_buttons.append(self.btn_nav_add_case)

        self.btn_nav_search = self._make_nav_button("NavBtn_search", "🔍  البحث الشامل والمتقدم")
        self.btn_nav_search.clicked.connect(lambda: self.switch_page(4, self.btn_nav_search))
        main_menu_layout.addWidget(self.btn_nav_search)
        self.nav_buttons.append(self.btn_nav_search)

        self.btn_nav_duplicates = self._make_nav_button("NavBtn_duplicates", "⚠️  الأسماء المتكررة")
        self.btn_nav_duplicates.clicked.connect(lambda: self.switch_page(5, self.btn_nav_duplicates))
        main_menu_layout.addWidget(self.btn_nav_duplicates)
        self.nav_buttons.append(self.btn_nav_duplicates)

        # Import Excel Action Button (not checkable — it opens a dialog)
        btn_nav_import = QPushButton("📥  استيراد بيانات إكسيل")
        btn_nav_import.setObjectName("NavBtn_import")
        btn_nav_import.setMinimumHeight(44)
        btn_nav_import.clicked.connect(self.open_import_dialog)
        main_menu_layout.addWidget(btn_nav_import)

        btn_nav_scan = QPushButton("📷  مسح ضوئي ذكي لمستند")
        btn_nav_scan.setObjectName("NavBtn_scan")
        btn_nav_scan.setMinimumHeight(44)
        btn_nav_scan.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: #93C5FD;
                border: 1.5px solid #3B82F6;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                text-align: right;
                padding-right: 18px;
            }
            QPushButton:hover {
                background-color: #1E40AF;
                color: #FFFFFF;
                border-color: #60A5FA;
            }
        """)
        btn_nav_scan.clicked.connect(self.open_smart_scan_dialog)
        main_menu_layout.addWidget(btn_nav_scan)

        main_menu_layout.addStretch()
        self.sidebar_menu_stack.addWidget(main_menu_page)

        # Footer Version
        ver_lbl = QLabel(f"الإصدار {APP_VERSION}")
        ver_lbl.setStyleSheet("color: #64748B; font-size: 10px; padding: 0 14px;")
        ver_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver_lbl)

        return sidebar

    def create_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("HeaderBar")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        if LOGO_PATH.exists():
            header_emblem = QLabel()
            h_pix = QPixmap(str(LOGO_PATH)).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            header_emblem.setPixmap(h_pix)
            header_emblem.setStyleSheet("border: none; background: transparent;")
            layout.addWidget(header_emblem)

        left_v = QVBoxLayout()
        left_v.setAlignment(Qt.AlignVCenter)
        left_v.setSpacing(2)
        title = QLabel(f"{APP_NAME} — {APP_SUBTITLE}")
        title.setObjectName("HeaderTitle")
        title.setWordWrap(True)
        title.setMinimumWidth(200)
        title.setMaximumWidth(400)
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1E40AF;")
        title.setToolTip(title.text())
        left_v.addWidget(title)

        status_lbl = QLabel("نظام مركزي لإدارة ومتابعة السجلات الأمنية والقضائية للعاملين بقطاع التعليم")
        status_lbl.setObjectName("HeaderSubtitle")
        status_lbl.setWordWrap(True)
        status_lbl.setMinimumWidth(200)
        status_lbl.setMaximumWidth(400)
        status_lbl.setStyleSheet("font-size: 10px; font-weight: 500; color: #64748B;")
        left_v.addWidget(status_lbl)
        layout.addLayout(left_v, 1)

        # Date & System Status Widget
        right_h = QHBoxLayout()
        right_h.setSpacing(8)
        self.date_lbl = QLabel(self.get_arabic_date_formatted())
        self.date_lbl.setAlignment(Qt.AlignCenter)
        self.date_lbl.setMinimumWidth(210)
        self.date_lbl.setFixedHeight(50)
        self.date_lbl.setStyleSheet("color: #1E40AF; font-weight: bold; background: #EFF6FF; border: 1px solid #BFDBFE; padding: 7px 12px; border-radius: 6px; font-size: 13px;")
        right_h.addWidget(self.date_lbl)

        # Timer to keep system date live and up to the minute
        self.date_timer = QTimer(self)
        self.date_timer.setInterval(60000)
        self.date_timer.timeout.connect(self.update_header_date)
        self.date_timer.start()

        header_import_btn = QPushButton("📥 استيراد ملف إكسيل")
        self.header_import_btn = header_import_btn
        header_import_btn.setObjectName("PrimaryBtn")
        header_import_btn.setMinimumHeight(44)
        header_import_btn.setStyleSheet("QPushButton#PrimaryBtn { font-size: 13px; padding: 8px 13px; }")
        header_import_btn.clicked.connect(self.open_import_dialog)
        right_h.addWidget(header_import_btn)

        layout.addLayout(right_h)
        return header

    def get_arabic_date_formatted(self) -> str:
        """Returns today's date formatted nicely with Arabic day and month names."""
        days = {
            "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
            "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
        }
        months = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
            7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }
        now = datetime.now()
        day_str = days.get(now.strftime("%A"), "")
        month_str = months.get(now.month, "")
        return f"📅 اليوم: {day_str} {now.day} {month_str} {now.year}"

    def update_header_date(self):
        if hasattr(self, "date_lbl"):
            self.date_lbl.setText(self.get_arabic_date_formatted())

    def create_dashboard_view(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(18)

        # 1. Top KPI Summary Cards (4 Cards)
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)

        self.kpi_excluded = self._build_kpi_card(
            "🚫 إجمالي المستبعدين أمنياً وتأديبياً", "0",
            "قرار استبعاد مسجل بالمديرية", "#DC2626"
        )
        kpi_grid.addWidget(self.kpi_excluded, 0, 0)

        self.kpi_prisoners = self._build_kpi_card(
            "⚖️ إجمالي المسجونين والأحكام القضائية", "0",
            "سجل قضايا وحبس مسجل بالمديرية", "#B91C1C"
        )
        kpi_grid.addWidget(self.kpi_prisoners, 0, 1)

        self.kpi_records = self._build_kpi_card(
            "👥 إجمالي سجلات الكشوف المعتمدة", "0",
            "إجمالي السجلات المقيدة بالكشفين", "#2563EB"
        )
        kpi_grid.addWidget(self.kpi_records, 0, 2)

        self.kpi_released = self._build_kpi_card(
            "✅ مفرج عنهم وعائدون للعمل", "0",
            "حالات إخلاء سبيل أو عودة للعمل", "#16A34A"
        )
        kpi_grid.addWidget(self.kpi_released, 0, 3)

        layout.addLayout(kpi_grid)

        # 2. Section Header: Quick Action Buttons
        sec_title = QLabel("⚡ الإجراءات السريعة ولوحة التنقل الفوري")
        sec_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {PALETTE['primary_dark']};")
        layout.addWidget(sec_title)

        actions_grid = QGridLayout()
        actions_grid.setSpacing(14)

        btn1 = self._build_action_card(
            "📋 إدارة أنواع القضايا",
            "إضافة أو حذف أنواع القضايا والمخالفات في النظام",
            "#2563EB", lambda: self.switch_page(3, self.btn_nav_add_case)
        )
        actions_grid.addWidget(btn1, 0, 0)

        btn2 = self._build_action_card(
            "🚫 بيانات المستبعدين",
            "إدارة قرارات الاستبعاد الأمني والوظائف البديلة",
            "#DC2626", lambda: self.switch_page(1, self.btn_nav_excluded)
        )
        actions_grid.addWidget(btn2, 0, 1)

        btn3 = self._build_action_card(
            "⚖️ بيانات المسجونين",
            "متابعة قضايا الحبس والأحكام القضائية وتواريخ الإفراج",
            "#B91C1C", lambda: self.switch_page(2, self.btn_nav_prisoners)
        )
        actions_grid.addWidget(btn3, 0, 2)

        btn4 = self._build_action_card(
            "🔍 بحث بالإسم / الرقم القومي",
            "استعلام فوري بالرقم القومي أو الاسم في كل السجلات",
            "#0891B2", self.action_search_name_nid
        )
        actions_grid.addWidget(btn4, 1, 0)

        btn5 = self._build_action_card(
            "📂 بحث بنوع القضية",
            "تصفية حسب نوع القضايا والتصنيف الجنائي",
            "#7C3AED", self.action_search_case_type
        )
        actions_grid.addWidget(btn5, 1, 1)

        btn6 = self._build_action_card(
            "📥 استيراد بيانات إكسيل",
            "معالجة ملفات إكسيل متعددة الأوراق بدقة وسرعة فائقة",
            "#059669", self.open_import_dialog
        )
        actions_grid.addWidget(btn6, 1, 2)

        layout.addLayout(actions_grid)

        # 3. Statistical Distribution Cards
        sec_analytics = QLabel("📈 التحليلات والتوزيع الإحصائي على مستوى المحافظة")
        sec_analytics.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {PALETTE['primary_dark']}; margin-top: 8px;")
        layout.addWidget(sec_analytics)

        analytics_layout = QHBoxLayout()
        analytics_layout.setSpacing(14)

        # Top Administrations Table Card
        admin_card = QFrame()
        admin_card.setStyleSheet("""
            QFrame { background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 12px; }
        """)
        admin_v = QVBoxLayout(admin_card)

        admin_card_title = QLabel("🏢 توزيع الحالات حسب الإدارات التعليمية")
        admin_card_title.setStyleSheet("font-weight: bold; color: #1E3A8A; font-size: 13px; border: none; padding: 0;")
        admin_v.addWidget(admin_card_title)

        self.admin_table = QTableWidget()
        self.admin_table.setColumnCount(3)
        self.admin_table.setHorizontalHeaderLabels(["الإدارة التعليمية", "المستبعدين", "المسجونين"])
        self.admin_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.admin_table.verticalHeader().setVisible(False)
        self.admin_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.admin_table.setFixedHeight(220)
        admin_v.addWidget(self.admin_table)
        analytics_layout.addWidget(admin_card, 1)

        # Top Case Types Table Card
        case_card = QFrame()
        case_card.setStyleSheet("""
            QFrame { background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 12px; }
        """)
        case_v = QVBoxLayout(case_card)

        case_card_title = QLabel("⚖️ توزيع الحالات حسب نوع القضية / التهمة")
        case_card_title.setStyleSheet("font-weight: bold; color: #1E3A8A; font-size: 13px; border: none; padding: 0;")
        case_v.addWidget(case_card_title)

        self.case_table = QTableWidget()
        self.case_table.setColumnCount(2)
        self.case_table.setHorizontalHeaderLabels(["نوع القضية / المخالفة", "إجمالي السجلات"])
        self.case_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.case_table.verticalHeader().setVisible(False)
        self.case_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.case_table.setFixedHeight(220)
        case_v.addWidget(self.case_table)
        analytics_layout.addWidget(case_card, 1)

        layout.addLayout(analytics_layout)

        scroll.setWidget(container)
        return scroll

    def _build_kpi_card(self, title: str, val: str, subtext: str, accent_color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("KpiCard")
        card.setStyleSheet(f"""
            QFrame#KpiCard {{
                background-color: white;
                border: 1px solid #E2E8F0;
                border-top: 4px solid {accent_color};
                border-radius: 12px;
            }}
            QFrame#KpiCard:hover {{
                border-color: #3B82F6;
                border-top: 4px solid {accent_color};
            }}
        """)
        v_layout = QVBoxLayout(card)
        v_layout.setContentsMargins(14, 14, 14, 14)
        v_layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: #64748B; border: none;")
        v_layout.addWidget(t_lbl)

        v_lbl = QLabel(val)
        v_lbl.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {accent_color}; border: none;")
        v_layout.addWidget(v_lbl)

        s_lbl = QLabel(subtext)
        s_lbl.setStyleSheet("font-size: 11px; color: #94A3B8; border: none;")
        v_layout.addWidget(s_lbl)

        card.val_label = v_lbl  # Reference for updating
        return card

    def _build_action_card(self, title: str, subtitle: str, color: str, callback) -> QWidget:
        card = ClickableCard(callback)
        card.setObjectName("ActionCardBtn")
        card.setStyleSheet(f"""
            QFrame#ActionCardBtn {{
                background-color: white;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                border-right: 4px solid {color};
            }}
            QFrame#ActionCardBtn:hover {{
                border: 2px solid {color};
                border-right: 4px solid {color};
                background-color: #F8FAFC;
            }}
        """)
        card.setMinimumHeight(90)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        v_layout = QVBoxLayout(card)
        v_layout.setContentsMargins(14, 12, 14, 12)
        v_layout.setSpacing(6)

        t = QLabel(title)
        t.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color}; border: none;")
        t.setAlignment(Qt.AlignRight)
        t.setAttribute(Qt.WA_TransparentForMouseEvents)
        v_layout.addWidget(t)

        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 11px; color: #64748B; font-weight: normal; border: none;")
        sub.setAlignment(Qt.AlignRight)
        sub.setAttribute(Qt.WA_TransparentForMouseEvents)
        v_layout.addWidget(sub)

        return card

    def switch_page(self, page_index: int, nav_button: Optional[QPushButton] = None):
        self.stack.setCurrentIndex(page_index)
        for btn in self.nav_buttons:
            btn.setChecked(btn == nav_button)

    def action_search_name_nid(self):
        self.switch_page(4, self.btn_nav_search)
        self.search_view.set_focus_field("name_nid")

    def action_search_case_type(self):
        self.switch_page(4, self.btn_nav_search)
        self.search_view.set_focus_field("case_type")

    def open_import_dialog(self):
        dlg = ExcelImportDialog(self.db, self)
        dlg.data_imported_signal.connect(self.on_data_updated)
        dlg.exec()

    def open_smart_scan_dialog(self, default_type="excluded"):
        dlg = SmartScanDialog(self.db, default_record_type=default_type, parent=self)
        dlg.record_added_signal.connect(self.on_data_updated)
        dlg.exec()

    def on_data_updated(self):
        """Called whenever data is imported, added, or deleted."""
        self.refresh_dashboard_stats()
        if hasattr(self.excluded_view, "refresh_combos"):
            self.excluded_view.refresh_combos()
        if hasattr(self.prisoners_view, "refresh_combos"):
            self.prisoners_view.refresh_combos()
        if hasattr(self.search_view, "refresh_combos"):
            self.search_view.refresh_combos()
        if hasattr(self.add_case_view, "refresh_combos"):
            self.add_case_view.refresh_combos()
        self.excluded_view.load_data()
        self.prisoners_view.load_data()
        self.add_case_view.load_data()
        self.search_view.execute_search()
        self.duplicates_view.load_duplicates()

    def refresh_dashboard_stats(self):
        stats = self.db.get_dashboard_stats()

        # Update KPI Labels
        self.kpi_excluded.val_label.setText(f"{stats['total_excluded']:,}")
        self.kpi_prisoners.val_label.setText(f"{stats['total_prisoners']:,}")
        self.kpi_records.val_label.setText(f"{stats['total_records']:,}")
        self.kpi_released.val_label.setText(f"{stats['released']:,}")

        # Update Top Administrations
        admin_rows = stats["admin_breakdown"]
        self.admin_table.setRowCount(len(admin_rows))
        for r_idx, item in enumerate(admin_rows):
            name_item = QTableWidgetItem(str(item["admin_name"]))
            name_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.admin_table.setItem(r_idx, 0, name_item)

            ex_item = QTableWidgetItem(f"{item['excluded_cnt']:,}")
            ex_item.setTextAlignment(Qt.AlignCenter)
            self.admin_table.setItem(r_idx, 1, ex_item)

            pr_item = QTableWidgetItem(f"{item['prisoner_cnt']:,}")
            pr_item.setTextAlignment(Qt.AlignCenter)
            self.admin_table.setItem(r_idx, 2, pr_item)

        # Update Top Case Types
        case_rows = stats["case_breakdown"]
        self.case_table.setRowCount(len(case_rows))
        for r_idx, item in enumerate(case_rows):
            c_name = QTableWidgetItem(str(item["case_name"]))
            c_name.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.case_table.setItem(r_idx, 0, c_name)

            cnt_item = QTableWidgetItem(f"{item['total_cases']:,}")
            cnt_item.setTextAlignment(Qt.AlignCenter)
            self.case_table.setItem(r_idx, 1, cnt_item)
