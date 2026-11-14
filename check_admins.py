import sys
import sqlite3
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("data/exclusions_prisoners.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT a.id, a.name, count(e.id) as emp_count
    FROM Administrations a
    LEFT JOIN Employees e ON e.administration_id = a.id
    GROUP BY a.id, a.name
    ORDER BY a.name
""")
rows = cur.fetchall()
print(f"Total entries in Administrations table: {len(rows)}")
print("ID\tEmployees\tName")
print("-" * 50)
for r in rows:
    print(f"{r['id']}\t{r['emp_count']}\t'{r['name']}'")
