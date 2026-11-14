# 🧩 مخطط المكونات والتفاعل (Component Interaction Diagram)
## التطبيق المكتبي الموحد — مديرية التربية والتعليم بالإسكندرية

يوضح هذا المستند كيفية تفاعل مكونات النظام الموحد عند استقبال أوامر المستخدم، وتدفق البيانات بين الواجهات والخدمات وقواعد البيانات.

---

### 1. المخطط الشامل لمكونات التطبيق (Complete Component Diagram)

```mermaid
graph TB
    subgraph UserInterface["👤 تفاعل المستخدم (User Actions)"]
        User(["الموظف / متخذ القرار"])
    end

    subgraph MainWindowComponent["نافذة التطبيق الرئيسية (MainWindow)"]
        TopBar["الشريط التنفيذي العلوي\n(TopSystemSwitcherBar)"]
        MasterStack["مكدس الصفحات الرئيسي\n(master_system_stack: QStackedWidget)"]
        TopBar -->|switch_system(0)| MasterStack
        TopBar -->|switch_system(1)| MasterStack
    end

    subgraph System1Components["🏛️ النظام الأول: المستبعدين والمسجونين"]
        S1_Sidebar["شريط التنقل الجانبي"]
        S1_Views["الشاشات:\n• ExcludedView\n• PrisonersView\n• SearchView\n• DuplicatesView\n• DashboardView"]
        S1_DAL["DatabaseManager"]
        S1_DB[("exclusions_prisoners.db")]
        
        S1_Sidebar --> S1_Views
        S1_Views --> S1_DAL
        S1_DAL --> S1_DB
    end

    subgraph System2Components["🏫 النظام الثاني: إدارة وتأمين المدارس وحراس الأمن"]
        S2_MainView["الحاوية التنفيذية (SchoolSecurityMainView)"]
        S2_Sidebar["شريط المهام والتنقل الجانبي"]
        
        subgraph S2_Views["شاشات النظام الثاني"]
            V_Dash["DashboardView\nلوحة المؤشرات التفاعلية"]
            V_Sch["SchoolsView\nإدارة المدارس وتجهيزات الأمان"]
            V_Grd["GuardsView\nإدارة وتوزيع حراس الأمن"]
            V_Srch["AdvancedSearchView\nالبحث الشامل والمتقدم"]
            V_Rpt["ReportsView\nالتقارير التحليلية المتخصصة"]
        end

        subgraph S2_Dialogs["النوافذ الحوارية المتخصصة"]
            D_Sch["SchoolDialog\n(تفاصيل المدرسة + الحراس الموزعين)"]
            D_Grd["GuardDialog\n(بيانات الحارس وتعيينه بمدرسة)"]
            D_Imp["SchoolSecurityImportDialog\n(معالج الاستيراد التفاعلي)"]
        end

        subgraph S2_Models["النماذج الافتراضية للبيانات"]
            M_Sch["SchoolTableModel"]
            M_Grd["GuardTableModel"]
        end

        subgraph S2_Services["طبقة الخدمات ومنطق الأعمال"]
            S_Sch["SchoolService"]
            S_Grd["GuardService"]
            S_Imp["SchoolSecurityExcelImporter"]
            S_Exp["SchoolSecurityExcelExporter"]
            S_Wrk["SchoolSecurityImportWorker (QThread)"]
        end

        S2_DAL["SchoolSecurityDatabaseManager"]
        S2_DB[("school_security.db")]

        S2_MainView --> S2_Sidebar
        S2_MainView --> S2_Views
        S2_Views -.-> S2_Dialogs
        
        V_Sch --> M_Sch
        V_Grd --> M_Grd

        V_Dash --> S_Sch
        V_Sch --> S_Sch
        V_Grd --> S_Grd
        V_Srch --> S_Sch
        V_Rpt --> S_Sch
        D_Sch --> S_Sch
        D_Sch --> S_Grd
        D_Grd --> S_Grd
        D_Imp --> S_Wrk
        S_Wrk --> S_Imp

        S_Sch --> S2_DAL
        S_Grd --> S2_DAL
        S_Wrk --> S2_DAL
        S_Exp --> S_Sch
        S_Exp --> S_Grd

        S2_DAL --> S2_DB
    end

    User --> TopBar
    User --> S1_Sidebar
    User --> S2_Sidebar
    MasterStack -->|Index 0| S1_Views
    MasterStack -->|Index 1| S2_MainView
```

---

### 2. تدفق الإشارات والتزامن (Signal-Slot Wiring & Synchronization)

1. **تزامن تعديل البيانات في النظام الثاني:**
   - عند قيام المستخدم بإضافة أو تعديل مدرسة عبر `SchoolDialog`، يُطلق الإشعار `data_changed`.
   - تستقبل الشاشة الحاوية `SchoolSecurityMainView.on_data_updated()` هذا الإشعار وتقوم تلقائياً بتحديث:
     - أرقام وبطاقات لوحة المؤشرات (`DashboardView.load_data()`).
     - جدول المدارس وجدول الحراس الموزعين (`SchoolsView` و `GuardsView`).
     - التقارير الإحصائية النشطة (`ReportsView.generate_selected_report()`).

2. **التنقل المترابط بين الشاشات (Cross-View Navigation):**
   - عند النقر المزدوج على أي نتيجة بحث في `AdvancedSearchView`، يتم إطلاق إشارة `open_school_requested(school_id)`.
   - تقوم النافذة الرئيسية بفتح `SchoolDialog` في وضع المعاينة الفورية مع عرض قائمة الحراس المعينين بتلك المدرسة وعناوينهم وأرقام هواتفهم.
   - عند النقر على بطاقات الاختصارات في لوحة المؤشرات (Quick Actions)، ترسل الإشارة `navigate_to_page(page_index)` لنقل المستخدم مباشرة إلى الشاشة المستهدفة وتفعيل الزر المقابل في القائمة الجانبية.

