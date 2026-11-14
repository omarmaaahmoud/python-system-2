import re
from typing import Dict, List, Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from config import PALETTE
from database import normalize_arabic


def find_smart_admin_match(raw_name: str, existing_names: List[str]) -> Optional[str]:
    """Smart fuzzy/normalized matching for Arabic administration names."""
    if not raw_name:
        return None
    norm_raw = normalize_arabic(raw_name)
    norm_raw_clean = re.sub(r"^(اداره|ادارة|مديريه|مديرية)\s+", "", norm_raw).strip()
    norm_raw_clean = re.sub(r"\s+(التعليميه|التعليمية)$", "", norm_raw_clean).strip()

    # Priority 1: Well-known directorate patterns
    if "منتزه" in norm_raw_clean:
        if "اول" in norm_raw_clean or "1" in norm_raw_clean:
            for ext in existing_names:
                if "اول" in normalize_arabic(ext):
                    return ext
            return "المنتزه أول"
        elif "ثان" in norm_raw_clean or "تان" in norm_raw_clean or "2" in norm_raw_clean:
            for ext in existing_names:
                if "ثان" in normalize_arabic(ext):
                    return ext
            return "المنتزه ثان"
        elif norm_raw_clean in ["منتزه", "المنتزه"]:
            for ext in existing_names:
                if normalize_arabic(ext) in ["منتزه", "المنتزه"]:
                    return ext

    if norm_raw_clean in ["مديريه", "المديريه", "ديوان المديريه", "ديوان عام المديريه"]:
        for ext in existing_names:
            if "مديريه" in normalize_arabic(ext) or "مديرية" in ext:
                return ext

    # Priority 2: Exact normalized match
    for ext in existing_names:
        norm_ext = normalize_arabic(ext)
        if norm_raw == norm_ext or norm_raw_clean == norm_ext:
            return ext

    # Priority 3: Substring / token matching
    for ext in existing_names:
        norm_ext = normalize_arabic(ext)
        norm_ext_clean = re.sub(r"^(اداره|ادارة|مديريه|مديرية)\s+", "", norm_ext).strip()
        norm_ext_clean = re.sub(r"\s+(التعليميه|التعليمية)$", "", norm_ext_clean).strip()
        if norm_raw_clean == norm_ext_clean:
            return ext
        if len(norm_raw_clean) >= 3 and (norm_raw_clean in norm_ext_clean or norm_ext_clean in norm_raw_clean):
            if "اول" in norm_raw_clean and "اول" not in norm_ext_clean:
                continue
            if "ثان" in norm_raw_clean and "ثان" not in norm_ext_clean:
                continue
            return ext

    return None


class SmartAdminMappingDialog(QDialog):
    """Smart Modal Dialog that detects administration variations in imported Excel sheets
    and lets the user choose to merge them into standard administrations or keep as new.
    """
    def __init__(self, detected_admins: Dict[str, int], existing_admins: List[str], parent=None):
        super().__init__(parent)
        self.detected_admins = detected_admins  # {raw_name: row_count}
        self.existing_admins = existing_admins
        self.combos: Dict[str, QComboBox] = {}
        self.mapping_result: Dict[str, str] = {}

        self.setWindowTitle("نظام الدمج والمطابقة الذكي للإدارات (Smart Admin Mapping)")
        self.resize(720, 520)
        self.setLayoutDirection(Qt.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Title
        title_label = QLabel("فحص الإدارات والمطابقة الذكية قبل الاستيراد")
        title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {PALETTE['primary']};")
        layout.addWidget(title_label)

        # Info Box
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_text = QLabel(
            "💡 قام النظام بفحص ملف الإكسيل وتحديد الإدارات الواردة فيه واقتراح دمج المتشابهات تلقائياً.\n"
            "يمكنك مراجعة كل إدارة وتحديد هل تريد دمجها مع إدارة معتمدة أم إضافتها كإدارة جديدة مستقلة:"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #1E3A8A; font-size: 12px; font-weight: 500; line-height: 1.5;")
        info_layout.addWidget(info_text)
        layout.addWidget(info_frame)

        # Table for Mappings
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "الإدارة الواردة بالشيت",
            "عدد السجلات",
            "الإجراء المقترح (الدمج في النظام)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
                gridline-color: #F1F5F9;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                font-weight: bold;
                color: #334155;
                padding: 8px;
                border: 1px solid #E2E8F0;
            }
        """)

        sorted_admins = sorted(self.detected_admins.items(), key=lambda x: x[1], reverse=True)
        self.table.setRowCount(len(sorted_admins))

        for row_idx, (raw_name, count) in enumerate(sorted_admins):
            # 1. Raw Name Item
            name_item = QTableWidgetItem(raw_name)
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            name_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row_idx, 0, name_item)

            # 2. Count Item
            count_item = QTableWidgetItem(f"{count} سجل")
            count_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            count_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 1, count_item)

            # 3. Smart Action Combobox
            combo = QComboBox()
            combo.setStyleSheet("""
                QComboBox {
                    padding: 5px 10px;
                    border: 1px solid #94A3B8;
                    border-radius: 6px;
                    font-weight: 600;
                    background: #FFFFFF;
                }
                QComboBox:focus {
                    border: 2px solid #2563EB;
                }
            """)

            # Find smart match
            best_match = find_smart_admin_match(raw_name, self.existing_admins)

            # Populate combo
            # Option A: Merged match
            if best_match:
                combo.addItem(f"⭐ دمج مع: {best_match}", best_match)

            # Option B: All other existing admins
            for ext in self.existing_admins:
                if ext != best_match:
                    combo.addItem(f"دمج مع: {ext}", ext)

            # Option C: Add as new administration
            combo.addItem(f"➕ إضافة كإدارة جديدة باسم ('{raw_name}')", "__NEW__")

            # Option D: Leave empty / Ignore
            combo.addItem("🚫 ترك الإدارة فارغة في هذا السجل", "__NONE__")

            # Default selection
            if best_match:
                combo.setCurrentIndex(0)
            else:
                # Default to new or first
                combo.setCurrentIndex(combo.count() - 2)

            self.combos[raw_name] = combo
            self.table.setCellWidget(row_idx, 2, combo)
            self.table.setRowHeight(row_idx, 44)

        layout.addWidget(self.table)

        # Action Buttons
        btn_layout = QHBoxLayout()

        select_all_merged_btn = QPushButton("✨ دمج كل المقترحات الذكية")
        select_all_merged_btn.setObjectName("SecondaryBtn")
        select_all_merged_btn.clicked.connect(self.apply_all_smart)
        btn_layout.addWidget(select_all_merged_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("إلغاء الاستيراد")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.confirm_btn = QPushButton("✅ اعتماد ومتابعة الاستيراد")
        self.confirm_btn.setObjectName("PrimaryBtn")
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #15803D;
            }
        """)
        self.confirm_btn.clicked.connect(self.confirm_mappings)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

    def apply_all_smart(self):
        """Resets all combos to their top smart recommendation."""
        for combo in self.combos.values():
            if combo.count() > 0:
                combo.setCurrentIndex(0)

    def confirm_mappings(self):
        """Gathers chosen mappings and closes with Accepted status."""
        for raw_name, combo in self.combos.items():
            chosen = combo.currentData()
            self.mapping_result[raw_name] = chosen
        self.accept()

    def get_mappings(self) -> Dict[str, str]:
        """Returns {raw_excel_admin_name: target_admin_name_or_special_flag}."""
        return self.mapping_result
