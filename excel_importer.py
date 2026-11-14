import re
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from database import DatabaseManager


logger = logging.getLogger(__name__)

@dataclass
class ImportResult:
    success: bool = True
    total_rows: int = 0
    excluded_imported: int = 0
    prisoners_imported: int = 0
    skipped_rows: int = 0
    errors: List[str] = field(default_factory=list)
    sheets_processed: List[str] = field(default_factory=list)

    def summary_arabic(self) -> str:
        msg = f"تمت معالجة {self.total_rows} سجل من {len(self.sheets_processed)} ورقة عمل:\n"
        msg += f"• مستبعدين تم استيرادهم بنجاح: {self.excluded_imported}\n"
        msg += f"• مسجونين تم استيرادهم بنجاح: {self.prisoners_imported}\n"
        msg += f"• سجلات تم تخطيها (فارغة أو غير صالحة): {self.skipped_rows}\n"
        if self.errors:
            msg += f"\nملاحظات وتنبيهات ({len(self.errors)}):\n"
            for err in self.errors[:5]:
                msg += f"- {err}\n"
            if len(self.errors) > 5:
                msg += f"- ... و {len(self.errors) - 5} أخطاء أخرى.\n"
        return msg

class ExcelImporter:
    """High-Performance Excel Batch Importer for Educational Directorate Records.
    Supports .xlsx, .xls, and .xlsb binary formats with automatic header detection,
    data sanitization, date conversion, and SQLite batch transactions.
    """

    # Aliases for Excluded Fields
    EXCLUDED_FIELD_ALIASES = {
        "record_number": ["م", "م.", "مسلسل", "الرقم", "رقم", "id", "serial"],
        "full_name": ["الاسم", "اسم الموظف", "اسم المعلم", "الاسم رباعي", "الموظف", "name", "full_name"],
        "national_id": ["القومي", "الرقم القومي", "رقم قومي", "بطاقة الرقم القومي", "الرقم_القومي", "national_id", "nid"],
        "administration": ["الإدارة", "الادارة", "الإدارة التعليمية", "الادارة التعليمية", "administration", "admin"],
        "school": ["المدرسة", "جهة العمل", "مكان العمل", "مقر العمل", "school", "workplace"],
        "phone": ["الهاتف", "رقم الهاتف", "الموبايل", "رقم الموبايل", "التليفون", "phone", "mobile"],
        "case_type": ["نوع القضية", "القضية", "التهمة", "نوع المخالفة", "التصنيف", "case_type"],
        "current_job": ["الوظيفة الحلية", "الوظيفة الحالية", "الوظيفة", "المسمى الوظيفي", "current_job", "job"],
        "nominee_job": ["الوظيفة المرشح لها", "المرشح لها", "الوظيفة المقترحة", "nominee_job"],
        "exclusion_entity": ["جهة الاستبعاد", "الجهة المستبعد منها", "الجهة الطالبة", "exclusion_entity"],
        "exclusion_date": ["تاريخ الاستبعاد", "تاريخ القرار", "تاريخ الاستبعاد من العمل", "exclusion_date"],
        "exclusion_reason": ["سبب الاستبعاد", "الأسباب", "ملاحظات الاستبعاد", "سبب القرار", "exclusion_reason", "reason"],
    }

    # Aliases for Prisoner Fields
    PRISONER_FIELD_ALIASES = {
        "record_number": ["م", "م.", "مسلسل", "الرقم", "رقم", "id", "serial"],
        "full_name": ["الاسم", "اسم الموظف", "اسم المعلم", "الاسم رباعي", "الموظف", "name", "full_name"],
        "national_id": ["القومي", "الرقم القومي", "رقم قومي", "بطاقة الرقم القومي", "الرقم_القومي", "national_id", "nid"],
        "administration": ["الإدارة", "الادارة", "الإدارة التعليمية", "الادارة التعليمية", "administration", "admin"],
        "school": ["المدرسة", "جهة العمل", "مكان العمل", "مقر العمل", "school", "workplace"],
        "phone": ["الهاتف", "رقم الهاتف", "الموبايل", "رقم الموبايل", "التليفون", "phone", "mobile"],
        "case_number": ["رقم القضية", "القضية", "رقم المحضر", "رقم الجنحة", "رقم الجناية", "case_number"],
        "case_type": ["نوع القضية", "التهمة", "وصف التهمة", "التصنيف", "case_type"],
        "court_ruling": ["منطوق الحكم", "الحكم", "الحكم الصادر", "قرار المحكمة", "قرار النيابة", "court_ruling", "verdict"],
        "current_status": ["الوضع الراهن", "الموقف الحالي", "الحالة", "حالة المتهم", "الموقف الجنائي", "current_status", "status"],
        "release_date": ["تاريخ الإفراج", "تاريخ الخروج", "تاريخ إخلاء السبيل", "release_date"],
        "housing_location": ["مكان التسكين", "محل التسكين", "محل الإقامة", "العنوان", "مقر السكن", "housing_location", "address"],
    }

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    @staticmethod
    def clean_text(val: Any) -> str:
        """Sanitizes strings, handles NaNs, removes dummy 0s from formulas, and strips whitespace."""
        if val is None or pd.isna(val):
            return ""
        s = str(val).strip()
        if s in ["0", "0.0", "nan", "NaN", "None", "null", "-", "0x17"]:
            return ""
        if s.endswith(".0") and s[:-2].isdigit():
            s = s[:-2]
        return s

    @staticmethod
    def clean_serial(val: Any) -> Optional[int]:
        """Parses serial number integer safely."""
        if val is None or pd.isna(val):
            return None
        try:
            s = str(val).strip()
            if s.endswith(".0"):
                s = s[:-2]
            return int(s)
        except Exception:
            return None

    @staticmethod
    def clean_national_id(val: Any) -> str:
        """Sanitizes national id: removes spaces, non-digits. Returns '0' if empty or dummy zero."""
        if val is None or pd.isna(val):
            return "0"
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        s = re.sub(r"[^\d]", "", s)
        if not s or set(s) == {"0"}:
            return "0"
        return s

    @staticmethod
    def format_date(val: Any) -> str:
        """Parses dates safely and converts to standard YYYY-MM-DD string,
        supporting Excel serial dates, Eastern Arabic numerals, and multi-date strings.
        """
        if val is None or pd.isna(val):
            return ""
        s = str(val).strip()
        if s in ["0", "0.0", "nan", "NaN", "None", "-", "0x17"]:
            return ""

        # Convert Eastern Arabic digits to standard ASCII digits
        arabic_digits = "٠١٢٣٤٥٦٧٨٩"
        for i, d in enumerate(arabic_digits):
            s = s.replace(d, str(i))

        # Check for Excel numeric serial date (e.g. 45992)
        try:
            num = float(s)
            if 20000 <= num <= 75000:
                dt = pd.to_datetime(num, unit="D", origin="1899-12-30")
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        # Try parsing standard slash or dash dates
        try:
            dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
            if pd.notna(dt):
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        return s

    def _map_columns(self, df: pd.DataFrame, alias_dict: Dict[str, List[str]]) -> Dict[str, str]:
        """Maps DataFrame column names to standard internal field names."""
        column_mapping = {}
        df_cols = [str(c).strip() for c in df.columns]

        for field_name, aliases in alias_dict.items():
            for col in df_cols:
                clean_col = col.lower().replace("_", " ").replace("-", " ")
                for alias in aliases:
                    clean_alias = alias.lower().replace("_", " ").replace("-", " ")
                    if clean_col == clean_alias or clean_alias in clean_col:
                        column_mapping[field_name] = col
                        break
                if field_name in column_mapping:
                    break
        return column_mapping

    def _detect_sheet_type(self, sheet_name: str, df: pd.DataFrame) -> Optional[str]:
        """Detects whether a sheet contains Excluded records, Prisoner records, or should be skipped."""
        name_lower = sheet_name.lower().strip()

        # Known metadata / formula sheets to skip
        if name_lower in ["face", "school", "report", "report2", "all", "key"]:
            return None

        if any(k in name_lower for k in ["most", "مستبعد", "استبعاد", "excluded", "exclusion"]):
            return "excluded"
        if any(k in name_lower for k in ["masj", "سجن", "مسجون", "حبس", "محبوس", "prisoner"]):
            return "prisoners"

        # Check by column contents
        cols_str = " ".join([str(c).lower() for c in df.columns])
        if any(k in cols_str for k in ["تاريخ الاستبعاد", "جهة الاستبعاد", "الوظيفة المرشح لها", "سبب الاستبعاد"]):
            return "excluded"
        if any(k in cols_str for k in ["رقم القضية", "منطوق الحكم", "تاريخ الإفراج", "مكان التسكين", "الوضع الراهن"]):
            return "prisoners"

        return None

    def _detect_header_row(self, excel_file: pd.ExcelFile, sheet_name: str) -> int:
        """Finds the row index that contains actual column headers (skips title banners)."""
        try:
            sample = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=10, header=None)
            for idx, row in sample.iterrows():
                row_text = " ".join([str(v).strip() for v in row.values if pd.notna(v)])
                if any(kw in row_text for kw in ["الاسم", "القومي", "رقم القضية", "المدرسة", "الإدارة", "full_name"]):
                    return idx
        except Exception as e:
            logger.debug(f"Header auto-detection fallback to 0 for {sheet_name}: {e}")
        return 0

    def scan_administrations(self, file_path: str, target_mode: str = "auto") -> Dict[str, int]:
        """Scans the Excel file quickly and returns {raw_admin_name: row_count}."""
        file_str = str(file_path).strip()
        file_lower = file_str.lower()
        if file_lower.endswith(".xlsb"):
            engine = "pyxlsb"
        elif file_lower.endswith(".xls"):
            engine = "xlrd"
        else:
            engine = "openpyxl"

        counts: Dict[str, int] = {}
        try:
            excel_file = pd.ExcelFile(file_str, engine=engine)
            for sheet_name in excel_file.sheet_names:
                header_row = self._detect_header_row(excel_file, sheet_name)
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=header_row)
                except Exception:
                    continue
                if df.empty or len(df.columns) < 2:
                    continue
                if target_mode == "auto":
                    sheet_type = self._detect_sheet_type(sheet_name, df)
                else:
                    sheet_type = target_mode
                if not sheet_type:
                    continue
                mapping = self._map_columns(df, self.EXCLUDED_FIELD_ALIASES if sheet_type == "excluded" else self.PRISONER_FIELD_ALIASES)
                admin_col = mapping.get("administration")
                if admin_col and admin_col in df.columns:
                    for val in df[admin_col].dropna():
                        cleaned = self.clean_text(val)
                        if cleaned and len(cleaned) >= 2 and cleaned not in ["0", "-", "null"]:
                            counts[cleaned] = counts.get(cleaned, 0) + 1
        except Exception as e:
            logger.warning(f"Failed to scan administrations: {e}")
        return counts

    def import_excel_file(
        self, 
        file_path: str, 
        progress_callback: Optional[Callable[[int, str], None]] = None,
        target_mode: str = "auto", # 'auto', 'excluded', or 'prisoners'
        admin_mapping: Optional[Dict[str, str]] = None
    ) -> ImportResult:
        """Reads Excel file (.xlsx, .xls, .xlsb), processes batches, and saves to SQLite."""
        result = ImportResult()

        file_str = str(file_path).strip()
        file_lower = file_str.lower()

        # Select the correct engine
        if file_lower.endswith(".xlsb"):
            engine = "pyxlsb"
        elif file_lower.endswith(".xls"):
            engine = "xlrd"
        else:
            engine = "openpyxl"

        try:
            excel_file = pd.ExcelFile(file_str, engine=engine)
            sheet_names = excel_file.sheet_names
            if not sheet_names:
                result.errors.append("الملف لا يحتوي على أي أوراق عمل.")
                result.success = False
                return result
        except Exception as e:
            result.errors.append(f"تعذر فتح ملف الإكسيل ({file_str}): {str(e)}")
            result.success = False
            return result

        total_sheets = len(sheet_names)
        current_sheet_idx = 0

        # Pre-cache administrations and case types in memory for fast lookup
        conn = self.db.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM Administrations;")
            admin_cache = {row["name"].strip().lower(): row["id"] for row in cur.fetchall()}

            cur.execute("SELECT id, name FROM CaseTypes;")
            case_cache = {row["name"].strip().lower(): row["id"] for row in cur.fetchall()}

            def resolve_admin(name: str) -> Optional[int]:
                if not name:
                    return None
                cleaned = name.strip()
                target_name = cleaned
                if admin_mapping and cleaned in admin_mapping:
                    mapped = admin_mapping[cleaned]
                    if mapped == "__NONE__":
                        return None
                    elif mapped != "__NEW__":
                        target_name = mapped

                key = target_name.lower()
                if key in admin_cache:
                    return admin_cache[key]
                cur.execute("INSERT INTO Administrations (name) VALUES (?);", (target_name,))
                new_id = cur.lastrowid
                admin_cache[key] = new_id
                return new_id

            def resolve_case(name: str) -> Optional[int]:
                if not name:
                    return None
                cleaned = name.strip()
                # Smart normalization for terror/banned group cases
                from database import normalize_arabic
                norm = normalize_arabic(cleaned)
                if any(w in norm for w in ["ارهاب", "حماع", "محظور", "ارهابيه", "محظوره"]) and any(v in norm for v in ["انضمام", "جماع", "حماع"]):
                    cleaned = "انضمام لجماعة إرهابية"

                key = cleaned.lower()
                if key in case_cache:
                    return case_cache[key]
                cur.execute("INSERT INTO CaseTypes (name) VALUES (?);", (cleaned,))
                new_id = cur.lastrowid
                case_cache[key] = new_id
                return new_id

            # Cache known employees by national_id and (name, admin_id)
            cur.execute("SELECT id, full_name, national_id, administration_id FROM Employees;")
            emp_by_nid: Dict[str, int] = {}
            emp_by_name_admin: Dict[Tuple[str, Optional[int]], int] = {}
            for row in cur.fetchall():
                nid = str(row["national_id"]).strip()
                emp_id = row["id"]
                if nid and nid != "0" and not nid.startswith("مؤقت"):
                    emp_by_nid[nid] = emp_id
                emp_by_name_admin[(row["full_name"].strip(), row["administration_id"])] = emp_id

            for sheet_name in sheet_names:
                current_sheet_idx += 1

                # Detect header row first
                header_row = self._detect_header_row(excel_file, sheet_name)

                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=header_row)
                except Exception as sheet_err:
                    result.errors.append(f"تعذر قراءة ورقة العمل '{sheet_name}': {str(sheet_err)}")
                    continue

                if df.empty or len(df.columns) < 2:
                    continue

                # Determine record type
                if target_mode == "auto":
                    sheet_type = self._detect_sheet_type(sheet_name, df)
                else:
                    sheet_type = target_mode

                if not sheet_type:
                    # Skip reference or summary sheets (e.g. face, school, report, all)
                    continue

                result.sheets_processed.append(sheet_name)

                if sheet_type == "excluded":
                    mapping = self._map_columns(df, self.EXCLUDED_FIELD_ALIASES)
                else:
                    mapping = self._map_columns(df, self.PRISONER_FIELD_ALIASES)

                if "full_name" not in mapping and "national_id" not in mapping:
                    result.errors.append(f"ورقة العمل '{sheet_name}' لا تحتوي على أعمدة الاسم أو الرقم القومي.")
                    continue

                rows_in_sheet = len(df)
                result.total_rows += rows_in_sheet

                for idx, row in df.iterrows():
                    # Progress callback
                    if progress_callback and (idx % 25 == 0 or idx == rows_in_sheet - 1):
                        sheet_progress = (idx + 1) / rows_in_sheet
                        overall_pct = int(((current_sheet_idx - 1 + sheet_progress) / total_sheets) * 100)
                        progress_callback(overall_pct, f"جاري استيراد ورقة '{sheet_name}' (سجل {idx+1} من {rows_in_sheet})...")

                    # Extract record number (م)
                    record_num = self.clean_serial(row.get(mapping.get("record_number"))) if "record_number" in mapping else None

                    # Extract basic employee data
                    full_name = self.clean_text(row.get(mapping.get("full_name"))) if "full_name" in mapping else ""
                    national_id = self.clean_national_id(row.get(mapping.get("national_id"))) if "national_id" in mapping else ""
                    admin_name = self.clean_text(row.get(mapping.get("administration"))) if "administration" in mapping else ""
                    school = self.clean_text(row.get(mapping.get("school"))) if "school" in mapping else ""
                    phone = self.clean_text(row.get(mapping.get("phone"))) if "phone" in mapping else ""
                    case_type_str = self.clean_text(row.get(mapping.get("case_type"))) if "case_type" in mapping else ""

                    # Validation: must have a valid employee name (skip blank formula rows)
                    if not full_name or full_name in ["0", "0.0", "nan", "none", "-", "null"] or len(full_name.strip()) < 2:
                        result.skipped_rows += 1
                        continue

                    admin_id = resolve_admin(admin_name)
                    case_id = resolve_case(case_type_str)

                    # Determine employee ID
                    emp_id = None
                    if national_id and national_id != "0" and national_id in emp_by_nid:
                        emp_id = emp_by_nid[national_id]
                    elif (full_name, admin_id) in emp_by_name_admin:
                        emp_id = emp_by_name_admin[(full_name, admin_id)]

                    if emp_id:
                        # Existing employee: update missing details
                        cur.execute("""
                            UPDATE Employees 
                            SET national_id = CASE WHEN (national_id = '0' OR national_id LIKE '%مؤقت%') AND ? != '0' THEN ? ELSE national_id END,
                                school = CASE WHEN (school IS NULL OR school = '') THEN ? ELSE school END,
                                phone = CASE WHEN (phone IS NULL OR phone = '') THEN ? ELSE phone END,
                                administration_id = CASE WHEN administration_id IS NULL THEN ? ELSE administration_id END
                            WHERE id = ?;
                        """, (national_id, national_id, school, phone, admin_id, emp_id))
                    else:
                        # Insert new employee (default national_id to '0' if missing)
                        if not national_id or national_id.startswith("مؤقت"):
                            national_id = "0"

                        if not full_name:
                            full_name = f"موظف ({national_id})"

                        cur.execute("""
                            INSERT INTO Employees (full_name, national_id, administration_id, school, phone)
                            VALUES (?, ?, ?, ?, ?);
                        """, (full_name, national_id, admin_id, school, phone))
                        emp_id = cur.lastrowid
                        if national_id != "0":
                            emp_by_nid[national_id] = emp_id
                        emp_by_name_admin[(full_name, admin_id)] = emp_id

                    # Insert respective record
                    if sheet_type == "excluded":
                        current_job = self.clean_text(row.get(mapping.get("current_job"))) if "current_job" in mapping else ""
                        nominee_job = self.clean_text(row.get(mapping.get("nominee_job"))) if "nominee_job" in mapping else ""
                        exclusion_entity = self.clean_text(row.get(mapping.get("exclusion_entity"))) if "exclusion_entity" in mapping else ""
                        exclusion_date = self.format_date(row.get(mapping.get("exclusion_date"))) if "exclusion_date" in mapping else ""
                        exclusion_reason = self.clean_text(row.get(mapping.get("exclusion_reason"))) if "exclusion_reason" in mapping else ""

                        cur.execute("""
                            INSERT INTO ExcludedRecords (
                                record_number, employee_id, case_type_id, current_job, nominee_job,
                                exclusion_entity, exclusion_date, exclusion_reason
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """, (record_num, emp_id, case_id, current_job, nominee_job, exclusion_entity, exclusion_date, exclusion_reason))
                        result.excluded_imported += 1

                    else:  # prisoners
                        case_number = self.clean_text(row.get(mapping.get("case_number"))) if "case_number" in mapping else ""
                        court_ruling = self.clean_text(row.get(mapping.get("court_ruling"))) if "court_ruling" in mapping else ""
                        current_status = self.clean_text(row.get(mapping.get("current_status"))) if "current_status" in mapping else "على رأس العمل"
                        release_date = self.format_date(row.get(mapping.get("release_date"))) if "release_date" in mapping else ""
                        housing_location = self.clean_text(row.get(mapping.get("housing_location"))) if "housing_location" in mapping else ""

                        cur.execute("""
                            INSERT INTO PrisonerRecords (
                                record_number, employee_id, case_number, case_type_id, court_ruling,
                                current_status, release_date, housing_location
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """, (record_num, emp_id, case_number, case_id, court_ruling, current_status, release_date, housing_location))
                        result.prisoners_imported += 1

            conn.commit()
            if progress_callback:
                progress_callback(100, "اكتمل الاستيراد بنجاح!")

        except Exception as global_err:
            conn.rollback()
            result.success = False
            result.errors.append(f"حدث خطأ أثناء حفظ البيانات: {str(global_err)}")
            logger.exception("Import error")
        finally:
            conn.close()

        return result
