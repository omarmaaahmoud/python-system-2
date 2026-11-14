import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist" / "ExclusionsAndPrisonersSystem"
TARGET_DIR = Path("E:/ExclusionsAndPrisonersSystem")

print(f"Deploying from {DIST_DIR} to {TARGET_DIR}...")
if not DIST_DIR.exists():
    print(f"Error: {DIST_DIR} does not exist. Run build_exe.py first.")
    exit(1)

if not Path("E:/").exists():
    print("Error: Drive E: is not connected or mounted. Please connect drive E: and run again.")
    exit(1)

TARGET_DIR.mkdir(parents=True, exist_ok=True)

existing_db = TARGET_DIR / "data" / "exclusions_prisoners.db"
has_target_db = existing_db.exists() and existing_db.stat().st_size > 0

for item in DIST_DIR.iterdir():
    dest = TARGET_DIR / item.name
    if item.is_dir():
        if item.name == "data" and has_target_db:
            print("Preserving existing live database at target...")
            dest.mkdir(exist_ok=True)
            for f in item.iterdir():
                if f.name != "exclusions_prisoners.db":
                    shutil.copy2(f, dest / f.name)
        else:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
    else:
        shutil.copy2(item, dest)

print(f"Deployment to {TARGET_DIR} complete!")

