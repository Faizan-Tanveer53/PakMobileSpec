"""
PakMobileSpec — Safe SQLite Database Backup & Export Utility.

Creates:
  1. Hot-safe binary SQLite snapshot: backups/mobile_hub_backup_YYYYMMDD_HHMMSS.db
  2. Portable JSON catalog export:    backups/mobile_hub_export_YYYYMMDD_HHMMSS.json
  3. SQL schema + data dump:          backups/mobile_hub_dump_YYYYMMDD_HHMMSS.sql

Usage:
  python backup_db.py
"""

import os
import json
import sqlite3
from datetime import datetime
from database import BASE_DIR, get_db_path, get_db_connection


def create_backups() -> dict:
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at: {db_path}")

    backups_dir = os.path.join(BASE_DIR, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    db_backup_path = os.path.join(backups_dir, f"mobile_hub_backup_{ts}.db")
    json_export_path = os.path.join(backups_dir, f"mobile_hub_export_{ts}.json")
    sql_dump_path = os.path.join(backups_dir, f"mobile_hub_dump_{ts}.sql")

    # 1. Hot-safe SQLite binary backup using sqlite3.Connection.backup()
    src_conn = get_db_connection()
    dst_conn = sqlite3.connect(db_backup_path)
    src_conn.backup(dst_conn)
    dst_conn.close()

    # 2. Portable JSON export
    export_data = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_db": os.path.basename(db_path),
        "brands": [dict(r) for r in src_conn.execute("SELECT * FROM brands ORDER BY id").fetchall()],
        "phones": [dict(r) for r in src_conn.execute("SELECT * FROM phones ORDER BY id").fetchall()],
        "phone_variants": [dict(r) for r in src_conn.execute("SELECT * FROM phone_variants ORDER BY id").fetchall()],
        "price_history": [dict(r) for r in src_conn.execute("SELECT * FROM price_history ORDER BY id").fetchall()],
        "data_feedback_reports": [
            dict(r) for r in src_conn.execute("SELECT * FROM data_feedback_reports ORDER BY id").fetchall()
        ],
    }
    with open(json_export_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)

    # 3. SQL text dump (excluding binary media_assets blob for readability)
    with open(sql_dump_path, "w", encoding="utf-8") as f:
        for line in src_conn.iterdump():
            if "INSERT INTO \"media_assets\"" not in line:
                f.write(f"{line}\n")

    src_conn.close()
    return {
        "sqlite_backup": db_backup_path,
        "json_export": json_export_path,
        "sql_dump": sql_dump_path,
        "phones_backed_up": len(export_data["phones"]),
    }


if __name__ == "__main__":
    result = create_backups()
    print(f"[OK] Backed up {result['phones_backed_up']} phones successfully:")
    print(f"  - SQLite Binary : {result['sqlite_backup']}")
    print(f"  - JSON Export   : {result['json_export']}")
    print(f"  - SQL Dump      : {result['sql_dump']}")
