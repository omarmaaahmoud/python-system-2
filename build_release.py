"""
Comprehensive Release Workflow Script.
Builds the application, standalone UpdateHelper, packages the safe update archive (excluding user databases),
calculates SHA-256 digests, and generates release metadata.
"""
import os
import sys
import shutil
import hashlib
import zipfile
import subprocess
from pathlib import Path
from config import APP_VERSION, APP_NAME

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
APP_DIST_DIR = DIST_DIR / "ExclusionsAndPrisonersSystem"
RELEASES_DIR = BASE_DIR / "releases"
RELEASES_DIR.mkdir(parents=True, exist_ok=True)

UPDATE_ZIP_NAME = f"ExclusionsAndPrisonersSystem_Update_v{APP_VERSION}.zip"
UPDATE_ZIP_PATH = RELEASES_DIR / UPDATE_ZIP_NAME
CHECKSUMS_PATH = RELEASES_DIR / "checksums.sha256"


def calculate_sha256(filepath: Path) -> str:
    """Calculates SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(64 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def package_update_zip():
    """Packages runtime files into update zip, STRICTLY EXCLUDING any database or user data."""
    if not APP_DIST_DIR.exists():
        raise FileNotFoundError(f"App dist directory does not exist: {APP_DIST_DIR}. Please run build_exe.py first.")

    print(f"\n>>> Creating safe update package: {UPDATE_ZIP_PATH} ...")
    if UPDATE_ZIP_PATH.exists():
        UPDATE_ZIP_PATH.unlink()

    protected_names = {
        "exclusions_prisoners.db",
        "school_security.db",
        "exclusions_prisoners.db-wal",
        "exclusions_prisoners.db-shm",
        "school_security.db-wal",
        "school_security.db-shm",
    }

    packed_count = 0
    with zipfile.ZipFile(UPDATE_ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(APP_DIST_DIR):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(APP_DIST_DIR)

                # STRICT USER DATA PROTECTION: Skip databases, data folder contents, log files
                if file.lower() in protected_names or file.lower().endswith((".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".log", ".tmp")):
                    print(f"    [SKIP PROTECTED] {rel_path}")
                    continue

                # Only skip user data folders (top-level data or _internal/data), not package internal data like cv2/data
                parts = [p.lower() for p in rel_path.parts]
                if parts and parts[0] == "data":
                    print(f"    [SKIP USER DATA FOLDER] {rel_path}")
                    continue
                if len(parts) >= 2 and parts[0] == "_internal" and parts[1] == "data":
                    print(f"    [SKIP BUNDLED DATA FOLDER] {rel_path}")
                    continue

                zf.write(file_path, arcname=str(rel_path))
                packed_count += 1

    size_mb = UPDATE_ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f">>> Successfully packed {packed_count} files into update archive ({size_mb:.2f} MB).")


def main():
    print(f"=" * 60)
    print(f" RELEASE AUTOMATION WORKFLOW — v{APP_VERSION}")
    print(f"=" * 60)

    # 1. Build Standalone UpdateHelper.exe
    print("\n[Step 1/4] Building standalone UpdateHelper.exe...")
    cmd_updater = [sys.executable, "build_updater.py"]
    res_updater = subprocess.run(cmd_updater)
    if res_updater.returncode != 0:
        print("ERROR: Failed to build UpdateHelper.exe")
        sys.exit(res_updater.returncode)

    # 2. Package safe update archive (excluding data/*.db)
    print("\n[Step 2/4] Packaging update archive (excluding user databases)...")
    package_update_zip()

    # 3. Calculate SHA-256 Checksums
    print("\n[Step 3/4] Calculating cryptographic SHA-256 checksums...")
    checksum_lines = []

    update_sha256 = calculate_sha256(UPDATE_ZIP_PATH)
    checksum_lines.append(f"{update_sha256}  {UPDATE_ZIP_NAME}")
    print(f"    {UPDATE_ZIP_NAME}: {update_sha256}")

    # Check for full package if built
    full_zip = DIST_DIR / "نظام_بيانات_المستبعدين_والمسجونين_كامل.zip"
    if full_zip.exists():
        full_sha256 = calculate_sha256(full_zip)
        checksum_lines.append(f"{full_sha256}  {full_zip.name}")
        print(f"    {full_zip.name}: {full_sha256}")

    with open(CHECKSUMS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(checksum_lines) + "\n")
    print(f">>> Saved checksums to {CHECKSUMS_PATH}")

    # 4. Generate GitHub Release Instructions
    print("\n[Step 4/4] Release Ready! Publishing Instructions:")
    print("-" * 60)
    print(f"Tag: v{APP_VERSION}")
    print(f"Title: الإصدار v{APP_VERSION}")
    print(f"Assets to upload:")
    print(f"  1. {UPDATE_ZIP_PATH}")
    print(f"  2. {CHECKSUMS_PATH}")
    if full_zip.exists():
        print(f"  3. {full_zip}")
    print("\nExample GitHub CLI (gh) Command:")
    print(f'gh release create v{APP_VERSION} "{UPDATE_ZIP_PATH}" "{CHECKSUMS_PATH}" --title "الإصدار v{APP_VERSION}" --notes "تحديث جديد يتضمن تحسينات الأداء ومطابقة الأسماء بدقة."')
    print("-" * 60)


if __name__ == "__main__":
    main()
