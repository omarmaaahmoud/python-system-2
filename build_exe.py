import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

# Force UTF-8 on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"

# Kill any running instance of the application to prevent file locking
try:
    subprocess.run(["powershell", "-Command", "Stop-Process -Name 'ExclusionsAndPrisonersSystem' -Force -ErrorAction SilentlyContinue"], capture_output=True)
except Exception:
    pass

ICON_PATH = ASSETS_DIR / "app_icon.ico"
print(">>> Starting PyInstaller build process...")

if not ICON_PATH.exists():
    from PIL import Image
    img = Image.open(ASSETS_DIR / "logo.png")
    img.save(ICON_PATH, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconsole",
    "--onedir",
    "--name=ExclusionsAndPrisonersSystem",
    f"--icon={ICON_PATH}",
    f"--add-data={ASSETS_DIR};assets",
    f"--add-data={DATA_DIR};data",
    "--hidden-import=pandas",
    "--hidden-import=openpyxl",
    "--hidden-import=sqlite3",
    "--hidden-import=PySide6",
    "--hidden-import=school_security",
    "--hidden-import=school_security.database",
    "--hidden-import=school_security.models",
    "--hidden-import=school_security.config",
    "--hidden-import=school_security.services",
    "--hidden-import=school_security.services.school_service",
    "--hidden-import=school_security.services.guard_service",
    "--hidden-import=school_security.services.excel_importer",
    "--hidden-import=school_security.services.excel_exporter",
    "--hidden-import=school_security.services.import_worker",
    "--hidden-import=school_security.ui",
    "--hidden-import=school_security.ui.main_view",
    "--hidden-import=school_security.ui.dashboard_view",
    "--hidden-import=school_security.ui.schools_view",
    "--hidden-import=school_security.ui.guards_view",
    "--hidden-import=school_security.ui.advanced_search_view",
    "--hidden-import=school_security.ui.reports_view",
    "--hidden-import=school_security.ui.school_dialog",
    "--hidden-import=school_security.ui.guard_dialog",
    "--hidden-import=school_security.ui.import_dialog",
    "--hidden-import=school_security.ui.table_models",
    "--clean",
    "-y",
    "main.py"
]

res = subprocess.run(cmd, cwd=str(BASE_DIR))
if res.returncode != 0:
    print(">>> Build failed with exit code:", res.returncode)
    sys.exit(res.returncode)

print(">>> PyInstaller build succeeded!")

out_folder = DIST_DIR / "ExclusionsAndPrisonersSystem"
dest_data = out_folder / "data"
dest_data.mkdir(exist_ok=True)

# Copy System 1 database (exclusions_prisoners.db)
db_src = DATA_DIR / "exclusions_prisoners.db"
if db_src.exists():
    shutil.copy2(db_src, dest_data / "exclusions_prisoners.db")
    print(">>> System 1 database (exclusions_prisoners.db) copied to output directory.")

# Copy System 2 database (school_security.db) if present
ss_db_src = DATA_DIR / "school_security.db"
if ss_db_src.exists():
    shutil.copy2(ss_db_src, dest_data / "school_security.db")
    print(">>> System 2 database (school_security.db) copied to output directory.")

dest_assets = out_folder / "assets"
dest_assets.mkdir(exist_ok=True)
for item in ASSETS_DIR.glob("*"):
    dest_item = dest_assets / item.name
    if item.is_dir():
        if dest_item.exists():
            shutil.rmtree(dest_item)
        shutil.copytree(item, dest_item)
    else:
        shutil.copy2(item, dest_item)

# Create Arabic README instructions inside the package
readme_content = """============================================================
نظام بيانات المستبعدين والمسجونين — مديرية التربية والتعليم
منظومة إدارة تأمين المدارس وحراس الأمن
============================================================

طريقة تشغيل البرنامج:
1. اضغط مرتين على ملف: ExclusionsAndPrisonersSystem.exe
2. سيعمل البرنامج مباشرة دون الحاجة لتثبيت أي برامج إضافية (بما فيها Python).
3. جميع البيانات والتعديلات تُحفظ تلقائياً في مجلد data المرفق.
4. يتيح البرنامج التبديل بين النظامين من شريط التنقل العلوي.

ملاحظة هامة:
• لا تقم بحذف مجلد _internal أو مجلد data لضمان استمرار عمل البرنامج وحفظ بياناتك.
• قاعدة بيانات النظام الأول: data/exclusions_prisoners.db
• قاعدة بيانات النظام الثاني: data/school_security.db
============================================================
"""
(out_folder / "تعليمات_التشغيل.txt").write_text(readme_content, encoding="utf-8")

# Package into a Single Distribution ZIP file for uploading to the internet
zip_name = "نظام_بيانات_المستبعدين_والمسجونين_كامل.zip"
zip_path = DIST_DIR / zip_name
print(f">>> Packaging full distribution ZIP: {zip_path} ...")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(out_folder):
        for file in files:
            file_full = Path(root) / file
            rel_path = file_full.relative_to(DIST_DIR)
            zf.write(file_full, rel_path)

print(f">>> ZIP Archive created successfully: {zip_path.stat().st_size / (1024*1024):.1f} MB")

# Locate user Desktop safely
desktop = None
for candidate in [
    Path(os.environ.get("USERPROFILE", "")) / "Desktop",
    Path(os.environ.get("USERPROFILE", "")) / "OneDrive" / "Desktop"
]:
    try:
        if candidate.exists():
            desktop = candidate
            break
    except Exception:
        pass

# Copy ZIP to Desktop for immediate easy upload
if desktop:
    try:
        shutil.copy2(zip_path, desktop / zip_name)
        print(">>> ZIP copied to Desktop ready for uploading!")
    except Exception as e:
        print(">>> Could not copy ZIP to Desktop:", e)

    # Refresh Desktop shortcut
    try:
        target_exe = out_folder / "ExclusionsAndPrisonersSystem.exe"
        temp_lnk = desktop / "app_sc_tmp.lnk"
        final_lnk = desktop / "نظام بيانات المستبعدين والمسجونين.lnk"
        ps_code = f"""
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut('{temp_lnk}')
$sc.TargetPath = '{target_exe}'
$sc.WorkingDirectory = '{out_folder}'
$sc.IconLocation = '{ICON_PATH},0'
$sc.Save()
"""
        subprocess.run(["powershell", "-Command", ps_code], check=False)
        if temp_lnk.exists():
            if final_lnk.exists():
                final_lnk.unlink()
            temp_lnk.rename(final_lnk)
            print(">>> Desktop shortcut refreshed successfully.")
    except Exception as e:
        print(">>> Desktop shortcut error:", e)

# Deploy build to E:\ExclusionsAndPrisonersSystem (if E drive is connected)
target_drive_e = Path("E:/ExclusionsAndPrisonersSystem")
if Path("E:/").exists():
    try:
        print(f">>> Deploying build to {target_drive_e} ...")
        target_drive_e.mkdir(parents=True, exist_ok=True)

        # Preserve System 1 database
        existing_db1 = target_drive_e / "data" / "exclusions_prisoners.db"
        has_live_db1 = existing_db1.exists() and existing_db1.stat().st_size > 0

        # Preserve System 2 database
        existing_db2 = target_drive_e / "data" / "school_security.db"
        has_live_db2 = existing_db2.exists() and existing_db2.stat().st_size > 0

        preserved_dbs = []
        if has_live_db1:
            preserved_dbs.append("exclusions_prisoners.db")
        if has_live_db2:
            preserved_dbs.append("school_security.db")

        for item in out_folder.iterdir():
            dest = target_drive_e / item.name
            if item.is_dir():
                if item.name == "data" and preserved_dbs:
                    print(f">>> Preserving existing live database(s): {', '.join(preserved_dbs)}")
                    dest.mkdir(exist_ok=True)
                    for f in item.iterdir():
                        if f.name not in preserved_dbs:
                            shutil.copy2(f, dest / f.name)
                else:
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        print(f">>> Successfully deployed to {target_drive_e}!")
        # Also copy the full ZIP archive to the root of the flash drive
        try:
            zip_on_e = Path("E:/") / zip_name
            shutil.copy2(zip_path, zip_on_e)
            print(f">>> Copied full ZIP package to flash drive root: {zip_on_e}")
        except Exception as ez:
            print(f">>> Could not copy ZIP to E root: {ez}")
    except Exception as e:
        print(f">>> Error deploying to E drive: {e}")
else:
    print(">>> Note: Drive E: is not currently mounted. The built files are ready in dist/ExclusionsAndPrisonersSystem and on Desktop.")

print(">>> BUILD AND DEPLOYMENT COMPLETE!")
