# 🏛️ وثيقة المعمارية العامة للنظام (System Architecture Document)
## مديرية التربية والتعليم بالإسكندرية — المنظومة الرقمية الموحدة

---

### 1. نظرة عامة على النظام (Executive Overview)
تجمع هذه المنظومة بين نظامين حكوميين متكاملين ومستقلين تماماً في تطبيق مكتبي واحد موحد (Unified Single Desktop Application) مبني باستخدام **Python 3.12** و **PySide6 (Qt for Python)**، مع اعتماد واجهات رسومية تنفيذية متطورة تدعم اللغة العربية واتجاه العرض من اليمين إلى اليسار (Native RTL):

1. **نظام بيانات المستبعدين والمسجونين (System 1: Exclusions & Prisoners System):**
   - متابعة السجلات الأمنية والقضائية للعاملين بمديرية التربية والتعليم بالإسكندرية.
   - كشف التكرارات والأسماء المتشابهة، وتصنيف القضايا والمخالفات.
   - مسح ضوئي ذكي للمستندات والقرارات واستخراج البيانات عبر الذكاء الاصطناعي (Gemini Vision OCR).
   - قاعدة البيانات المستقلة: `data/exclusions_prisoners.db`.

2. **منظومة إدارة تأمين المدارس وحراس الأمن (System 2: School Security Management System):**
   - حصر وتوثيق الحالة الإنشائية والأمنية لمدارس المحافظة (المنشآت، البوابات، الفصول، التبعية).
   - إدارة تجهيزات الإطفاء والدفاع المدني (طفايات، خطوط حريق مفعلة/غير مفعلة، خراطيم صالحة/تالفة، جرادل رمل).
   - متابعة منظومات المراقبة التلفزيونية والكاميرات (الكاميرات العاملة والمعطلة، شركات الصيانة المتعاقدة).
   - إدارة وتوزيع عمال وحراس الأمن المدرسي وربطهم بالمدارس والإدارات التعليمية.
   - محرك استيراد ذكي من كشوف الإكسيل مع المطابقة الذكية للأسماء والإدارات.
   - قاعدة البيانات المستقلة: `data/school_security.db`.

---

### 2. المخطط المعماري العام للنظام (Overall System Architecture)

```mermaid
flowchart TD
    subgraph DesktopApp["🖥️ تطبيق سطح المكتب الموحد (Unified Desktop Application)"]
        direction TB
        
        subgraph TopLevel["الشريط التنفيذي الموحد (Master Dual-System Switcher)"]
            Switcher["MainWindow (QStackedWidget - Master Index 0 & 1)"]
        end

        subgraph System1["🏛️ النظام الأول: المستبعدين والمسجونين"]
            direction TB
            S1_UI["واجهات النظام الأول (UI Layer)\nExcludedView | PrisonersView | SearchView | DuplicatesView"]
            S1_DAL["طبقة البيانات (DatabaseManager)"]
            S1_DB[("exclusions_prisoners.db\nSQLite WAL Mode")]
            S1_UI --> S1_DAL --> S1_DB
        end

        subgraph System2["🏫 النظام الثاني: إدارة وتأمين المدارس وحراس الأمن"]
            direction TB
            S2_UI["واجهات النظام الثاني (UI Layer)\nSchoolsView | GuardsView | AdvancedSearch | ReportsView | Dashboard"]
            S2_Models["النماذج الافتراضية (Virtual Table Models)\nSchoolTableModel | GuardTableModel (QAbstractTableModel)"]
            S2_Services["طبقة الخدمات (Services Layer)\nSchoolService | GuardService | ExcelImporter | ExcelExporter | ImportWorker"]
            S2_DAL["مدير قاعدة البيانات المستقلة (SchoolSecurityDatabaseManager)"]
            S2_DB[("school_security.db\nSQLite WAL Mode + Foreign Keys")]
            
            S2_UI --> S2_Models
            S2_UI --> S2_Services
            S2_Services --> S2_DAL --> S2_DB
        end

        Switcher -->|Index 0| System1
        Switcher -->|Index 1| System2
    end

    subgraph ExternalIO["ملفات الإدخال والإخراج والنسخ"]
        ExcelFiles["ملفات إكسيل (بيانات تأمين المدارس.xlsx)"]
        ExternalStorage["وحدة التخزين الخارجية (E:\\ExclusionsAndPrisonersSystem)"]
    end

    ExcelFiles <-->|استيراد وتصدير آلي| S2_Services
    S1_DB -.->|مزامنة آمنة| ExternalStorage
    S2_DB -.->|مزامنة آمنة| ExternalStorage
```

---

### 3. مبادئ التصميم والمعمارية (Key Architectural Principles)

1. **الاستقلالية التامة لقواعد البيانات (Strict Database Isolation):**
   - تم الفصل الكامل بين قاعدة بيانات المستبعدين `exclusions_prisoners.db` وقاعدة بيانات تأمين المدارس `school_security.db`.
   - لا تتشارك العمليات أي جداول أو اتصالات لتجنب أي تداخل في السجلات الحساسة.

2. **عدم إعادة البناء والحفاظ على الحالة (State Preservation):**
   - يتم التبديل بين النظامين عبر `QStackedWidget` مركزي رئيسي دون تدمير أو إعادة بناء الكائنات في الذاكرة.
   - يحتفظ المستخدم بمدخلات البحث ومواضع التمرير (Scroll Positions) والمرشحات النشطة عند التنقل.

3. **النماذج الافتراضية عالية الأداء (Virtualized Virtual Models):**
   - تم استخدام `QAbstractTableModel` بدلاً من `QTableWidget` لعرض آلاف سجلات المدارس والحراس بسرعة استجابة تقل عن بضعة أجزاء من الثانية.

4. **المعالجة في الخلفية بدون تجميد (Non-Blocking Concurrency):**
   - عمليات استيراد كشوف الإكسيل الكبيرة تعمل عبر خيط عمل مستقل `QThread` (`SchoolSecurityImportWorker`) يرسل إشارات دورية بالتقدم ونسبة الإنجاز للواجهة.

5. **المطابقة الذكية للنصوص العربية (Smart Arabic Normalization):**
   - دوال مطابقة وتطبيع مخصصة في محرك SQLite (`NORMALIZE_AR`) لتوحيد الهمزات والتاء المربوطة والياء وإزالة التشكيل، لضمان دقة ربط الحراس بالمدارس.

