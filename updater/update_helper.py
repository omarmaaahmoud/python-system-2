"""
Standalone Update Helper.
Executed as an external process to update the application after it closes.
Works completely independently from the main running executable.

Workflow:
1. Waits for the parent application PID to terminate cleanly.
2. Backs up current executable and internal runtime files.
3. Unpacks the verified update package.
   CRITICAL: STRICTLY PRESERVES data/, .db, .db-wal, .db-shm, and all user data!
4. Launches the updated application.
5. In case of any failure, rolls back from backup and relaunches the original version.
"""
import sys
import os
import time
import shutil
import zipfile
import argparse
import subprocess
import datetime
from pathlib import Path

# Protected directories and file extensions that MUST NEVER be overwritten or deleted
PROTECTED_PATH_PATTERNS = [
    "data/",
    "data\\",
    "backups/",
    "backups\\",
    "exports/",
    "exports\\",
    "uploads/",
    "uploads\\",
]
PROTECTED_EXTENSIONS = [
    ".db",
    ".db-wal",
    ".db-shm",
    ".sqlite",
    ".sqlite3",
]


def log_message(target_dir: Path, msg: str):
    """Appends timestamped log message to update_log.txt."""
    try:
        log_file = target_dir / "update_log.txt"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass
    print(f">>> {msg}")


def wait_for_process_exit(pid: int, timeout_seconds: int = 30) -> bool:
    """Waits for process with given PID to terminate using Win32 API."""
    if pid <= 0:
        return True

    if sys.platform == "win32":
        import ctypes
        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            # Process already terminated
            return True

        # Wait up to timeout_seconds
        WAIT_OBJECT_0 = 0x00000000
        res = ctypes.windll.kernel32.WaitForSingleObject(handle, timeout_seconds * 1000)
        ctypes.windll.kernel32.CloseHandle(handle)
        return res == WAIT_OBJECT_0
    else:
        # Generic POSIX / fallback loop
        start = time.time()
        while time.time() - start < timeout_seconds:
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except OSError:
                return True
        return False


def is_protected_entry(member_path: str) -> bool:
    """Checks if a zip member path touches user data or databases."""
    norm = member_path.lower().replace("/", "\\")
    parts = [p.lower() for p in Path(norm).parts]
    if parts:
        # Top-level user data or backups
        if parts[0] in ("data", "backups", "exports", "uploads"):
            return True
        # If inside bundle root wrapper
        if len(parts) >= 2 and parts[0] in ("exclusionsandprisonerssystem", "dist"):
            if parts[1] in ("data", "backups", "exports", "uploads"):
                return True
        # If in _internal/data/
        if len(parts) >= 2 and parts[0] == "_internal" and parts[1] in ("data", "backups"):
            return True

    for ext in PROTECTED_EXTENSIONS:
        if norm.endswith(ext.lower()):
            return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Standalone Update Helper for Exclusions & Prisoners System")
    parser.add_argument("--pid", type=int, default=0, help="PID of main application to wait for")
    parser.add_argument("--package", type=str, required=True, help="Path to verified update zip package")
    parser.add_argument("--target-dir", type=str, required=True, help="Target application directory")
    parser.add_argument("--executable", type=str, default="ExclusionsAndPrisonersSystem.exe", help="Executable name to relaunch")
    args = parser.parse_args()

    target_dir = Path(args.target_dir).resolve()
    package_path = Path(args.package).resolve()
    exe_name = args.executable
    target_exe = target_dir / exe_name

    backup_dir = target_dir / "_update_backup"

    log_message(target_dir, f"UpdateHelper started. Target: {target_dir}, Package: {package_path.name}")

    # 1. Wait for parent process to exit cleanly
    if args.pid > 0:
        log_message(target_dir, f"Waiting for application process (PID {args.pid}) to exit...")
        if not wait_for_process_exit(args.pid, timeout_seconds=30):
            log_message(target_dir, f"Process {args.pid} still active after 30s. Sending terminate signal...")
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/PID", str(args.pid)], capture_output=True)
                else:
                    os.kill(args.pid, 9)
            except Exception as k_err:
                log_message(target_dir, f"Failed to kill process {args.pid}: {k_err}")
            time.sleep(2.0)
            if not wait_for_process_exit(args.pid, timeout_seconds=5):
                log_message(target_dir, f"FATAL: Application process {args.pid} could not be terminated. Aborting update.")
                relaunch_app(target_exe, target_dir)
                sys.exit(1)

    # Extra short pause to allow Windows file locks to release
    time.sleep(1.0)

    # 2. Verify update package exists
    if not package_path.exists():
        log_message(target_dir, f"FATAL ERROR: Update package does not exist: {package_path}")
        relaunch_app(target_exe, target_dir)
        sys.exit(1)

    # 3. Create backup for rollback safety (including data/ snapshot)
    log_message(target_dir, "Creating rollback backup of current files...")
    try:
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

        if target_exe.exists():
            shutil.copy2(target_exe, backup_dir / exe_name)

        # Backup _internal directory if in onedir mode
        internal_dir = target_dir / "_internal"
        if internal_dir.exists():
            shutil.copytree(internal_dir, backup_dir / "_internal", dirs_exist_ok=True)

        # Safety snapshot of user data directory
        data_dir = target_dir / "data"
        if data_dir.exists():
            shutil.copytree(data_dir, backup_dir / "data", dirs_exist_ok=True)

    except Exception as e:
        log_message(target_dir, f"Backup creation warning: {e}")

    # 4. Extract update package into target directory with Zip Slip protection
    log_message(target_dir, "Extracting update package...")
    try:
        target_dir_resolved = target_dir.resolve()
        with zipfile.ZipFile(package_path, "r") as zf:
            for member in zf.infolist():
                # STRICT USER DATA PROTECTION: Skip databases, data folder, user documents
                if is_protected_entry(member.filename):
                    log_message(target_dir, f"PRESERVED PROTECTED ENTRY: {member.filename}")
                    continue

                # Strip top-level directory if archive has a root wrapper folder
                # e.g. "ExclusionsAndPrisonersSystem/..."
                parts = Path(member.filename).parts
                if parts and parts[0].lower() in ("exclusionsandprisonerssystem", "dist"):
                    rel_parts = parts[1:]
                else:
                    rel_parts = parts

                if not rel_parts:
                    continue

                dest_path = target_dir.joinpath(*rel_parts)

                # ZIP SLIP SECURITY CHECK: Ensure destination stays within target_dir
                resolved_dest = dest_path.resolve()
                if not str(resolved_dest).startswith(str(target_dir_resolved)):
                    raise SecurityError(f"Zip Slip attack detected in member: {member.filename}")

                if member.is_dir():
                    dest_path.mkdir(parents=True, exist_ok=True)
                else:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    # Try extraction with retries for transient locks
                    success = False
                    for attempt in range(5):
                        try:
                            with zf.open(member) as source, open(dest_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                            success = True
                            break
                        except Exception as write_err:
                            time.sleep(0.5)

                    if not success:
                        raise IOError(f"Could not overwrite locked file: {dest_path}")

        log_message(target_dir, "Update files extracted successfully.")

    except Exception as extract_err:
        log_message(target_dir, f"ERROR during extraction: {extract_err}")
        log_message(target_dir, "Initiating automatic rollback from backup...")
        perform_rollback(backup_dir, target_dir, exe_name)
        relaunch_app(target_exe, target_dir)
        sys.exit(1)

    # 5. Verify target executable exists
    if not target_exe.exists():
        log_message(target_dir, f"ERROR: Target executable {target_exe} is missing after extraction! Rolling back...")
        perform_rollback(backup_dir, target_dir, exe_name)
        relaunch_app(target_exe, target_dir)
        sys.exit(1)

    # 6. Verify SQLite database integrity after update
    data_dir = target_dir / "data"
    if data_dir.exists():
        import sqlite3
        for db_file in data_dir.glob("*.db"):
            log_message(target_dir, f"Verifying integrity of database: {db_file.name}...")
            try:
                conn = sqlite3.connect(str(db_file), timeout=10.0)
                cur = conn.cursor()
                cur.execute("PRAGMA integrity_check;")
                check_res = cur.fetchone()[0]
                conn.close()
                if check_res != "ok":
                    raise ValueError(f"Integrity check failed: {check_res}")
                log_message(target_dir, f"Database {db_file.name} integrity verified (OK).")
            except Exception as db_err:
                log_message(target_dir, f"CRITICAL: Database integrity failure on {db_file.name}: {db_err}")
                log_message(target_dir, "Initiating automatic rollback from backup...")
                perform_rollback(backup_dir, target_dir, exe_name)
                relaunch_app(target_exe, target_dir)
                sys.exit(1)

    # 7. Clean up temporary files on success
    try:
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
        if package_path.exists():
            package_path.unlink()
    except Exception:
        pass

    log_message(target_dir, "UPDATE SUCCESSFUL! Relaunching updated application...")

    # 8. Relaunch updated application
    relaunch_app(target_exe, target_dir)
    sys.exit(0)


def perform_rollback(backup_dir: Path, target_dir: Path, exe_name: str):
    """Restores files from backup directory in case of failure."""
    try:
        if not backup_dir.exists():
            return
        backup_exe = backup_dir / exe_name
        if backup_exe.exists():
            shutil.copy2(backup_exe, target_dir / exe_name)
        backup_internal = backup_dir / "_internal"
        if backup_internal.exists():
            shutil.copytree(backup_internal, target_dir / "_internal", dirs_exist_ok=True)
        backup_data = backup_dir / "data"
        if backup_data.exists():
            shutil.copytree(backup_data, target_dir / "data", dirs_exist_ok=True)
        log_message(target_dir, "Rollback completed successfully.")
    except Exception as e:
        log_message(target_dir, f"CRITICAL: Rollback failed: {e}")


def relaunch_app(target_exe: Path, target_dir: Path):
    """Spawns the target application as a fully detached process."""
    if not target_exe.exists():
        log_message(target_dir, f"Cannot relaunch: {target_exe} does not exist.")
        return

    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen([str(target_exe)], cwd=str(target_dir), **kwargs)
        log_message(target_dir, f"Relaunched process: {target_exe}")
    except Exception as e:
        log_message(target_dir, f"Failed to relaunch application: {e}")


if __name__ == "__main__":
    main()
