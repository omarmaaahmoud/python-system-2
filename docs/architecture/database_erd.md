# 🗄️ المخطط العلائقي لقواعد البيانات (Database Entity-Relationship Diagram)
## التطبيق المكتبي الموحد — مديرية التربية والتعليم بالإسكندرية

تعتمد المنظومة على قاعدتي بيانات SQLite منفصلتين ومستقلتين تماماً، مع تفعيل نمط الكتابة المسبقة للتسجيلات (Write-Ahead Logging - WAL) وقيود التكامل المرجعي (Foreign Keys).

---

### 1. مخطط قاعدة بيانات تأمين المدارس (`school_security.db`)

```mermaid
erDiagram
    schools ||--o{ school_guard_assignments : "يُوزع عليها"
    guards ||--o{ school_guard_assignments : "يُكلف بحراستها"

    schools {
        INTEGER school_id PK "معرف المدرسة التلقائي"
        TEXT administration "الإدارة التعليمية (مثل: المنتزه أول)"
        TEXT school_name "اسم المدرسة"
        TEXT affiliation "التبعية (رسمي عربي / لغات / خاص)"
        TEXT manager_name "اسم مدير المدرسة"
        TEXT manager_phone "رقم هاتف المدير (TEXT)"
        TEXT security_officer_name "اسم مسئول الأمن بالمدرسة"
        TEXT security_officer_phone "رقم هاتف مسئول الأمن (TEXT)"
        TEXT classrooms_count "عدد الفصول"
        TEXT gates_count "عدد البوابات"
        TEXT fire_extinguishers_count "عدد طفايات الحريق"
        TEXT fire_extinguisher_type "نوع الطفايات (بودرة/رغوة/CO2)"
        TEXT fire_extinguisher_weight "وزن الطفايات (كجم)"
        TEXT activated_fire_lines "عدد خطوط الحريق المفعلة"
        TEXT inactive_fire_lines "عدد خطوط الحريق غير المفعلة"
        TEXT working_cameras "عدد الكاميرات التي تعمل"
        TEXT non_working_cameras "عدد الكاميرات المعطلة"
        TEXT camera_maintenance_company "شركة صيانة الكاميرات المتعاقدة"
        TEXT buckets_count "عدد جرادل الرمل"
        TEXT valid_fire_hoses "عدد خراطيم الحريق الصالحة"
        TEXT invalid_fire_hoses "عدد خراطيم الحريق التالفة"
        TEXT notes "ملاحظات إضافية"
        TIMESTAMP created_at "تاريخ الإضافة"
        TIMESTAMP updated_at "تاريخ آخر تعديل"
    }

    guards {
        INTEGER guard_id PK "معرف الحارس التلقائي"
        TEXT guard_name "اسم عامل الحراسة / فرد الأمن"
        TEXT national_id "الرقم القومي 14 رقم (TEXT)"
        TEXT phone "رقم هاتف الحارس (TEXT)"
        TEXT notes "ملاحظات السجل"
        TIMESTAMP created_at "تاريخ التسجيل"
        TIMESTAMP updated_at "تاريخ آخر تعديل"
    }

    school_guard_assignments {
        INTEGER assignment_id PK "معرف التكليف التلقائي"
        INTEGER school_id FK "المدرسة المعين بها"
        INTEGER guard_id FK "الحارس المكلف"
        TEXT address "عنوان المدرسة / مقر الخدمة"
        TIMESTAMP created_at "تاريخ تسجيل التكليف"
    }

    import_history {
        INTEGER id PK "معرف عملية الاستيراد"
        TEXT file_name "اسم ملف الإكسيل المصدر"
        TIMESTAMP imported_at "تاريخ وتوقيت العملية"
        INTEGER schools_count "عدد المدارس المعالجة"
        INTEGER guards_count "عدد الحراس المعالجين"
        INTEGER assignments_count "عدد روابط التوزيع المنشأة"
        TEXT status "حالة العملية (SUCCESS / FAILED)"
        TEXT log_details "تقرير المعالجة والملاحظات"
    }

    audit_logs {
        INTEGER id PK "معرف السجل"
        TEXT action_type "نوع الإجراء (ADD / UPDATE / DELETE)"
        TEXT entity_type "نوع الكيان (SCHOOL / GUARD)"
        INTEGER entity_id "معرف الكيان المتأثر"
        TEXT details "بيانات وملاحظات التعديل"
        TIMESTAMP timestamp "التوقيت الزمني الدقيق"
    }
```

---

### 2. مخطط قاعدة بيانات المستبعدين والمسجونين (`exclusions_prisoners.db`)

```mermaid
erDiagram
    case_types ||--o{ records : "تصنيف القضية"

    records {
        INTEGER id PK "معرف السجل"
        TEXT record_type "نوع السجل (excluded / prisoner)"
        TEXT name "اسم الموظف / العامل"
        TEXT national_id "الرقم القومي (TEXT)"
        TEXT phone "رقم الهاتف (TEXT)"
        TEXT job_title "المسمى الوظيفي"
        TEXT administration "الإدارة التعليمية"
        TEXT school_name "جهة العمل الأصلية / المدرسة"
        INTEGER case_type_id FK "معرف نوع القضية"
        TEXT decision_number "رقم القرار أو الحكم"
        TEXT decision_date "تاريخ صدور القرار"
        TEXT release_date "تاريخ الإفراج (للمسجونين)"
        TEXT notes "ملاحظات تفصيلية"
        TIMESTAMP created_at "تاريخ الإدخال"
    }

    case_types {
        INTEGER id PK "معرف نوع القضية"
        TEXT name "اسم التصنيف (أمني / جنائي / انقطاع)"
        TEXT description "وصف التصنيف القانوني"
        INTEGER is_active "حالة التفعيل (1 / 0)"
    }
```

---

### 3. قواعد السلامة والتكامل (Integrity Constraints & Indexing Rules)

1. **التعامل مع الأرقام الحساسة كنصوص (Text Storage for Sensitive Identifiers):**
   - تم تعيين نوع البيانات للأرقام القومية وأرقام الهواتف كـ `TEXT` دائماً. يضمن ذلك عدم حذف الصفر الأولي في أرقام مثل `010...` و `012...`، ويمنع فقدان الدقة الحسابية عند تخزين أرقام الهوية المكونة من 14 خانة.

2. **العلاقات متعدد إلى متعدد (Many-to-Many Assignment Model):**
   - جدول `school_guard_assignments` يربط المدارس بالحراس مع قيد تفرد مركب `UNIQUE (school_id, guard_id)`.
   - يمكن للمدرسة الواحدة استيعاب أكثر من حارس أمن (مثال: نوبتجيات ليلية وصباحية).
   - يمكن للحارس الواحد أن يُكلف بتأمين أكثر من منشأة متقاربة إذا لزم الأمر، دون تكرار هويته في جدول `guards`.
   - تفعيل الحذف المتعاقب `ON DELETE CASCADE` بحيث عند حذف مدرسة أو حارس، تُحذف سجلات التوزيع المرتبطة تلقائياً دون ترك سجلات يتيمة.

3. **الفهارس التحسينية (Performance Indexes):**
   - `idx_schools_name`: تسريع البحث الفوري باسم المدرسة.
   - `idx_schools_admin`: تسريع الترشيح حسب الإدارة التعليمية وتوليد مؤشرات لوحة القيادة.
   - `idx_guards_nid`: تسريع التحقق اللحظي من عدم تكرار الرقم القومي أثناء الإدخال اليدوي والاستيراد.
   - `idx_assignment_school` و `idx_assignment_guard`: تسريع عمليات الدمج العلائقي (JOIN) في الاستعلامات المركبة.

