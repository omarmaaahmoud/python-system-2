"""Script to clear database and reimport fresh data from the Excel file."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from database import DatabaseManager
from excel_importer import ExcelImporter

EXCEL_PATH = r"E:\برنامج 6-5-2026.xlsb"

def main():
    print("=" * 60)
    print("بدء عملية مسح قاعدة البيانات وإعادة الاستيراد...")
    print("=" * 60)
    
    # Initialize database
    db = DatabaseManager()
    
    # Clear all existing data
    print("\n[1/3] مسح جميع البيانات القديمة...")
    db.clear_all_data()
    print("     ✅ تم مسح قاعدة البيانات بالكامل وإعادة تهيئة البيانات الأساسية.")
    
    # Re-import from Excel
    print(f"\n[2/3] بدء استيراد البيانات من الملف:")
    print(f"     {EXCEL_PATH}")
    
    importer = ExcelImporter(db)
    
    def progress(pct, msg):
        print(f"     [{pct:3d}%] {msg}")
    
    result = importer.import_excel_file(
        EXCEL_PATH, 
        progress_callback=progress,
        target_mode="auto"
    )
    
    print(f"\n[3/3] نتائج الاستيراد:")
    print(result.summary_arabic())
    
    # Show counts
    stats = db.get_dashboard_stats()
    print(f"\n{'=' * 60}")
    print(f"إحصائيات قاعدة البيانات بعد الاستيراد:")
    print(f"  - إجمالي الموظفين: {stats['total_employees']}")
    print(f"  - إجمالي المستبعدين: {stats['total_excluded']}")
    print(f"  - إجمالي المسجونين: {stats['total_prisoners']}")
    print(f"  - إجمالي السجلات: {stats['total_records']}")
    print(f"{'=' * 60}")
    
    # Show case types
    case_types = db.get_case_types()
    print(f"\nأنواع القضايا المسجلة ({len(case_types)}):")
    for ct in case_types:
        print(f"  - {ct['name']}")
    
    # Show duplicates
    dups = db.find_duplicate_names()
    if dups:
        print(f"\nالأسماء المتكررة ({len(dups)}):")
        for d in dups[:10]:
            print(f"  - {d['full_name']} (مكرر {d['name_count']} مرات) | أرقام قومية: {d['national_ids']}")
    else:
        print("\nلا توجد أسماء متكررة.")
    
    print("\n✅ اكتملت عملية إعادة الاستيراد بنجاح!")

if __name__ == "__main__":
    main()
