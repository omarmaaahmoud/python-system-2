# -*- coding: utf-8 -*-
"""
Main View Container for School Security Management System (System 2).
Provides dedicated sidebar navigation, executive header, and stacked subviews.
"""
from datetime import datetime
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap

from ..database import SchoolSecurityDatabaseManager
from ..services.school_service import SchoolService
from ..services.guard_service import GuardService
from .dashboard_view import SchoolSecurityDashboardView
from .schools_view import SchoolsView
from .guards_view import GuardsView
from .advanced_search_view import AdvancedSearchView
from .reports_view import ReportsView
from .import_dialog import SchoolSecurityImportDialog
from .school_dialog import SchoolDialog


class SchoolSecurityMainView(QWidget):
    """Integrated System 2 container."""

    def __init__(self, db_manager: SchoolSecurityDatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.school_service = SchoolService(self.db)
        self.guard_service = GuardService(self.db)

        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Dedicated System 2 Sidebar
        self.sidebar = self.create_sidebar()
        root_layout.addWidget(self.sidebar)

        # 2. Main Content Container (Header + Stack)
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header Bar
        header = self.create_header()
        content_layout.addWidget(header)

        # Stacked Subviews
        self.stack = QStackedWidget()

        self.dashboard_view = SchoolSecurityDashboardView(self.school_service, parent=self)
        self.schools_view = SchoolsView(self.school_service, self.guard_service, parent=self)
        self.guards_view = GuardsView(self.guard_service, self.school_service, parent=self)
        self.search_view = AdvancedSearchView(self.db, self.school_service, parent=self)
        self.reports_view = ReportsView(self.db, self.school_service, parent=self)

        # Connect inter-view signals
        self.dashboard_view.navigate_to_page.connect(self.switch_page_by_index)
        self.schools_view.data_changed.connect(self.on_data_updated)
        self.guards_view.data_changed.connect(self.on_data_updated)
        self.search_view.open_school_requested.connect(self.open_school_by_id)

        self.stack.addWidget(self.dashboard_view)  # 0
        self.stack.addWidget(self.schools_view)    # 1
        self.stack.addWidget(self.guards_view)     # 2
        self.stack.addWidget(self.search_view)     # 3
        self.stack.addWidget(self.reports_view)    # 4

        content_layout.addWidget(self.stack, 1)
        root_layout.addWidget(content_container, 1)

    def _make_nav_button(self, object_name: str, text: str) -> QPushButton:
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

        # Header Badge
        brand_frame = QFrame()
        b_lay = QVBoxLayout(brand_frame)
        b_lay.setContentsMargins(14, 16, 14, 14)
        b_lay.setSpacing(6)
        b_lay.setAlignment(Qt.AlignCenter)

        badge = QLabel("🏛️ مديرية التربية والتعليم بالإسكندرية")
        badge.setStyleSheet("color: #FCD34D; font-size: 11px; font-weight: bold;")
        badge.setAlignment(Qt.AlignCenter)
        b_lay.addWidget(badge)

        sys_title = QLabel("منظومة تأمين المدارس")
        sys_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFFFFF;")
        sys_title.setAlignment(Qt.AlignCenter)
        b_lay.addWidget(sys_title)

        sys_sub = QLabel("إدارة وتجهيزات الأمان وعمال الحراسة")
        sys_sub.setStyleSheet("font-size: 11px; color: #93C5FD;")
        sys_sub.setAlignment(Qt.AlignCenter)
        b_lay.addWidget(sys_sub)

        layout.addWidget(brand_frame)
        layout.addSpacing(8)

        # Nav Buttons
        self.nav_buttons = []

        self.btn_nav_dash = self._make_nav_button("NavBtn_dashboard", "📊  لوحة المؤشرات والتحكم")
        self.btn_nav_dash.setChecked(True)
        self.btn_nav_dash.clicked.connect(lambda: self.switch_page(0, self.btn_nav_dash))
        layout.addWidget(self.btn_nav_dash)
        self.nav_buttons.append(self.btn_nav_dash)

        self.btn_nav_schools = self._make_nav_button("NavBtn_schools", "🏫  سجلات تأمين المدارس")
        self.btn_nav_schools.clicked.connect(lambda: self.switch_page(1, self.btn_nav_schools))
        layout.addWidget(self.btn_nav_schools)
        self.nav_buttons.append(self.btn_nav_schools)

        self.btn_nav_guards = self._make_nav_button("NavBtn_guards", "🛡️  كشوف حراس أمن المدارس")
        self.btn_nav_guards.clicked.connect(lambda: self.switch_page(2, self.btn_nav_guards))
        layout.addWidget(self.btn_nav_guards)
        self.nav_buttons.append(self.btn_nav_guards)

        self.btn_nav_search = self._make_nav_button("NavBtn_search", "🔍  البحث الشامل والمتقدم")
        self.btn_nav_search.clicked.connect(lambda: self.switch_page(3, self.btn_nav_search))
        layout.addWidget(self.btn_nav_search)
        self.nav_buttons.append(self.btn_nav_search)

        self.btn_nav_reports = self._make_nav_button("NavBtn_reports", "📑  التقارير والإحصائيات")
        self.btn_nav_reports.clicked.connect(lambda: self.switch_page(4, self.btn_nav_reports))
        layout.addWidget(self.btn_nav_reports)
        self.nav_buttons.append(self.btn_nav_reports)

        layout.addSpacing(6)

        # Direct Excel Import Button
        btn_import = QPushButton("📥  استيراد كشوف الإكسيل")
        btn_import.setObjectName("NavBtn_import")
        btn_import.setMinimumHeight(44)
        btn_import.clicked.connect(self.open_import_dialog)
        layout.addWidget(btn_import)

        layout.addStretch()

        ver_lbl = QLabel("إصدار المنظومة 1.0 (تأمين المدارس)")
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

        left_v = QVBoxLayout()
        left_v.setAlignment(Qt.AlignVCenter)
        left_v.setSpacing(2)

        t_lbl = QLabel("منظومة إدارة تأمين المدارس وحراس الأمن — مديرية التربية والتعليم بالإسكندرية")
        t_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #1E40AF;")
        left_v.addWidget(t_lbl)

        sub_lbl = QLabel("متابعة خطوط الحريق، الكاميرات، طفايات الحريق، وتوزيع أفراد الأمن المدرسي")
        sub_lbl.setStyleSheet("font-size: 10px; color: #64748B;")
        left_v.addWidget(sub_lbl)
        layout.addLayout(left_v, 1)

        # Date Label
        right_h = QHBoxLayout()
        right_h.setSpacing(8)

        self.date_lbl = QLabel(self.get_arabic_date_formatted())
        self.date_lbl.setAlignment(Qt.AlignCenter)
        self.date_lbl.setFixedHeight(44)
        self.date_lbl.setStyleSheet("color: #1E40AF; font-weight: bold; background: #EFF6FF; border: 1px solid #BFDBFE; padding: 6px 12px; border-radius: 6px; font-size: 12px;")
        right_h.addWidget(self.date_lbl)

        btn_header_import = QPushButton("📥 استيراد كشوف تأمين المدارس")
        btn_header_import.setObjectName("PrimaryBtn")
        btn_header_import.setMinimumHeight(44)
        btn_header_import.clicked.connect(self.open_import_dialog)
        right_h.addWidget(btn_header_import)

        layout.addLayout(right_h)
        return header

    def get_arabic_date_formatted(self) -> str:
        days = {
            "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
            "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
        }
        months = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
            7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }
        now = datetime.now()
        return f"📅 {days.get(now.strftime('%A'), '')} {now.day} {months.get(now.month, '')} {now.year}"

    def switch_page(self, index: int, nav_btn: Optional[QPushButton] = None):
        self.stack.setCurrentIndex(index)
        for b in self.nav_buttons:
            b.setChecked(b == nav_btn)

    def switch_page_by_index(self, index: int):
        if index == 5:
            self.open_import_dialog()
            return
        if 0 <= index < len(self.nav_buttons):
            self.switch_page(index, self.nav_buttons[index])

    def open_school_by_id(self, school_id: int):
        dlg = SchoolDialog(self.school_service, self.guard_service, school_id=school_id, read_only=True, parent=self)
        dlg.exec()

    def open_import_dialog(self, initial_file: Optional[str] = None):
        dlg = SchoolSecurityImportDialog(self.db, parent=self)
        dlg.import_completed.connect(self.on_data_updated)
        if initial_file:
            dlg.set_file_path(initial_file)
        dlg.exec()

    def on_data_updated(self):
        self.dashboard_view.load_data()
        self.schools_view.on_data_updated()
        self.guards_view.on_data_updated()
        self.reports_view.generate_selected_report()
