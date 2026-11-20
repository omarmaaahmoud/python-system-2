"""
PyInstaller Build Script for UpdateHelper.exe.
Builds a standalone, one-file executable that requires no Python installation.
"""
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPDATER_SCRIPT = BASE_DIR / "updater" / "update_helper.py"
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
ASSETS_DIR = BASE_DIR / "assets"
ICON_PATH = ASSETS_DIR / "app_icon.ico"

print(">>> Starting PyInstaller build for UpdateHelper.exe...")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconsole",
    "--onefile",
    "--clean",
    "--name=UpdateHelper",
    f"--distpath={DIST_DIR}",
    f"--workpath={BUILD_DIR / 'update_helper'}",
    str(UPDATER_SCRIPT),
]

if ICON_PATH.exists():
    cmd.insert(4, f"--icon={ICON_PATH}")

print("Running command:", " ".join(cmd))
res = subprocess.run(cmd)

if res.returncode == 0:
    helper_exe = DIST_DIR / "UpdateHelper.exe"
    print(f"\n>>> UpdateHelper built successfully: {helper_exe}")

    # Copy into main onedir bundle if dist/ExclusionsAndPrisonersSystem exists
    main_bundle_dir = DIST_DIR / "ExclusionsAndPrisonersSystem"
    if main_bundle_dir.exists():
        shutil.copy2(helper_exe, main_bundle_dir / "UpdateHelper.exe")
        print(f">>> Copied UpdateHelper.exe into {main_bundle_dir}")
else:
    print("\n>>> ERROR building UpdateHelper!")
    sys.exit(res.returncode)
