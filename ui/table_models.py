from typing import List, Dict, Any, Optional
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QColor, QBrush

class ExcludedTableModel(QAbstractTableModel):
    """High-Performance Virtualized Table Model for Excluded Personnel."""
    HEADERS = [
        "م",
        "الاسم رباعي",
        "الرقم القومي",
        "الإدارة التعليمية",
        "جهة العمل / المدرسة",
        "الهاتف",
        "الوظيفة الحالية",
        "الوظيفة المرشح لها",
        "جهة الاستبعاد",
        "تاريخ الاستبعاد",
        "نوع القضية",
        "سبب الاستبعاد"
    ]

    FIELD_KEYS = [
        "index",
        "full_name",
        "national_id",
        "administration_name",
        "school",
        "phone",
        "current_job",
        "nominee_job",
        "exclusion_entity",
        "exclusion_date",
        "case_type_name",
        "exclusion_reason"
    ]

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

        if role == Qt.DisplayRole:
            if col == 0:
                rec_num = row_item.get("record_number")
                return str(rec_num) if rec_num is not None else str(index.row() + 1)
            key = self.FIELD_KEYS[col]
            val = row_item.get(key, "")
            if key == "national_id":
                clean_nid = str(val).strip() if val is not None else ""
                if not clean_nid or "مؤقت" in clean_nid or clean_nid in ["0", "None", "nan"]:
                    return "⚠️ 0"
                elif len(clean_nid) < 14:
                    return f"⚠️ {clean_nid}"
                return clean_nid
            return str(val) if val is not None else ""

        elif role == Qt.ToolTipRole:
            if col < len(self.FIELD_KEYS) and self.FIELD_KEYS[col] == "national_id":
                val = row_item.get("national_id", "")
                clean_nid = str(val).strip() if val is not None else ""
                if not clean_nid or "مؤقت" in clean_nid or clean_nid in ["0", "None", "nan"]:
                    return "⚠️ الرقم القومي غير مسجل (0)"
                elif len(clean_nid) < 14:
                    return f"⚠️ تنبيه: الرقم القومي غير مكتمل ({len(clean_nid)} رقماً من أصل 14)"

        elif role == Qt.ForegroundRole:
            if col < len(self.FIELD_KEYS) and self.FIELD_KEYS[col] == "national_id":
                val = row_item.get("national_id", "")
                clean_nid = str(val).strip() if val is not None else ""
                if not clean_nid or "مؤقت" in clean_nid or clean_nid in ["0", "None", "nan"] or len(clean_nid) < 14:
                    return QBrush(QColor("#D97706"))

        elif role == Qt.TextAlignmentRole:
            if col in (0, 2, 5, 9):  # Index, National ID, Phone, Date
                return Qt.AlignCenter
            return Qt.AlignRight | Qt.AlignVCenter

        elif role == Qt.BackgroundRole:
            if index.row() % 2 == 1:
                return QBrush(QColor("#F8FAFC"))  # Light alternate row

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


class PrisonersTableModel(QAbstractTableModel):
    """High-Performance Virtualized Table Model for Prisoner Personnel."""
    HEADERS = [
        "م",
        "الاسم رباعي",
        "الرقم القومي",
        "الإدارة التعليمية",
        "جهة العمل / المدرسة",
        "الهاتف",
        "رقم القضية",
        "نوع القضية",
        "الموقف الجنائي الحالي",
        "منطوق الحكم",
        "تاريخ الإفراج",
        "مكان التسكين"
    ]

    FIELD_KEYS = [
        "index",
        "full_name",
        "national_id",
        "administration_name",
        "school",
        "phone",
        "case_number",
        "case_type_name",
        "current_status",
        "court_ruling",
        "release_date",
        "housing_location"
    ]

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

        if role == Qt.DisplayRole:
            if col == 0:
                rec_num = row_item.get("record_number")
                return str(rec_num) if rec_num is not None else str(index.row() + 1)
            key = self.FIELD_KEYS[col]
            val = row_item.get(key, "")
            if key == "national_id":
                clean_nid = str(val).strip() if val is not None else ""
                if not clean_nid or "مؤقت" in clean_nid or clean_nid in ["0", "None", "nan"]:
                    return "⚠️ 0"
                elif len(clean_nid) < 14:
                    return f"⚠️ {clean_nid}"
                return clean_nid
            return str(val) if val is not None else ""

        elif role == Qt.ToolTipRole:
            if col < len(self.FIELD_KEYS) and self.FIELD_KEYS[col] == "national_id":
                val = row_item.get("national_id", "")
                clean_nid = str(val).strip() if val is not None else ""
                if not clean_nid or "مؤقت" in clean_nid or clean_nid in ["0", "None", "nan"]:
                    return "⚠️ الرقم القومي غير مسجل (0)"
                elif len(clean_nid) < 14:
                    return f"⚠️ تنبيه: الرقم القومي غير مكتمل ({len(clean_nid)} رقماً من أصل 14)"

        elif role == Qt.TextAlignmentRole:
            if col in (0, 2, 5, 6, 8, 10):  # Index, ID, Phone, Case#, Status, Release Date
                return Qt.AlignCenter
            return Qt.AlignRight | Qt.AlignVCenter

        elif role == Qt.ForegroundRole:
            if col < len(self.FIELD_KEYS) and self.FIELD_KEYS[col] == "national_id":
                val = row_item.get("national_id", "")
                clean_nid = str(val).strip() if val is not None else ""
                if not clean_nid or "مؤقت" in clean_nid or clean_nid in ["0", "None", "nan"] or len(clean_nid) < 14:
                    return QBrush(QColor("#D97706"))
            if col == 8: # Current status color coding
                status = str(row_item.get("current_status", ""))
                if "حبس" in status or "عقوبة" in status:
                    return QBrush(QColor("#DC2626"))  # Red
                elif "مفرج" in status or "براءة" in status or "عفو" in status:
                    return QBrush(QColor("#16A34A"))  # Green
                elif "إخلاء" in status or "محاكمة" in status:
                    return QBrush(QColor("#D97706"))  # Amber

        elif role == Qt.BackgroundRole:
            if col == 8: # Highlight status cell subtly
                status = str(row_item.get("current_status", ""))
                if "حبس" in status or "عقوبة" in status:
                    return QBrush(QColor("#FEF2F2"))
                elif "مفرج" in status or "براءة" in status:
                    return QBrush(QColor("#F0FDF4"))
                elif "إخلاء" in status:
                    return QBrush(QColor("#FFFBEB"))
            elif index.row() % 2 == 1:
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


class EmployeesTableModel(QAbstractTableModel):
    """High-Performance Table Model for Basic Directory Personnel."""
    HEADERS = [
        "#",
        "الاسم رباعي",
        "الرقم القومي",
        "الإدارة التعليمية",
        "المدرسة / جهة العمل",
        "رقم الهاتف",
        "سجلات الاستبعاد",
        "سجلات الحبس والقضايا"
    ]

    FIELD_KEYS = [
        "index",
        "full_name",
        "national_id",
        "administration_name",
        "school",
        "phone",
        "excluded_count",
        "prisoner_count"
    ]

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

        if role == Qt.DisplayRole:
            if col == 0:
                return str(index.row() + 1)
            key = self.FIELD_KEYS[col]
            val = row_item.get(key, "")
            if key == "national_id":
                clean_nid = str(val).strip() if val is not None else ""
                if not clean_nid or "مؤقت" in clean_nid or clean_nid in ["0", "None", "nan"]:
                    return "⚠️ 0"
                elif len(clean_nid) < 14:
                    return f"⚠️ {clean_nid}"
                return clean_nid
            return str(val) if val is not None else ""

        elif role == Qt.ToolTipRole:
            if col < len(self.FIELD_KEYS) and self.FIELD_KEYS[col] == "national_id":
                val = row_item.get("national_id", "")
                clean_nid = str(val).strip() if val is not None else ""
                if not clean_nid or "مؤقت" in clean_nid or clean_nid in ["0", "None", "nan"]:
                    return "⚠️ الرقم القومي غير مسجل (0)"
                elif len(clean_nid) < 14:
                    return f"⚠️ تنبيه: الرقم القومي غير مكتمل ({len(clean_nid)} رقماً من أصل 14)"

        elif role == Qt.ForegroundRole:
            if col < len(self.FIELD_KEYS) and self.FIELD_KEYS[col] == "national_id":
                val = row_item.get("national_id", "")
                clean_nid = str(val).strip() if val is not None else ""
                if not clean_nid or "مؤقت" in clean_nid or clean_nid in ["0", "None", "nan"] or len(clean_nid) < 14:
                    return QBrush(QColor("#D97706"))

        elif role == Qt.TextAlignmentRole:
            if col in (0, 2, 5, 6, 7):
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

