# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/omar mahmoud/.gemini/antigravity-ide/scratch/exclusions_prisoners_system/assets', 'assets'), ('C:/Users/omar mahmoud/.gemini/antigravity-ide/scratch/exclusions_prisoners_system/data', 'data')],
    hiddenimports=['pandas', 'openpyxl', 'sqlite3', 'PySide6', 'school_security', 'school_security.database', 'school_security.models', 'school_security.config', 'school_security.services', 'school_security.services.school_service', 'school_security.services.guard_service', 'school_security.services.excel_importer', 'school_security.services.excel_exporter', 'school_security.services.import_worker', 'school_security.ui', 'school_security.ui.main_view', 'school_security.ui.dashboard_view', 'school_security.ui.schools_view', 'school_security.ui.guards_view', 'school_security.ui.advanced_search_view', 'school_security.ui.reports_view', 'school_security.ui.school_dialog', 'school_security.ui.guard_dialog', 'school_security.ui.import_dialog', 'school_security.ui.table_models', 'updater', 'updater.config', 'updater.version', 'updater.github_client', 'updater.checker', 'updater.downloader', 'ui.update_dialog'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ExclusionsAndPrisonersSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/omar mahmoud/.gemini/antigravity-ide/scratch/exclusions_prisoners_system/assets/app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ExclusionsAndPrisonersSystem',
)
