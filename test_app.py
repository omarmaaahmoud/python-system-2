import sys
import os

# Enable offscreen platform for reliable headless test
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from database import DatabaseManager
from ui.main_window import MainWindow

def test_full_application():
    app = QApplication.instance() or QApplication(sys.argv)
    db = DatabaseManager()
    
    # Verify MainWindow creation
    window = MainWindow(db)
    print("MainWindow created successfully!")

    # Check dashboard stats
    stats = db.get_dashboard_stats()
    print("Dashboard Stats verified:", stats["total_employees"], "employees,", stats["total_excluded"], "excluded,", stats["total_prisoners"], "prisoners")
    assert stats["total_employees"] > 0, "Expected seeded/imported employee records"

    # Test tab switching
    for page_idx in range(5):
        window.switch_page(page_idx)
        print(f"Switched to page index {page_idx} successfully.")

    # Test search view query
    window.search_view.search_input.setText("أحمد")
    window.search_view.execute_search()
    print("Search query executed successfully, found excluded:", len(window.search_view.excluded_model._data))

    # Test filter in excluded view
    window.excluded_view.search_input.setText("الشهيد")
    window.excluded_view.load_data()
    print("Excluded view filtered successfully, count:", len(window.excluded_view.model._data))

    print("ALL APPLICATION TESTS PASSED 100%!")
    return True

if __name__ == "__main__":
    test_full_application()
