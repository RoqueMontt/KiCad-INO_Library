import csv
import sqlite3
import os
import sys
import re
import json

# ==========================================
# CONFIGURATION
# ==========================================
# The script filename: build_kicad_library.py

base_folder = r'C:\INO_Master_Library'
database_folder_name = 'Database'

# The actual SQLite database file
db_filename = 'INO_componentsDB.db'

# The KiCad configuration file
# Naming this "INO_Components" means it shows up nicely in the Symbol Chooser
dbl_filename = 'INO_Components.kicad_dbl'

# Paths
csv_folder = os.path.join(base_folder, database_folder_name)
db_file = os.path.join(base_folder, db_filename)
dbl_file = os.path.join(base_folder, dbl_filename)

# Columns that KiCad specifically looks for to link symbols/footprints
SYSTEM_COLUMNS = ['part_id', 'symbol', 'footprint']

# Columns that should be set to "visible_on_add": true
VISIBLE_COLUMNS = ['value', 'rating']
# ==========================================
# HELPER FUNCTIONS
# ==========================================

def sanitize_sql_name(name):
    """Sanitizes names for SQL tables/columns (e.g. 'Part Number' -> 'Part_Number')"""
    clean = re.sub(r'[ -]', '_', name)
    clean = re.sub(r'[^a-zA-Z0-9_]', '', clean)
    if clean and clean[0].isdigit():
        clean = f"_{clean}"
    return clean

def get_column_display_name(col_name):
    """Generates a pretty name for KiCad (e.g. 'mpn' -> 'MPN')"""
    if col_name.lower() == 'mpn': return 'MPN'
    if col_name.lower() == 'lcsc': return 'LCSC'
    if col_name.lower() == 'mfg': return 'Manufacturer'
    return col_name.replace('_', ' ').title()

# ==========================================
# PHASE 1: GENERATE SQLITE DATABASE
# ==========================================

def update_database():
    print("PHASE 1: Updating SQLite Database...")
    
    if not os.path.exists(csv_folder):
        print(f"ERROR: Database folder not found: {csv_folder}")
        return []

    csv_files = [f for f in os.listdir(csv_folder) if f.lower().endswith('.csv')]
    if not csv_files:
        print("No CSV files found.")
        return []

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # We will store metadata about processed tables to generate the JSON later
    # Format: {'table_name': 'Capacitor', 'csv_name': 'Capacitors', 'columns': ['part_id', 'val'...]}
    processed_tables = []

    for filename in csv_files:
        full_csv_path = os.path.join(csv_folder, filename)
        
        # 1. Determine Table Name
        raw_name = os.path.splitext(filename)[0]
        table_name = sanitize_sql_name(raw_name)
        
        # 2. Read Headers & Data
        rows_to_insert = []
        headers = []
        
        try:
            with open(full_csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                try:
                    raw_headers = next(reader)
                except StopIteration:
                    print(f"  [SKIPPING] Empty file: {filename}")
                    continue

                headers = [sanitize_sql_name(h) for h in raw_headers]
                
                # Check for required primary key in first column
                if not headers: continue

                for row in reader:
                    # Pad or truncate row to match headers
                    if len(row) < len(headers): row += [''] * (len(headers) - len(row))
                    row = row[:len(headers)]
                    rows_to_insert.append(row)

        except Exception as e:
            print(f"  [ERROR] Could not read {filename}: {e}")
            continue

        # 3. Update SQL
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Create columns. First column is always Primary Key.
            col_defs = [f"{col} TEXT PRIMARY KEY" if i==0 else f"{col} TEXT" for i, col in enumerate(headers)]
            cursor.execute(f"CREATE TABLE {table_name} ({', '.join(col_defs)})")
            
            placeholders = ", ".join(["?"] * len(headers))
            cursor.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows_to_insert)
            conn.commit()
            
            print(f"  [OK] Table '{table_name}' created ({len(rows_to_insert)} parts).")
            
            # Save metadata for JSON generation
            processed_tables.append({
                'display_name': raw_name.replace('_', ' ').title(), # e.g. "Capacitors"
                'table_name': table_name,
                'columns': headers
            })

        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                print("\n!!! ERROR: DATABASE LOCKED. CLOSE KICAD !!!")
                sys.exit(1)
            print(f"  [SQL ERROR] {e}")

    conn.close()
    return processed_tables

# ==========================================
# PHASE 2: GENERATE KICAD DBL JSON
# ==========================================

def generate_kicad_dbl(tables_data):
    print("-" * 50)
    print("PHASE 2: Generating 'library_link.kicad_dbl'...")

    # Base Structure
    dbl_data = {
        "meta": {"version": 0},
        "name": "INO Master Library",
        "description": "Auto-generated Global Component Database",
        "source": {
            "type": "odbc",
            "dsn": "",
            "username": "",
            "password": "",
            "timeout_seconds": 2,
            "connection_string": "Driver={SQLite3 ODBC Driver};Database=${CWD}/" + db_filename + ";"
        },
        "libraries": []
    }

    for table in tables_data:
        cols = table['columns']
        
        # Identify special columns (case-insensitive search)
        # We need the EXACT string from the database column list
        key_col = cols[0] # Assumes first column is ID
        
        # Find symbol and footprint columns dynamically
        sym_col = next((c for c in cols if c.lower() == 'symbol'), None)
        fp_col = next((c for c in cols if c.lower() == 'footprint'), None)

        if not sym_col or not fp_col:
            print(f"  [WARNING] Table '{table['table_name']}' missing 'symbol' or 'footprint' column. Skipping JSON entry.")
            continue

        # Build Fields List
        fields = []
        properties = {}

        for col in cols:
            # Skip the Key, Symbol, and Footprint in the 'fields' list (usually not needed in chooser grid)
            # BUT we map them in 'properties'
            
            # 1. Add to Properties Map (Maps KiCad Property -> DB Column)
            # Special handling: 'Value' property usually Capitalized in KiCad
            if col.lower() == 'value':
                properties['Value'] = col
            else:
                properties[col] = col

            # 2. Add to Fields List (Visible in Chooser)
            # We exclude system columns from the chooser grid to keep it clean, 
            # unless you specifically want to see the symbol path in the grid.
            if col not in SYSTEM_COLUMNS:
                is_visible = col.lower() in [v.lower() for v in VISIBLE_COLUMNS]
                
                field_entry = {
                    "column": col,
                    "name": get_column_display_name(col),
                    "visible_on_add": is_visible,
                    "visible_in_chooser": True
                }
                fields.append(field_entry)

        # Construct Library Entry
        lib_entry = {
            "name": table['display_name'],
            "table": table['table_name'],
            "key": key_col,
            "symbols": sym_col,
            "footprints": fp_col,
            "fields": fields,
            "properties": properties
        }
        
        dbl_data['libraries'].append(lib_entry)

    # Write JSON file
    try:
        with open(dbl_file, 'w', encoding='utf-8') as f:
            json.dump(dbl_data, f, indent=4)
        print(f"  [SUCCESS] Created {dbl_filename}")
    except Exception as e:
        print(f"  [ERROR] Failed to write JSON: {e}")

# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    # Run Phase 1
    tables_found = update_database()
    
    # Run Phase 2 (only if tables were found)
    if tables_found:
        generate_kicad_dbl(tables_found)
    
    print("-" * 50)
    print("Done.")
    input("Press Enter to close...")