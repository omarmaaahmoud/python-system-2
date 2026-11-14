# 🔄 مخططات تدفق البيانات (Data Flow & Sequence Diagrams)
## العمليات الأساسية في منظومة تأمين المدارس وحراس الأمن

يوضح هذا المستند بالتسلسل الزمني الدقيق كيفية معالجة وتدفق البيانات بين مختلف المكونات أثناء تنفيذ العمليات الحيوية للنظام.

---

### 1. تدفق عملية استيراد كشوف الإكسيل التلقائية (Excel Bulk Import Flow)

```mermaid
sequenceDiagram
    autonumber
    actor User as المستخدم / المسؤول
    participant UI as ImportDialog
    participant Worker as ImportWorker (QThread)
    participant Importer as SchoolSecurityExcelImporter
    participant DB as SQLite (school_security.db)

    User->>UI: اختيار ملف "بيانات تأمين المدارس.xlsx" وتحديد نمط المعالجة
    User->>UI: النقر على "بدء عملية الاستيراد الآن"
    UI->>Worker: تشغيل العامل بالخلفية (Worker.start())
    
    Worker->>Importer: فتح المصنف وفحص أوراق العمل ديناميكياً
    Importer-->>Worker: التعرف على شيت المدارس وشيت الحراس ومطابقة الأعمدة
    
    Worker->>Importer: استخراج سجلات المدارس (parse_schools)
    Worker->>Importer: استخراج سجلات الحراس (parse_guards)
    
    Worker->>DB: فتح معاملة مصرفية ذرية (BEGIN TRANSACTION)
    
    loop معالجة المدارس
        Worker->>DB: فحص تكرار المدرسة بالاسم والإدارة المطبعة (NORMALIZE_AR)
        alt مدرسة جديدة
            Worker->>DB: INSERT INTO schools (...)
        else مدرسة مسجلة مسبقاً
            Worker->>DB: UPDATE schools SET (...)
        end
    end

    loop معالجة الحراس وربط التكليفات
        Worker->>DB: مطابقة الحارس بالرقم القومي (14 رقم) أو الاسم والهاتف
        alt حارس جديد
            Worker->>DB: INSERT INTO guards (...)
        else حارس مسجل
            Worker->>DB: UPDATE guards SET (...)
        end
        Worker->>DB: ربط الحارس بالمدرسة المقابلة في school_guard_assignments
    end

    Worker->>DB: توثيق العملية في import_history
    Worker->>DB: تأكيد حفظ التغييرات نهائياً (COMMIT)
    
    Worker-->>UI: إرسال إشارة الاكتمال (finished_signal مع تقرير الإحصائيات)
    UI-->>User: عرض رسالة النجاح المنمقة وتفاصيل الإدخال والتحديث
```

---

### 2. تدفق إضافة وتعديل بيانات مدرسة وتجهيزات الأمان (School Management Flow)

```mermaid
sequenceDiagram
    autonumber
    actor User as المستخدم
    participant View as SchoolsView
    participant Dlg as SchoolDialog
    participant Svc as SchoolService
    participant DB as SQLite DAL

    User->>View: النقر على "إضافة مدرسة جديدة" (أو تعديل)
    View->>Dlg: فتح نافذة المدرسة المنظمة في بطاقات أمان
    User->>Dlg: إدخال بيانات الفصول، الكاميرات، طفايات وخطوط الحريق
    User->>Dlg: النقر على "حفظ البيانات"
    Dlg->>Svc: add_school(data) أو update_school(id, data)
    Svc->>DB: تنفيذ أمر INSERT/UPDATE مع المعاملات
    DB-->>Svc: تأكيد الحفظ ورقم المعرف (school_id)
    Svc->>DB: تسجيل العملية في سجل التدقيق (audit_logs)
    Svc-->>Dlg: نجاح الحفظ
    Dlg-->>View: إطلاق إشارة data_changed
    View->>Svc: get_schools() لإعادة تحميل النموذج الافتراضي
    View-->>User: تحديث الجدول فورياً مع إبراز المدرسة
```

---

### 3. تدفق تسجيل وتعيين حارس أمن وتفادي التكرار (Guard Assignment Flow)

```mermaid
sequenceDiagram
    autonumber
    actor User as المستخدم
    participant View as GuardsView
    participant Dlg as GuardDialog
    participant Svc as GuardService
    participant DB as SQLite DAL

    User->>View: النقر على "تسجيل حارس أمن جديد"
    View->>Dlg: فتح نافذة الحارس
    User->>Dlg: إدخال الاسم، الرقم القومي، الهاتف، واختيار المدرسة
    Dlg->>Dlg: التحقق من صحة الرقم القومي (14 خانة)
    User->>Dlg: النقر على "حفظ التعيين"
    Dlg->>Svc: add_guard_with_assignment(guard_data, school_id, address)
    Svc->>DB: التحقق من عدم وجود نفس الرقم القومي مسبقاً
    alt غير مكرر
        Svc->>DB: INSERT INTO guards (...)
        Svc->>DB: INSERT INTO school_guard_assignments (school_id, guard_id, address)
        DB-->>Svc: تأكيد العملية
        Svc-->>Dlg: تم الحفظ والتكليف بنجاح
    else رقم قومي مسجل مسبقاً
        Svc-->>Dlg: تنبيه بوجود الحارس وإتاحة نقله أو تحديثه
    end
    Dlg-->>View: إشعار data_changed
    View-->>User: ظهور الحارس الجديد مرتبطاً بمدرسته في الجدول
```

---

### 4. تدفق البحث المتقدم والتقارير التحليلية والتصدير (Search & Reports Flow)

```mermaid
sequenceDiagram
    autonumber
    actor User as المستخدم
    participant UI as ReportsView / AdvancedSearchView
    participant Svc as SchoolService
    participant Exporter as SchoolSecurityExcelExporter
    participant Excel as مكتبة openpyxl

    User->>UI: اختيار تقرير (مثال: تقرير المدارس ذات الكاميرات المعطلة)
    UI->>Svc: get_schools() مع مرشحات الكاميرات والأمان
    Svc-->>UI: قائمة المدارس المطابقة
    UI-->>User: عرض النتائج في الجدول التفاعلي مع إحصائية إجمالية
    User->>UI: النقر على "تصدير التقرير إلى إكسيل 📄"
    UI->>Exporter: export_schools_report(data, file_path)
    Exporter->>Excel: إنشاء Workbook وتنسيق الترويسات والخلايا بالخط والألوان الملكية
    Exporter->>Excel: حفظ الملف في المسار المختار
    Exporter-->>UI: مسار الملف المكتمل
    UI-->>User: إظهار إشعار النجاح مع إمكانية فتح الملف مباشرة
```

