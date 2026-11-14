# المنظومة الرقمية الموحدة — مديرية التربية والتعليم بالإسكندرية
### Unified Educational Directorate Management System — Alexandria

تطبيق مكتبي متكامل فائق الأداء والسرعة مبني باستخدام **Python 3.12** و **PySide6 (Qt for Python)** مع قواعد بيانات **SQLite** منفصلة ومستقلة، يقدم بوابة موحدة تجمع بين نظامين حكوميين رئيسيين:

1. **🏛️ نظام بيانات المستبعدين والمسجونين (Exclusions & Prisoners Data System):**
   - متابعة السجلات الأمنية والقضائية للعاملين بقطاع التعليم.
   - تصنيف القضايا، كشف التكرارات والأسماء المتشابهة.
   - المسح الضوئي الذكي للمستندات والقرارات بالذكاء الاصطناعي (Gemini Vision OCR).
   - قاعدة البيانات: `data/exclusions_prisoners.db`.

2. **🏫 منظومة إدارة تأمين المدارس وحراس الأمن (School Security Management System):**
   - حصر المدارس والمنشآت التعليمية والتبعية والفصول والبوابات.
   - متابعة شبكات وتجهيزات الدفاع المدني (طفايات، خطوط الحريق المفعلة وغير المفعلة، خراطيم صالحة/تالفة، جرادل رمل).
   - متابعة كاميرات المراقبة (الكاميرات العاملة والمعطلة، شركات الصيانة المتعاقدة).
   - إدارة عمال وحراس الأمن المدرسي وربطهم بالمدارس والإدارات التعليمية.
   - محرك استيراد وتفسير ذكي لكشوف تأمين المدارس وبيان حراس الأمن (`بيانات تأمين المدارس.xlsx`).
   - قاعدة البيانات المستقلة: `data/school_security.db`.

---

## 📚 التوثيق المعماري الشامل (Architecture Documentation)
يتضمن المشروع حزمة توثيق هندسية متكاملة داخل مجلد [`docs/architecture/`](docs/architecture/):
- [المعمارية العامة للنظام (System Architecture)](docs/architecture/system_architecture.md)
- [معمارية الطبقات المتعددة (Layered Architecture)](docs/architecture/layered_architecture.md)
- [مخطط المكونات والتفاعل (Component Interaction)](docs/architecture/component_diagram.md)
- [المخطط العلائقي لقواعد البيانات (Database ERD)](docs/architecture/database_erd.md)
- [مسار التنقل وتدفق الشاشات (Navigation Flow)](docs/architecture/navigation_flow.md)
- [مخططات تدفق العمليات والتسلسل (Data Flow Diagrams)](docs/architecture/data_flow_diagrams.md)
- [معمارية البناء والنشر وحفظ البيانات (Deployment Architecture)](docs/architecture/deployment_architecture.md)
- [الهيكلية الكاملة للمشروع ومسؤوليات الملفات (Project Structure)](docs/architecture/project_structure.md)

---

## 🌟 أبرز الميزات التقنية (Key Features)

1. **شريط تنفيذي علوي للتبديل الفوري بين المنظومتين (Dual-System Navigation):**
   - التبديل الفوري دون إعادة بناء الواجهات أو فقدان حالة الجداول والبحث ومواضع التمرير.
2. **استقلالية تامة للبيانات (Database Isolation):**
   - قاعدتا بيانات SQLite مستقلتان ومؤمنتان بنمط WAL مع تشغيل قيود المفاتيح الأجنبية `PRAGMA foreign_keys = ON;`.
3. **نماذج افتراضية فائقة السرعة (Virtualized QAbstractTableModel):**
   - عرض آلاف السجلات بتمرير سلس وزمن استجابة أقل من 1 مللي ثانية ودون استهلاك للذاكرة.
4. **محركات استيراد وتصدير إكسيل ذكية:**
   - قراءة تلقائية لأوراق العمل ومطابقة ذكية للمرادفات اللغوية لأسماء الأعمدة والتعامل مع الفروق الإملائية.
   - معالجة بالخلفية عبر `QThread` مع إرسال إشعارات التقدم اللحظية.
5. **لوحات قيادة تنفيذية (Executive KPI Dashboards):**
   - مؤشرات لحظية، رسوم بيانية وتوزيعات إحصائية محسوبة من السجلات الفعلية.
6. **بناء تنفيذي مدمج وحماية البيانات (Zero-Overwrite Deployment):**
   - إنتاج حزمة Windows EXE مستقلة تعمل بدون بايثون، مع استراتيجية حماية قواعد البيانات الحية في وحدة التخزين المؤمنة `E:\ExclusionsAndPrisonersSystem`.

---

## 🚀 طريقة التشغيل (How to Run)

### 1. تثبيت الحزم المطلوبة:
```bash
pip install PySide6 openpyxl pandas pillow
```

### 2. تشغيل التطبيق الموحد:
```bash
python main.py
```

### 3. بناء النسخة التنفيذية وإنشاء ملف ZIP:
```bash
python build_exe.py
```
سيتكفل السكريبت بتجميع البرنامج كاملاً مع أيقونته الرسمية في مجلد `dist/ExclusionsAndPrisonersSystem` وإنشاء الأرشيف المضغوط الموحد ونسخه لسطح المكتب والمزامنة مع القرص الخارجي `E:` تلقائياً.
