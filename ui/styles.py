"""Modern Executive Stylesheet (QSS) for Alexandria Educational Directorate System.
Customized for Arabic Right-To-Left (RTL) reading with a clean Dark/Light Blue palette.
"""

from config import PALETTE

MAIN_STYLESHEET = f"""
/* Global Reset and Font Settings */
* {{
    font-family: 'Segoe UI', 'Cairo', 'Tahoma', 'Arial', sans-serif;
    font-size: 13px;
    color: {PALETTE['text_main']};
}}

QMainWindow, QDialog {{
    background-color: {PALETTE['background']};
}}

QWidget {{
    outline: none;
}}

/* Top Navigation Bar / Header */
#HeaderBar {{
    background-color: {PALETTE['surface']};
    border-bottom: 1px solid {PALETTE['border_light']};
    min-height: 86px;
    padding: 0;
}}

#HeaderTitle {{
    font-size: 17px;
    font-weight: 700;
    color: {PALETTE['primary']};
}}

#HeaderSubtitle {{
    font-size: 11px;
    font-weight: 500;
    color: {PALETTE['text_muted']};
}}

/* Sidebar Menu */
#Sidebar {{
    background-color: {PALETTE['primary_dark']};
    min-width: 280px;
    max-width: 280px;
    border-left: 1px solid #334155;
}}

#SidebarLogoFrame {{
    padding: 20px 14px 14px 14px;
    border-bottom: 1px solid #334155;
}}

#SidebarAppTitle {{
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
}}

#SidebarAppSubtitle {{
    color: #94A3B8;
    font-size: 11px;
    margin-top: 2px;
}}

/* Sidebar Navigation Buttons */
#Sidebar QPushButton {{
    text-align: right;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
    color: #E2E8F0;
    background-color: transparent;
    border: none;
    border-radius: 8px;
    margin: 3px 8px;
    min-height: 38px;
}}

#Sidebar QPushButton:hover {{
    background-color: #334155;
    color: #FFFFFF;
}}

#Sidebar QPushButton:checked {{
    background-color: {PALETTE['primary']};
    color: #FFFFFF;
}}

#NavBtn_dashboard, #NavBtn_excluded, #NavBtn_prisoners, #NavBtn_addcase, #NavBtn_search, #NavBtn_duplicates, #NavBtn_import {{
    text-align: right;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
    color: #E2E8F0;
    background-color: transparent;
    border: none;
    border-radius: 8px;
    margin: 3px 8px;
    min-height: 38px;
}}

#NavBtn_dashboard:hover, #NavBtn_excluded:hover, #NavBtn_prisoners:hover, #NavBtn_addcase:hover, #NavBtn_search:hover, #NavBtn_duplicates:hover {{
    background-color: #334155;
    color: #FFFFFF;
}}

#NavBtn_dashboard:checked, #NavBtn_excluded:checked, #NavBtn_prisoners:checked, #NavBtn_addcase:checked, #NavBtn_search:checked, #NavBtn_duplicates:checked {{
    background-color: {PALETTE['primary']};
    color: #FFFFFF;
}}

#NavBtn_import {{
    background-color: #1E3A8A;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 14px;
    border: 1px solid #3B82F6;
    margin-top: 14px;
    min-height: 40px;
}}

#NavBtn_import:hover {{
    background-color: #2563EB;
    color: #FFFFFF;
}}

/* KPI & Summary Cards */
#KpiCard {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border_light']};
    border-radius: 12px;
}}

#KpiCard:hover {{
    border-color: {PALETTE['primary_light']};
}}

/* Action Dashboard Buttons */
#ActionCardBtn {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border_light']};
    border-radius: 12px;
    padding: 0px;
    min-height: 90px;
}}

#ActionCardBtn:hover {{
    border: 2px solid {PALETTE['primary_light']};
    background-color: #F8FAFC;
}}

#ActionCardBtn:pressed {{
    background-color: #EFF6FF;
}}

/* Input Fields, Text Areas and Comboboxes */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox {{
    background-color: #FFFFFF;
    border: 1.5px solid {PALETTE['border']};
    border-radius: 7px;
    padding: 7px 12px;
    min-height: 24px;
    font-size: 13px;
    color: #0F172A;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateEdit:focus {{
    border: 2px solid {PALETTE['primary_light']};
    background-color: #FFFFFF;
}}


QComboBox QAbstractItemView {{
    border: 1px solid {PALETTE['border']};
    border-radius: 6px;
    background-color: {PALETTE['surface']};
    selection-background-color: #EFF6FF;
    selection-color: {PALETTE['primary']};
    padding: 4px;
}}

/* Primary Buttons */
#PrimaryBtn {{
    background-color: {PALETTE['primary']};
    color: #FFFFFF;
    border: none;
    border-radius: 7px;
    padding: 8px 18px;
    font-weight: 600;
    min-height: 22px;
}}

#PrimaryBtn:hover {{
    background-color: {PALETTE['primary_hover']};
}}

#PrimaryBtn:pressed {{
    background-color: {PALETTE['primary_dark']};
}}

/* Secondary Buttons */
#SecondaryBtn {{
    background-color: {PALETTE['surface']};
    color: {PALETTE['text_main']};
    border: 1px solid {PALETTE['border']};
    border-radius: 7px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 22px;
}}

#SecondaryBtn:hover {{
    background-color: #F8FAFC;
    border-color: {PALETTE['text_muted']};
}}

/* Danger Buttons */
#DangerBtn {{
    background-color: {PALETTE['danger_bg']};
    color: {PALETTE['danger']};
    border: 1px solid #FECACA;
    border-radius: 7px;
    padding: 8px 16px;
    font-weight: 600;
}}

#DangerBtn:hover {{
    background-color: #FEE2E2;
    border-color: {PALETTE['danger']};
}}

/* Success Buttons */
#SuccessBtn {{
    background-color: {PALETTE['success']};
    color: #FFFFFF;
    border: none;
    border-radius: 7px;
    padding: 8px 18px;
    font-weight: 600;
}}

#SuccessBtn:hover {{
    background-color: #15803D;
}}

/* Modern QTableView */
QTableView, QTableWidget {{
    background-color: {PALETTE['surface']};
    border: 1px solid {PALETTE['border_light']};
    border-radius: 8px;
    gridline-color: #F1F5F9;
    selection-background-color: #E0E7FF;
    selection-color: #0F172A;
    outline: none;
}}

QTableView::item, QTableWidget::item {{
    padding: 8px;
    border-bottom: 1px solid #F1F5F9;
}}

QTableView::item:selected, QTableWidget::item:selected {{
    background-color: #DBEAFE;
    color: #1E3A8A;
}}

QHeaderView::section {{
    background-color: #1E3A8A;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 12px;
    padding: 8px 6px;
    border: none;
    border-bottom: 2px solid #1D4ED8;
    border-left: 1px solid #2563EB;
}}

/* QCalendarWidget Custom Styling & DatePicker Fix (prevent '...' truncation) */
QCalendarWidget {{
    background-color: #FFFFFF;
    border: 1.5px solid {PALETTE['border']};
    border-radius: 8px;
}}

QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {PALETTE['primary']};
    min-height: 40px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
}}

QCalendarWidget QToolButton {{
    color: #FFFFFF;
    background-color: transparent;
    border: none;
    border-radius: 5px;
    font-size: 13px;
    font-weight: bold;
    padding: 4px 10px;
    margin: 2px 4px;
}}

QCalendarWidget QToolButton:hover {{
    background-color: {PALETTE['primary_hover']};
}}

QCalendarWidget QToolButton:pressed {{
    background-color: {PALETTE['primary_dark']};
}}

QCalendarWidget QToolButton#qt_calendar_prevmonth,
QCalendarWidget QToolButton#qt_calendar_nextmonth {{
    min-width: 24px;
}}

QCalendarWidget QMenu {{
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid {PALETTE['border']};
    border-radius: 6px;
    padding: 4px;
}}

QCalendarWidget QSpinBox {{
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid {PALETTE['border']};
    border-radius: 5px;
    font-size: 12px;
    padding: 2px 6px;
    margin: 2px;
}}

QCalendarWidget QHeaderView::section {{
    background-color: #F1F5F9;
    color: #475569;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 0px;
    border: none;
    border-bottom: 1px solid #CBD5E1;
    border-left: none;
}}

/* Day cells in QCalendarWidget: explicitly override QTableView::item padding */
QCalendarWidget QTableView,
QCalendarWidget QTableView#qt_calendar_calendarview {{
    background-color: #FFFFFF;
    border: none;
    border-radius: 0px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    outline: none;
}}

QCalendarWidget QTableView::item,
QCalendarWidget QTableView#qt_calendar_calendarview::item,
QCalendarWidget QAbstractItemView::item {{
    padding: 1px 0px;
    margin: 0px;
    border: none;
    border-bottom: none;
    font-size: 12px;
    font-weight: 500;
}}

QCalendarWidget QTableView::item:hover,
QCalendarWidget QTableView#qt_calendar_calendarview::item:hover,
QCalendarWidget QAbstractItemView::item:hover {{
    background-color: #EFF6FF;
    border-radius: 4px;
}}

QCalendarWidget QTableView::item:selected,
QCalendarWidget QTableView#qt_calendar_calendarview::item:selected,
QCalendarWidget QAbstractItemView::item:selected {{
    background-color: #2563EB;
    color: #FFFFFF;
    border-radius: 4px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background-color: #F1F5F9;
    width: 9px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: #CBD5E1;
    min-height: 25px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #94A3B8;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background-color: #F1F5F9;
    height: 9px;
    margin: 0px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: #CBD5E1;
    min-width: 25px;
    border-radius: 4px;
}}

/* Progress Bar */
QProgressBar {{
    border: 1px solid {PALETTE['border_light']};
    border-radius: 7px;
    text-align: center;
    background-color: #E2E8F0;
    height: 18px;
    font-weight: bold;
    color: {PALETTE['text_main']};
}}

QProgressBar::chunk {{
    background-color: {PALETTE['primary']};
    border-radius: 6px;
}}

/* Group Box */
QGroupBox {{
    font-weight: 700;
    border: 1px solid {PALETTE['border_light']};
    border-radius: 9px;
    margin-top: 14px;
    padding-top: 14px;
    background-color: {PALETTE['surface']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 10px;
    color: {PALETTE['primary']};
}}

/* Context Menus & Dropdown Popups (Explicit Light & Crisp Text) */
QMenu {{
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px;
}}

QMenu::item {{
    background-color: transparent;
    padding: 8px 22px 8px 12px;
    border-radius: 6px;
    color: #0F172A;
    font-weight: 600;
    font-size: 13px;
}}

QMenu::item:selected {{
    background-color: #EFF6FF;
    color: #1E40AF;
}}

QMenu::item:disabled {{
    color: #475569;
    background-color: #F8FAFC;
    font-weight: bold;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 6px;
    margin-bottom: 4px;
}}

QMenu::separator {{
    height: 1px;
    background-color: #E2E8F0;
    margin: 4px 6px;
}}

/* Dialogs & Message Boxes */
QDialog, QMessageBox {{
    background-color: #F8FAFC;
    color: #0F172A;
}}

QMessageBox QLabel {{
    color: #0F172A;
    font-size: 13px;
    font-weight: 500;
}}
"""
