# 🧭 مسار التنقل وتدفق الشاشات (Navigation Flow & State Preservation)
## التطبيق المكتبي الموحد — مديرية التربية والتعليم بالإسكندرية

يوضح هذا المستند كيفية تنظيم مسارات التنقل للمستخدم داخل التطبيق، والآلية المتبعة للتبديل الفوري بين النظامين مع الحفاظ التام على حالة البيانات والشاشات في الذاكرة دون إعادة تحميل.

---

### 1. مخطط التنقل الرئيسي والتفريعي (Master Navigation Flowchart)

```mermaid
flowchart TD
    AppStart(["تشغيل التطبيق (main.py)"]) --> MainWindow["النافذة الرئيسية (MainWindow)"]
    
    MainWindow --> MasterSwitcher{"الشريط التنفيذي العلوي\n(Top System Switcher)"}

    subgraph System1Flow["🏛️ مسار النظام الأول: المستبعدين والمسجونين"]
        MasterSwitcher -->|نقر زر النظام الأول| S1_Container["حاوية النظام الأول (system1_widget)"]
        S1_Container --> S1_Sidebar["القائمة الجانبية للنظام الأول"]
        S1_Sidebar --> S1_P0["📊 لوحة المؤشرات (Dashboard)"]
        S1_Sidebar --> S1_P1["🚫 سجلات المستبعدين (ExcludedView)"]
        S1_Sidebar --> S1_P2["⚖️ سجلات المسجونين (PrisonersView)"]
        S1_Sidebar --> S1_P3["📋 إدارة أنواع القضايا (ManageCaseTypesView)"]
        S1_Sidebar --> S1_P4["🔍 البحث الشامل والمتقدم (AdvancedSearchView)"]
        S1_Sidebar --> S1_P5["⚠️ كشف الأسماء المتكررة (DuplicateNamesView)"]
        S1_Sidebar --> S1_Dlg1["📥 نافذة استيراد إكسيل (ExcelImportDialog)"]
        S1_Sidebar --> S1_Dlg2["📷 نافذة المسح الضوئي الذكي (SmartScanDialog)"]
    end

    subgraph System2Flow["🏫 مسار النظام الثاني: إدارة وتأمين المدارس وحراس الأمن"]
        MasterSwitcher -->|نقر زر النظام الثاني| S2_Container["حاوية النظام الثاني (SchoolSecurityMainView)"]
        S2_Container --> S2_Sidebar["القائمة الجانبية للنظام الثاني"]
        S2_Sidebar --> S2_P0["📊 لوحة المؤشرات ومتابعة الأمان (DashboardView)"]
        S2_Sidebar --> S2_P1["🏫 إدارة وتجهيزات المدارس (SchoolsView)"]
        S2_Sidebar --> S2_P2["👮 كشوف وتوزيع حراس الأمن (GuardsView)"]
        S2_Sidebar --> S2_P3["🔍 البحث الأمني الشامل (AdvancedSearchView)"]
        S2_Sidebar --> S2_P4["📑 التقارير والإحصائيات التخصصية (ReportsView)"]
        S2_Sidebar --> S2_Dlg1["📥 نافذة استيراد كشوف تأمين المدارس (ImportDialog)"]
    end
```

---

### 2. آليات الحفاظ على حالة الواجهات (State Preservation Mechanism)

1. **الاحتفاظ بالكائنات في الذاكرة (In-Memory Singleton Views):**
   - لا يتم تدمير (Destroy) أي شاشة عند مغادرتها.
   - يتكون مكدس الصفحات الرئيسي من كائني واجهة دائمين:
     - `self.system1_widget` (فهرس 0)
     - `self.system2_widget` (فهرس 1)
   - يتم التبديل بينهما عبر استدعاء:
     ```python
     self.master_system_stack.setCurrentIndex(system_index)
     ```
   - هذا التبديل لا يستغرق أكثر من صفر مللي ثانية ولا يتطلب إعادة قراءة البيانات من القرص الصلب.

2. **بقاء مواضع التمرير وكلمات البحث (Preserved Scroll & Query State):**
   - عندما يبحث المستخدم في جدول المدارس على كلمة "المنتزه" ويصل إلى الصف رقم 45، ثم ينتقل للنظام الأول لمراجعة سجل مستبعد، ثم يعود للنظام الثاني:
     - يظل نص البحث "المنتزه" موجوداً في حقل البحث.
     - تظل القائمة المنسدلة للإدارة كما هي محددة.
     - يظل الجدول متوقفاً عند نفس الصف ومحتفظاً بالتحديد (Selection).

3. **التحديث الذكي عند وقوع تغييرات حقيقية (Event-Driven Refresh):**
   - لا يُعاد استدعاء قواعد البيانات عشوائياً عند مجرد التبديل بين الشاشات.
   - يتم التحديث فقط عند إطلاق إشارة `data_changed` إثر إضافة سجل جديد، أو تعديله، أو إتمام استيراد إكسيل، مما يوفر أقصى سرعة واستجابة ممكنة للتطبيق.
