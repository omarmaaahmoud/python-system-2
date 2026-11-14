# -*- coding: utf-8 -*-
"""
High-Performance Virtualized Qt Table Models for School Security Management System.
Features:
- Sub-millisecond scrolling on large datasets
- Centered numeric and status cells
- Conditional warning colors for broken cameras or invalid hoses
- Custom tooltips
"""
from typing import List, Dict, Any, Optional
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush


class SchoolTableModel(QAbstractTableModel):
    """Virtualized Model for Schools Data."""

    HEADERS = [
        "م",
        "الإدارة التعليمية",
        "اسم المدرسة",
        "التبعية",
        "مدير المدرسة",
        "تليفون المدير",
        "مسؤول الأمن",
        "تليفون مسؤول الأمن",
        "الفصول",
        "البوابات",
        "الطفايات",
        "نوع الطفاية",
        "الوزن",
        "خطوط مفعلة",
        "خطوط غير مفعلة",
        "كاميرات تعمل",
        "كاميرات معطلة",
        "شركة الصيانة",
        "الجرادل",
        "خراطيم صالحة",
        "خراطيم غير صالحة",
        "الحراس المكلفين"
    ]

    FIELD_KEYS = [
        "school_id",
        "administration",
        "school_name",
        "affiliation",
        "manager_name",
        "manager_phone",
        "security_officer_name",
        "security_officer_phone",
        "classrooms_count",
        "gates_count",
        "fire_extinguishers_count",
        "fire_extinguisher_type",
        "fire_extinguisher_weight",
        "activated_fire_lines",
        "inactive_fire_lines",
        "working_cameras",
        "non_working_cameras",
        "camera_maintenance_company",
        "buckets_count",
        "valid_fire_hoses",
        "invalid_fire_hoses",
        "assigned_guards_count"
    ]

    CENTER_COLS = {0, 3, 5, 7, 8, 9, 10, 12, 13, 14, 15, 16, 18, 19, 20, 21}

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None):
        super().__init__()
        self._data = data or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row_item = self._data[index.row()]
        col = index.column()
        key = self.FIELD_KEYS[col]
        val = row_item.get(key)
        val_str = str(val).strip() if val is not None else ""

        if role == Qt.DisplayRole:
            if col == 0:
                return str(index.row() + 1)
            if col == 21:
                cnt = row_item.get("assigned_guards_count", 0)
                names = str(row_item.get("guard_names_preview") or "").strip()
                if names:
                    return f"{names} ({cnt})" if cnt > 1 else names
                return "لا يوجد"
            if not val_str or val_str in ("None", "nan", "NaN", "null"):
                return "—"
            return val_str

        elif role == Qt.ToolTipRole:
            if col == 2 and not val_str:
                return "ملاحظة: السجل ناقص بدون اسم مدرسة"
            if key in ("non_working_cameras", "inactive_fire_lines", "invalid_fire_hoses"):
                clean = val_str.replace("—", "").strip()
                if clean and clean not in ("0", "٠"):
                    return f"تنبيه عطل/نقص: {self.HEADERS[col]} ({val_str})"
            if col == 21 and row_item.get("guard_names_preview"):
                return f"الحراس المكلفون:\n{row_item.get('guard_names_preview')}"

        elif role == Qt.ForegroundRole:
            if col == 2 and not val_str:
                return QBrush(QColor("#D97706"))
            if key in ("non_working_cameras", "inactive_fire_lines", "invalid_fire_hoses"):
                clean = val_str.replace("—", "").strip()
                if clean and clean not in ("0", "٠"):
                    return QBrush(QColor("#DC2626"))
            if col == 21:
                cnt = row_item.get("assigned_guards_count", 0)
                if not cnt:
                    return QBrush(QColor("#94A3B8"))
                return QBrush(QColor("#16A34A"))

        elif role == Qt.TextAlignmentRole:
            if col in self.CENTER_COLS:
                return Qt.AlignCenter
            return Qt.AlignRight | Qt.AlignVCenter

        elif role == Qt.BackgroundRole:
            if not str(row_item.get("school_name") or "").strip():
                return QBrush(QColor("#FFFBEB"))
            if index.row() % 2 == 1:
                return QBrush(QColor("#F8FAFC"))

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.HEADERS):
                return self.HEADERS[section]
        return None

    def update_data(self, new_data: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_row(self, row_idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]
        return None


class GuardTableModel(QAbstractTableModel):
    """Virtualized Model for Security Guards Data."""

    HEADERS = [
        "م",
        "اسم الحارس",
        "الرقم القومي",
        "رقم الهاتف",
        "المدرسة المكلف بها",
        "الإدارة التعليمية",
        "عنوان المدرسة",
        "ملاحظات"
    ]

    FIELD_KEYS = [
        "guard_id",
        "guard_name",
        "national_id",
        "phone",
        "school_name",
        "administration",
        "address",
        "notes"
    ]

    CENTER_COLS = {0, 2, 3}

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None):
        super().__init__()
        self._data = data or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row_item = self._data[index.row()]
        col = index.column()
        key = self.FIELD_KEYS[col]
        val = row_item.get(key)
        val_str = str(val).strip() if val is not None else ""

        if role == Qt.DisplayRole:
            if col == 0:
                return str(index.row() + 1)
            if key == "national_id":
                if not val_str or val_str in ("0", "None", "nan", "null"):
                    return "—"
                if len(val_str) < 14:
                    return f"⚠️ {val_str}"
                return val_str
            if not val_str or val_str in ("None", "nan", "NaN", "null"):
                return "—"
            return val_str

        elif role == Qt.ToolTipRole:
            if key == "national_id" and val_str and val_str != "0" and len(val_str) < 14:
                return f"تنبيه: الرقم القومي غير مكتمل ({len(val_str)} رقماً من 14)"
            if not row_item.get("school_name"):
                return "حارس غير مرتبط بمدرسة حالياً"

        elif role == Qt.ForegroundRole:
            if key == "national_id" and val_str and val_str != "0" and len(val_str) < 14:
                return QBrush(QColor("#D97706"))
            if col == 4 and not str(row_item.get("school_name") or "").strip():
                return QBrush(QColor("#94A3B8"))

        elif role == Qt.TextAlignmentRole:
            if col in self.CENTER_COLS:
                return Qt.AlignCenter
            return Qt.AlignRight | Qt.AlignVCenter

        elif role == Qt.BackgroundRole:
            if index.row() % 2 == 1:
                return QBrush(QColor("#F8FAFC"))

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.HEADERS):
                return self.HEADERS[section]
        return None

    def update_data(self, new_data: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_row(self, row_idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]
        return None

