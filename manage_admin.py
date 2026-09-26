"""
Secure Administrator Account & Password Hash Utility for PakMobileSpec.

Usage:
  1. Interactive password update in local SQLite DB:
       python manage_admin.py
  2. Non-interactive password update in SQLite DB:
       python manage_admin.py --username admin --password "YourStrongPassword!"
  3. Generate a PBKDF2-HMAC-SHA256 hash for PAK_MOBILE_ADMIN_HASH env var:
       python manage_admin.py --hash-only --password "YourStrongPassword!"
"""

import argparse
import getpass
from datetime import datetime
from database import init_db, get_db_connection, hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage PakMobileSpec Administrator Credentials")
    parser.add_argument("--username", default="admin", help="Admin username (default: admin)")
    parser.add_argument("--password", default=None, help="New password (omit to enter interactively)")
    parser.add_argument(
        "--hash-only",
        action="store_true",
        help="Only print the PBKDF2-HMAC-SHA256 hash for PAK_MOBILE_ADMIN_HASH without modifying DB",
    )
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass(f"Enter new password for '{args.username}': ")
        confirm = getpass.getpass("Confirm new password: ")
        if password != confirm:
            print("Error: Passwords do not match.")
            raise SystemExit(1)

    if len(password) < 6:
        print("Error: Password must be at least 6 characters long.")
        raise SystemExit(1)

    pw_hash = hash_password(password)

    if args.hash_only:
        print(f"PAK_MOBILE_ADMIN_HASH={pw_hash}")
        return

    init_db()
    conn = get_db_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM admin_users WHERE username = ?", (args.username.strip(),))
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE admin_users SET password_hash = ? WHERE username = ?",
            (pw_hash, args.username.strip()),
        )
        print(f"[OK] Updated password for existing administrator '{args.username.strip()}'.")
    else:
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, role, created_at) VALUES (?, ?, 'Super Administrator', ?)",
            (args.username.strip(), pw_hash, now_str),
        )
        print(f"[OK] Created new administrator account '{args.username.strip()}'.")

    conn.commit()
    conn.close()
    print(f"Generated PAK_MOBILE_ADMIN_HASH (for cloud environment variables):\n{pw_hash}")


if __name__ == "__main__":
    main()
