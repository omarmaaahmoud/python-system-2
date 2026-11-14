import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/exclusions_prisoners.db")
cur = conn.cursor()

# Find target id for 'انضمام لجماعة إرهابية'
cur.execute("SELECT id FROM CaseTypes WHERE name = 'انضمام لجماعة إرهابية'")
row = cur.fetchone()
if not row:
    cur.execute("INSERT INTO CaseTypes (name) VALUES ('انضمام لجماعة إرهابية')")
    target_id = cur.lastrowid
else:
    target_id = row[0]

# Find source ids for duplicates/typos
cur.execute("SELECT id, name FROM CaseTypes WHERE name IN ('إنضمام لحماعة إرهابية', 'إنضمام جماعة محظورة')")
sources = cur.fetchall()
print("Found sources to merge:", sources)

for src_id, src_name in sources:
    cur.execute("UPDATE ExcludedRecords SET case_type_id = ? WHERE case_type_id = ?", (target_id, src_id))
    cur.execute("UPDATE PrisonerRecords SET case_type_id = ? WHERE case_type_id = ?", (target_id, src_id))
    cur.execute("DELETE FROM CaseTypes WHERE id = ?", (src_id,))
    print(f"Merged {src_name} (ID {src_id}) into target ID {target_id}")

conn.commit()

print("\n--- Remaining Case Types ---")
cur.execute("SELECT id, name FROM CaseTypes ORDER BY id")
for r in cur.fetchall():
    print(f"ID {r[0]}: {r[1]}")

conn.close()
