# -*- coding: utf-8 -*-
"""
Executive Dashboard View for School Security Management System.
Displays real-time KPIs, administration distribution, safety gear status, and quick action cards.
"""
from typing import Callable, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPalette

from ..services.school_service import SchoolService


class ClickableCard(QFrame):
    """Clickable dashboard action card with hover effects."""
    def __init__(self, callback: Optional[Callable] = None, parent=None):
        super().__init__(parent)
        self._callback = callback
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._callback:
            self._callback()
        super().mousePressEvent(event)


class SchoolSecurityDashboardView(QWidget):
    navigate_to_page = Signal(int)

    def __init__(self, school_service: SchoolService, parent=None):
        super().__init__(parent)
        self.school_service = school_service
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #F1F5F9; border: none; }")

        container = QWidget()
        container.setObjectName("DashboardContainer")
        container.setStyleSheet("""
            #DashboardContainer {
                background-color: #F1F5F9;
            }
            #DashboardContainer QLabel {
                background: transparent;
                border: none;
            }
        """)
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(24, 20, 24, 24)
        self.main_layout.setSpacing(18)

        # 1. Header with Refresh Button
        header_h = QHBoxLayout()
        title_lbl = QLabel("📊 لوحة مؤشرات متابعة تأمين المدارس")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #1E3A8A;")
        header_h.addWidget(title_lbl)
        header_h.addStretch()

        self.btn_refresh = QPushButton("🔄 تحديث المؤشرات")
        self.btn_refresh.setObjectName("SecondaryBtn")
        self.btn_refresh.setMinimumHeight(36)
        self.btn_refresh.clicked.connect(self.load_data)
        header_h.addWidget(self.btn_refresh)
        self.main_layout.addLayout(header_h)

        # 2. Top KPI Cards Grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)

        self.kpi_schools = self._create_kpi_card("🏫 إجمالي المدارس", "0", "منشأة تعليمية مسجلة", "#2563EB")
        self.kpi_guards = self._create_kpi_card("🛡️ حراس الأمن", "0", "حارس مكلف بالمدارس", "#16A34A")
        self.kpi_admins = self._create_kpi_card("🏢 الإدارات التعليمية", "0", "إدارة بمحافظة الإسكندرية", "#0891B2")
        self.kpi_cameras = self._create_kpi_card("📹 كاميرات تعمل", "0", "منظومة مراقبة نشطة", "#7C3AED")
        self.kpi_broken_cameras = self._create_kpi_card("⚠️ كاميرات معطلة", "0", "تحتاج صيانة وإصلاح", "#DC2626")
        self.kpi_extinguishers = self._create_kpi_card("🧯 طفايات الحريق", "0", "طفاية موزعة بالمدارس", "#D97706")
        self.kpi_classrooms = self._create_kpi_card("🚪 إجمالي الفصول", "0", "فصل تعليمي بالمدارس", "#475569")
        self.kpi_incomplete = self._create_kpi_card("📋 مدارس ناقصة البيانات", "0", "تحتاج استكمال الأمان", "#B91C1C")

        kpi_grid.addWidget(self.kpi_schools, 0, 0)
        kpi_grid.addWidget(self.kpi_guards, 0, 1)
        kpi_grid.addWidget(self.kpi_admins, 0, 2)
        kpi_grid.addWidget(self.kpi_cameras, 0, 3)

        kpi_grid.addWidget(self.kpi_broken_cameras, 1, 0)
        kpi_grid.addWidget(self.kpi_extinguishers, 1, 1)
        kpi_grid.addWidget(self.kpi_classrooms, 1, 2)
        kpi_grid.addWidget(self.kpi_incomplete, 1, 3)

        self.main_layout.addLayout(kpi_grid)

        # 3. Quick Action Cards
        sec_actions = QLabel("⚡ الإجراءات السريعة والتنقل الفوري")
        sec_actions.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E3A8A; margin-top: 6px;")
        self.main_layout.addWidget(sec_actions)

        act_grid = QGridLayout()
        act_grid.setSpacing(12)

        c1 = self._create_action_card("🏫 سجلات تأمين المدارس", "إدارة وفحص تجهيزات وأمان المنشآت التعليمية", "#2563EB", lambda: self.navigate_to_page.emit(1))
        c2 = self._create_action_card("🛡️ كشوف حراس الأمن", "توزيع عمال الحراسة وربطهم بالمدارس", "#16A34A", lambda: self.navigate_to_page.emit(2))
        c3 = self._create_action_card("🔍 البحث المتقدم الشامل", "استعلام فوري عن مدرسة أو حارس أو هاتف", "#0891B2", lambda: self.navigate_to_page.emit(3))
        c4 = self._create_action_card("📑 التقارير الإحصائية", "تقارير النواقص والأعطال ومعدات الطوارئ", "#7C3AED", lambda: self.navigate_to_page.emit(4))
        c5 = self._create_action_card("📥 استيراد ملف الإكسيل", "معالجة كشوف تأمين المدارس وحراس الأمن آلياً", "#059669", lambda: self.navigate_to_page.emit(5))

        act_grid.addWidget(c1, 0, 0)
        act_grid.addWidget(c2, 0, 1)
        act_grid.addWidget(c3, 0, 2)
        act_grid.addWidget(c4, 1, 0)
        act_grid.addWidget(c5, 1, 1)

        self.main_layout.addLayout(act_grid)

        # 4. Distribution Breakdown Table
        sec_dist = QLabel("📈 التوزيع الإحصائي على الإدارات التعليمية")
        sec_dist.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E3A8A; margin-top: 8px;")
        self.main_layout.addWidget(sec_dist)

        dist_card = QFrame()
        dist_card.setObjectName("DistCard")
        dist_card.setStyleSheet("""
            #DistCard {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 14px;
            }
        """)
        d_lay = QVBoxLayout(dist_card)

        self.admin_table = QTableWidget(0, 4)
        self.admin_table.setHorizontalHeaderLabels(["م", "الإدارة التعليمية", "عدد المدارس المسجلة", "عدد الحراس المكلفين"])
        self.admin_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.admin_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.admin_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.admin_table.verticalHeader().setVisible(False)
        self.admin_table.setFixedHeight(220)
        self.admin_table.setStyleSheet("background: white; border: 1px solid #E2E8F0;")
        d_lay.addWidget(self.admin_table)

        self.main_layout.addWidget(dist_card)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _create_kpi_card(self, title: str, val: str, subtext: str, color: str) -> QFrame:
        card = QFrame()
        card.setMinimumHeight(100)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-top: 4px solid {color};
                border-radius: 12px;
                padding: 14px;
            }}
            QFrame:hover {{
                border-color: #93C5FD;
                border-top: 4px solid {color};
            }}
            QLabel {{
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet(f"font-size: 12px; font-weight: 600; color: #64748B;")
        t.setAlignment(Qt.AlignRight)
        v.addWidget(t)

        lbl_val = QLabel(val)
        lbl_val.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {color};")
        lbl_val.setAlignment(Qt.AlignRight)
        v.addWidget(lbl_val)

        s = QLabel(subtext)
        s.setStyleSheet("font-size: 11px; color: #94A3B8;")
        s.setAlignment(Qt.AlignRight)
        v.addWidget(s)

        card.val_label = lbl_val
        return card

    def _create_action_card(self, title: str, subtitle: str, color: str, callback: Callable) -> QWidget:
        card = ClickableCard(callback)
        card.setMinimumHeight(85)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                border-right: 5px solid {color};
                padding: 12px;
            }}
            QFrame:hover {{
                background-color: #F8FAFC;
                border: 1.5px solid {color};
                border-right: 5px solid {color};
            }}
            QLabel {{
                background: transparent;
                border: none;
                padding: 0px;
            }}
        """)
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
        t.setAlignment(Qt.AlignRight)
        t.setAttribute(Qt.WA_TransparentForMouseEvents)
        v.addWidget(t)

        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 11px; color: #475569;")
        sub.setAlignment(Qt.AlignRight)
        sub.setAttribute(Qt.WA_TransparentForMouseEvents)
        v.addWidget(sub)

        return card

    def load_data(self):
        try:
            metrics = self.school_service.get_dashboard_metrics()
        except Exception:
            return

        self.kpi_schools.val_label.setText(f"{metrics['total_schools']:,}")
        self.kpi_guards.val_label.setText(f"{metrics['total_guards']:,}")
        self.kpi_admins.val_label.setText(f"{metrics['total_administrations']:,}")
        self.kpi_cameras.val_label.setText(f"{metrics['total_working_cameras']:,}")
        self.kpi_broken_cameras.val_label.setText(f"{metrics['total_broken_cameras']:,}")
        self.kpi_extinguishers.val_label.setText(f"{metrics['total_extinguishers']:,}")
        self.kpi_classrooms.val_label.setText(f"{metrics['total_classrooms']:,}")
        self.kpi_incomplete.val_label.setText(f"{metrics['incomplete_schools_count']:,}")

        # Update distribution table
        breakdown = metrics.get("admin_breakdown", [])
        self.admin_table.setRowCount(len(breakdown))
        for r_idx, b in enumerate(breakdown):
            idx_item = QTableWidgetItem(str(r_idx + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            self.admin_table.setItem(r_idx, 0, idx_item)

            adm_item = QTableWidgetItem(str(b.get("administration", "")))
            adm_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.admin_table.setItem(r_idx, 1, adm_item)

            sch_item = QTableWidgetItem(f"{b.get('schools_cnt', 0):,}")
            sch_item.setTextAlignment(Qt.AlignCenter)
            self.admin_table.setItem(r_idx, 2, sch_item)

            grd_item = QTableWidgetItem(f"{b.get('guards_cnt', 0):,}")
            grd_item.setTextAlignment(Qt.AlignCenter)
            self.admin_table.setItem(r_idx, 3, grd_item)
