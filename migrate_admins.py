import sys
import shutil
import sqlite3
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = Path("data/exclusions_prisoners.db")
BACKUP_PATH = Path("data/exclusions_prisoners.db.bak")

print(f"Creating backup at {BACKUP_PATH}...")
shutil.copy2(DB_PATH, BACKUP_PATH)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = OFF;") # Temporarily disable to update cleanly
cur = conn.cursor()

# Plan of unification:
# Format: Target Name: list of existing IDs/Names to merge into it
merge_plan = {
    "المنتزه أول": [
        "إدارة المنتزه أول", "إدارة المنتزة اول", "المنتزة  اول",
        "المنتزة اول", "المنتزه اول", "منتزة اول", "منتزة أول",
        "منتزه اول", "منتزه أول"
    ],
    "المنتزه": [
        "المنتزة", "منتزة"
    ],
    "المنتزه ثان": [
        "إدارة المنتزه ثان", "منتزة ثان", "المنتزة ثان"
    ],
    "شرق": [
        "إدارة شرق التعليمية", "إدارة شرق", "شرق"
    ],
    "وسط": [
        "إدارة وسط التعليمية", "إدارة وسط", "وسط", "وســـــط"
    ],
    "غرب": [
        "إدارة غرب التعليمية", "إدارة غرب", "غرب"
    ],
    "الجمرك": [
        "إدارة الجمرك التعليمية", "إدارة الجمرك", "الجمرك"
    ],
    "العجمي": [
        "إدارة العجمي التعليمية", "العجمى", "العجمي"
    ],
    "العامرية": [
        "إدارة العامرية التعليمية", "إدارة العامرية", "العامرية"
    ],
    "برج العرب": [
        "إدارة برج العرب التعليمية", "إدارة برج العرب", "برج العرب"
    ],
    "المديرية": [
        "ديوان عام المديرية", "المديرية"
    ]
}

print("\n--- Starting Unification Process ---")

for target_name, source_names in merge_plan.items():
    # 1. Find all matching IDs
    placeholders = ",".join(["?"] * len(source_names))
    cur.execute(f"SELECT id, name FROM Administrations WHERE name IN ({placeholders})", source_names)
    matches = cur.fetchall()
    
    if not matches:
        print(f"No existing records found for {target_name}, creating new.")
        cur.execute("INSERT INTO Administrations (name) VALUES (?)", (target_name,))
        target_id = cur.lastrowid
        continue
    
    # Pick the target ID: preferably the one that already has target_name, or the first one
    existing_target = [m[0] for m in matches if m[1] == target_name]
    if existing_target:
        target_id = existing_target[0]
    else:
        target_id = matches[0][0]
        # Rename it to target_name
        cur.execute("UPDATE Administrations SET name = ? WHERE id = ?", (target_name, target_id))
    
    source_ids = [m[0] for m in matches]
    other_ids = [i for i in source_ids if i != target_id]
    
    # 2. Update Employees to point to target_id
    if other_ids:
        other_placeholders = ",".join(["?"] * len(other_ids))
        cur.execute(f"UPDATE Employees SET administration_id = ? WHERE administration_id IN ({other_placeholders})", [target_id] + other_ids)
        emp_moved = cur.rowcount
        
        # 3. Delete obsolete administration rows
        cur.execute(f"DELETE FROM Administrations WHERE id IN ({other_placeholders})", other_ids)
        deleted_count = cur.rowcount
        print(f"✅ '{target_name}' (ID: {target_id}): دمج {len(other_ids)} تصنيفات سابقة ({emp_moved} موظف تم تحديثهم، وحذف {deleted_count} صفوف مكررة).")
    else:
        print(f"ℹ️ '{target_name}' (ID: {target_id}) لا يوجد مكررات تحتاج للدمج.")

# Ensure name is exactly target_name
for target_name in merge_plan.keys():
    cur.execute("SELECT id FROM Administrations WHERE name = ?", (target_name,))

conn.commit()
conn.execute("PRAGMA foreign_keys = ON;")

print("\n--- Summary of Administrations after Unification ---")
cur.execute("""
    SELECT a.id, a.name, count(e.id) as emp_count
    FROM Administrations a
    LEFT JOIN Employees e ON e.administration_id = a.id
    GROUP BY a.id, a.name
    ORDER BY emp_count DESC
""")
for row in cur.fetchall():
    print(f"ID {row[0]}\t| {row[1]}: {row[2]} موظف")

conn.close()
