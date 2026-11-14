from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from config import PALETTE
from database import DatabaseManager


class DuplicateNamesView(QWidget):
    """View for detecting and displaying duplicate employee names across records."""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()
        self.load_duplicates()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # Title Card
        title_card = QFrame()
        title_card.setStyleSheet(f"""
            QFrame {{ background-color: {PALETTE['surface']}; border: 1px solid {PALETTE['border_light']}; 
                     border-radius: 10px; padding: 14px; border-right: 4px solid #D97706; }}
            QLabel {{ border: none; }}
        """)
        title_layout = QVBoxLayout(title_card)
        
        title_lbl = QLabel("⚠️ كشف الأسماء المتكررة في قاعدة البيانات")
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {PALETTE['warning']}; border: none;")
        title_layout.addWidget(title_lbl)
        
        desc_lbl = QLabel("يعرض هذا القسم جميع الأسماء المتكررة في سجلات الموظفين "
                          "ويساعد في اكتشاف البيانات المكررة لتنقية قاعدة البيانات.")
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 12px; border: none;")
        title_layout.addWidget(desc_lbl)
        
        main_layout.addWidget(title_card)

        # Toolbar
        toolbar = QHBoxLayout()
        
        self.count_badge = QLabel("الأسماء المتكررة: 0")
        self.count_badge.setStyleSheet(f"font-weight: bold; color: {PALETTE['warning']}; "
                                       f"background: {PALETTE['warning_bg']}; border: 1px solid #FDE68A; "
                                       f"border-radius: 6px; padding: 6px 12px;")
        toolbar.addWidget(self.count_badge)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("🔄 إعادة الفحص")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self.load_duplicates)
        toolbar.addWidget(refresh_btn)
        
        main_layout.addLayout(toolbar)

        # Duplicates Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "الاسم المتكرر",
            "عدد التكرار",
            "الأرقام القومية",
            "الإدارات التعليمية",
            "المدارس / جهات العمل"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 80)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                gridline-color: #F1F5F9;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px 8px;
            }
            QTableWidget::item:selected {
                background-color: #EFF6FF;
                color: #1E3A8A;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                color: #1E3A8A;
                font-weight: bold;
                border: 1px solid #E2E8F0;
                padding: 8px;
            }
        """)
        main_layout.addWidget(self.table)

    def load_duplicates(self):
        """Load and display duplicate names from the database."""
        duplicates = self.db.find_duplicate_names()
        self.table.setRowCount(len(duplicates))
        self.count_badge.setText(f"الأسماء المتكررة: {len(duplicates)}")

        for row_idx, dup in enumerate(duplicates):
            # Name
            name_item = QTableWidgetItem(str(dup.get("full_name", "")))
            name_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            name_item.setForeground(QBrush(QColor("#B91C1C")))
            self.table.setItem(row_idx, 0, name_item)

            # Count
            count_item = QTableWidgetItem(str(dup.get("name_count", 0)))
            count_item.setTextAlignment(Qt.AlignCenter)
            count_item.setBackground(QBrush(QColor("#FEF3C7")))
            count_item.setForeground(QBrush(QColor("#92400E")))
            self.table.setItem(row_idx, 1, count_item)

            # National IDs
            nids = str(dup.get("national_ids", ""))
            clean_nids_list = [
                "⚠️ 0" if ("مؤقت" in part or not part.strip() or part.strip() in ["0", "None"])
                else (f"⚠️ {part.strip()}" if len(part.strip()) < 14 else part.strip())
                for part in nids.split(" | ")
            ]
            nid_item = QTableWidgetItem(" | ".join(clean_nids_list))
            nid_item.setTextAlignment(Qt.AlignCenter)
            if any(p.startswith("⚠️") for p in clean_nids_list):
                nid_item.setForeground(QBrush(QColor("#D97706")))
            self.table.setItem(row_idx, 2, nid_item)

            # Administrations
            admins = str(dup.get("administrations", ""))
            admin_item = QTableWidgetItem(admins)
            admin_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row_idx, 3, admin_item)

            # Schools
            schools = str(dup.get("schools", ""))
            school_item = QTableWidgetItem(schools)
            school_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row_idx, 4, school_item)
