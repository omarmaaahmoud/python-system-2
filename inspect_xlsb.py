import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

file_path = r'E:\برنامج 6-5-2026.xlsb'
xls = pd.ExcelFile(file_path, engine='pyxlsb')

# Check 'most' sheet (excluded) - skip header row
df_most = pd.read_excel(xls, sheet_name='most', header=1)
print('=== MOST (Excluded) ===')
print(f'Columns: {list(df_most.columns)}')
print(f'Total rows: {len(df_most)}')
# Count non-empty rows (column index 1 = الاسم)
name_col = df_most.columns[1]
non_empty = df_most[df_most[name_col].notna() & (df_most[name_col].astype(str).str.strip() != '')]
print(f'Non-empty rows (has name): {len(non_empty)}')
if len(non_empty) > 0:
    print('First 3 data rows:')
    for i in range(min(3, len(non_empty))):
        print(f'  Row {i}:')
        for col in df_most.columns:
            val = non_empty.iloc[i][col]
            if pd.notna(val):
                print(f'    {col}: {val}')
    print()

# Check 'masj' sheet (prisoners) - skip header row
df_masj = pd.read_excel(xls, sheet_name='masj', header=1)
print('=== MASJ (Prisoners) ===')
print(f'Columns: {list(df_masj.columns)}')
print(f'Total rows: {len(df_masj)}')
name_col2 = df_masj.columns[1]
non_empty2 = df_masj[df_masj[name_col2].notna() & (df_masj[name_col2].astype(str).str.strip() != '')]
print(f'Non-empty rows (has name): {len(non_empty2)}')
if len(non_empty2) > 0:
    print('First 3 data rows:')
    for i in range(min(3, len(non_empty2))):
        print(f'  Row {i}:')
        for col in df_masj.columns:
            val = non_empty2.iloc[i][col]
            if pd.notna(val):
                print(f'    {col}: {val}')
    print()

# Check school sheet for admin/case type reference lists
df_school = pd.read_excel(xls, sheet_name='school', header=1)
print('=== SCHOOL (Reference Data) ===')
print(f'Columns: {list(df_school.columns)}')
print('All rows:')
for i in range(min(26, len(df_school))):
    row = df_school.iloc[i]
    parts = []
    for col in df_school.columns:
        v = row[col]
        if pd.notna(v):
            parts.append(f'{col}={v}')
    if parts:
        sep = ' | '
        print(f'  [{i}] {sep.join(parts)}')
