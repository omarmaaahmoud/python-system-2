import sys
import shutil
import sqlite3
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path("data/exclusions_prisoners.db")
BACKUP_PATH = Path("data/exclusions_prisoners_backup_before_wipe.db")

print(f"1. Creating backup to {BACKUP_PATH}...")
shutil.copy2(DB_PATH, BACKUP_PATH)

from database import DatabaseManager

print("2. Clearing database tables...")
db = DatabaseManager(DB_PATH)
db.clear_all_data()

# Verify counts
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
for table in ['Employees', 'ExcludedRecords', 'PrisonerRecords', 'Administrations', 'CaseTypes']:
    cur.execute(f"SELECT count(*) FROM {table}")
    print(f"   {table}: {cur.fetchone()[0]} rows")

# List clean administrations
cur.execute("SELECT id, name FROM Administrations ORDER BY id")
print("\nClean Seeded Administrations:")
for row in cur.fetchall():
    print(f"   ID {row[0]}: '{row[1]}'")

conn.close()

# Update dist database
DIST_DB = Path("dist/ExclusionsAndPrisonersSystem/data/exclusions_prisoners.db")
if DIST_DB.parent.exists():
    shutil.copy2(DB_PATH, DIST_DB)
    print("\n3. Updated dist/ExclusionsAndPrisonersSystem/data/exclusions_prisoners.db")

print("\nDatabase wiped and initialized fresh successfully!")
