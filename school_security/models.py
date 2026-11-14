# -*- coding: utf-8 -*-
"""
Data transfer and domain models for the School Security Management System.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class School:
    school_id: Optional[int] = None
    administration: str = ""
    school_name: str = ""
    affiliation: str = ""
    manager_name: str = ""
    manager_phone: str = ""
    security_officer_name: str = ""
    security_officer_phone: str = ""
    classrooms_count: str = ""
    gates_count: str = ""
    fire_extinguishers_count: str = ""
    fire_extinguisher_type: str = ""
    fire_extinguisher_weight: str = ""
    activated_fire_lines: str = ""
    inactive_fire_lines: str = ""
    working_cameras: str = ""
    non_working_cameras: str = ""
    camera_maintenance_company: str = ""
    buckets_count: str = ""
    valid_fire_hoses: str = ""
    invalid_fire_hoses: str = ""
    notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Joined or calculated fields
    assigned_guards_count: int = 0
    assigned_guards: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Guard:
    guard_id: Optional[int] = None
    guard_name: str = ""
    national_id: str = ""
    phone: str = ""
    notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # Joined or assignment fields
    assigned_schools_count: int = 0
    assigned_schools: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchoolGuardAssignment:
    assignment_id: Optional[int] = None
    school_id: int = 0
    guard_id: int = 0
    address: str = ""
    created_at: Optional[str] = None
    # Joined fields
    school_name: str = ""
    administration: str = ""
    guard_name: str = ""
    national_id: str = ""
    phone: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImportResult:
    total_processed: int = 0
    schools_inserted: int = 0
    schools_updated: int = 0
    schools_skipped: int = 0
    guards_inserted: int = 0
    guards_updated: int = 0
    guards_skipped: int = 0
    assignments_created: int = 0
    unmatched_guards: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = True

    def summary_message(self) -> str:
        msg = (
            f"✅ اكتملت عملية الاستيراد والمعالجة بنجاح:\n\n"
            f"• المدارس: {self.schools_inserted:,} جديدة | {self.schools_updated:,} تم تحديثها | {self.schools_skipped:,} مستثناة\n"
            f"• الحراس: {self.guards_inserted:,} جدد | {self.guards_updated:,} تم تحديثهم | {self.guards_skipped:,} مستثنون\n"
            f"• روابط التوزيع المسجلة: {self.assignments_created:,} تكليف حراسة\n"
            f"• حراس بدون مدرسة مطابقة: {self.unmatched_guards:,}\n"
            f"• الأخطاء والملاحظات: {len(self.errors):,}"
        )
        if self.schools_inserted == 0 and self.guards_inserted == 0 and (self.schools_skipped > 0 or self.guards_skipped > 0):
            msg += (
                "\n\n💡 ملاحظة هامة: السجلات الموجودة في الملف مسجلة بالفعل مسبقاً في قاعدة البيانات ولذلك تم تخطي تكرارها."
                "\nإذا كنت ترغب في إعادة حفظها من الصفر، يمكنك النقر على «مسح الكل وإعادة الاستيراد»."
            )
        return msg


