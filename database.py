import sqlite3
import json
import hashlib
import hmac
import os
import secrets
from datetime import datetime
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_WARNING_TEXT = "DEMO / SAMPLE DATA — Verify before relying on this information."
PASSWORD_SALT = os.environ.get("PAK_MOBILE_SALT", "pakmobile_salt_v1")

# Pre-computed PBKDF2-HMAC-SHA256 hash fallback for local development when env vars are not set
DEFAULT_ADMIN_HASH = "dd640c2097311496c4592974e0a8ade22d9cfd2938cad4ffba3c24eddb07a3da"


def get_db_path() -> str:
    """Resolve the active SQLite database path from PAK_MOBILE_DB_PATH or default to ./mobile_hub.db."""
    custom_path = os.environ.get("PAK_MOBILE_DB_PATH", "").strip()
    if custom_path:
        return os.path.abspath(custom_path)
    return os.path.join(BASE_DIR, "mobile_hub.db")


DB_PATH = get_db_path()


def get_uploads_dir() -> str:
    """Resolve persistent phone images directory (Linux & Windows compatible)."""
    custom_uploads = os.environ.get("PAK_MOBILE_UPLOADS_DIR", "").strip()
    if custom_uploads:
        os.makedirs(custom_uploads, exist_ok=True)
        return os.path.abspath(custom_uploads)
    default_dir = os.path.join(BASE_DIR, "static", "images", "phones")
    os.makedirs(default_dir, exist_ok=True)
    return default_dir


def get_secret_key() -> str:
    """
    Retrieve PAK_MOBILE_SECRET from environment variables.
    If not set in environment, persist a cryptographically random 64-char hex key
    alongside the database file so session tokens remain valid across restarts
    without hard-coding any secret in source code.
    """
    env_secret = os.environ.get("PAK_MOBILE_SECRET", "").strip()
    if env_secret:
        return env_secret

    db_dir = os.path.dirname(get_db_path())
    os.makedirs(db_dir, exist_ok=True)
    secret_file = os.path.join(db_dir, ".pakmobile_secret")
    if os.path.exists(secret_file):
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                stored = f.read().strip()
                if len(stored) >= 32:
                    return stored
        except Exception:
            pass

    generated = secrets.token_hex(32)
    try:
        with open(secret_file, "w", encoding="utf-8") as f:
            f.write(generated)
    except Exception:
        pass
    return generated


SECRET_KEY = get_secret_key()


def get_db_connection() -> sqlite3.Connection:
    active_db_path = get_db_path()
    parent_dir = os.path.dirname(active_db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    conn = sqlite3.connect(active_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def _parse_datetime_safe(dt_str: Optional[str], is_end_bound: bool = False) -> Optional[datetime]:
    if not dt_str or not str(dt_str).strip():
        return None
    s = str(dt_str).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    try:
        dt = datetime.strptime(s[:10], "%Y-%m-%d")
        if is_end_bound and len(s) <= 10:
            return dt.replace(hour=23, minute=59, second=59)
        return dt
    except ValueError:
        return None


def validate_sale_inputs(
    price_pkr: Optional[int] = None,
    regular_price_pkr: Optional[int] = None,
    sale_active: Any = 0,
    sale_price_pkr: Any = None,
    sale_start_at: Optional[str] = None,
    sale_end_at: Optional[str] = None,
    sale_label: Optional[str] = None,
):
    """
    Validate and normalize sale configuration.
    Returns (is_valid: bool, error_msg: Optional[str], cleaned: dict).
    """
    base_price = int(regular_price_pkr if regular_price_pkr is not None else (price_pkr or 0))
    active_int = 1 if str(sale_active).strip().lower() in ("1", "true", "on", "yes") else 0
    clean_start = str(sale_start_at).strip() if sale_start_at and str(sale_start_at).strip() else None
    clean_end = str(sale_end_at).strip() if sale_end_at and str(sale_end_at).strip() else None
    clean_label = str(sale_label).strip() if sale_label and str(sale_label).strip() else None

    sale_price_int: Optional[int] = None
    if sale_price_pkr is not None and str(sale_price_pkr).strip() != "":
        try:
            sale_price_int = int(float(str(sale_price_pkr).strip()))
        except ValueError:
            return False, "Sale price must be a valid integer in PKR.", {}

        if sale_price_int <= 0:
            return False, "Sale price must be greater than 0 PKR.", {}

        if sale_price_int >= base_price:
            return False, "Sale price must be strictly less than the regular price (price_pkr).", {}

    if active_int == 1 and sale_price_int is None:
        return False, "Cannot enable Sale without a valid sale price less than regular price.", {}

    if clean_start and clean_end:
        st_dt = _parse_datetime_safe(clean_start, is_end_bound=False)
        en_dt = _parse_datetime_safe(clean_end, is_end_bound=True)
        if st_dt and en_dt and en_dt <= st_dt:
            return False, "Sale end date/time must be after start date/time.", {}

    return True, None, {
        "sale_active": active_int,
        "sale_price_pkr": sale_price_int,
        "sale_start_at": clean_start,
        "sale_end_at": clean_end,
        "sale_label": clean_label,
    }


def is_sale_active(phone: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """
    Centralized sale rule:
    Returns True ONLY when sale_active == 1, sale_price_pkr > 0, sale_price_pkr < price_pkr,
    and current time is within [sale_start_at, sale_end_at] if specified.
    """
    if not phone:
        return False
    try:
        if int(phone.get("sale_active") or 0) != 1:
            return False
        reg_price = int(phone.get("price_pkr") or 0)
        raw_sale = phone.get("sale_price_pkr")
        if raw_sale is None or str(raw_sale).strip() == "":
            return False
        sale_price = int(raw_sale)
        if sale_price <= 0 or sale_price >= reg_price:
            return False

        current_dt = now or datetime.now()
        start_dt = _parse_datetime_safe(phone.get("sale_start_at"), is_end_bound=False)
        if start_dt and current_dt < start_dt:
            return False

        end_dt = _parse_datetime_safe(phone.get("sale_end_at"), is_end_bound=True)
        if end_dt and current_dt > end_dt:
            return False

        return True
    except Exception:
        return False


def get_display_price(phone: Dict[str, Any], now: Optional[datetime] = None) -> int:
    if is_sale_active(phone, now=now):
        return int(phone["sale_price_pkr"])
    return int(phone.get("price_pkr") or 0)


def get_discount_percent(phone: Dict[str, Any], require_active: bool = True, now: Optional[datetime] = None) -> int:
    if not phone:
        return 0
    if require_active and not is_sale_active(phone, now=now):
        return 0
    try:
        reg_price = int(phone.get("price_pkr") or 0)
        raw_sale = phone.get("sale_price_pkr")
        if raw_sale is None or str(raw_sale).strip() == "":
            return 0
        sale_price = int(raw_sale)
        if reg_price <= 0 or sale_price <= 0 or sale_price >= reg_price:
            return 0
        return int(round((reg_price - sale_price) / reg_price * 100))
    except Exception:
        return 0


def get_sale_status(phone: Dict[str, Any], now: Optional[datetime] = None) -> str:
    if is_sale_active(phone, now=now):
        return "SALE ACTIVE"
    try:
        if int(phone.get("sale_active") or 0) == 1:
            reg_price = int(phone.get("price_pkr") or 0)
            raw_sale = phone.get("sale_price_pkr")
            if raw_sale is not None and str(raw_sale).strip() != "":
                sale_price = int(raw_sale)
                if 0 < sale_price < reg_price:
                    current_dt = now or datetime.now()
                    start_dt = _parse_datetime_safe(phone.get("sale_start_at"), is_end_bound=False)
                    if start_dt and current_dt < start_dt:
                        return "SCHEDULED"
                    end_dt = _parse_datetime_safe(phone.get("sale_end_at"), is_end_bound=True)
                    if end_dt and current_dt > end_dt:
                        return "EXPIRED"
    except Exception:
        pass
    return "NO SALE"


def dict_from_row(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    d = dict(row)
    if "gallery_json" in d and d["gallery_json"]:
        try:
            d["gallery"] = json.loads(d["gallery_json"])
        except Exception:
            d["gallery"] = []
    else:
        d["gallery"] = []

    data_status = str(d.get("data_status") or "").upper()
    if data_status == "VERIFIED" or d.get("is_demo_data") == 0:
        d["is_demo_data"] = 0
        d["data_status"] = "VERIFIED"
    else:
        d["is_demo_data"] = 1
        d["data_status"] = "DEMO/SAMPLE"

    if not d.get("currency"):
        d["currency"] = "PKR"
    if not d.get("official_variant_name"):
        d["official_variant_name"] = f"{d.get('model_name', '')} ({d.get('ram_gb', 8)}GB / {d.get('storage_gb', 128)}GB)"
    if d["is_demo_data"] == 1:
        if not d.get("verification_notes"):
            d["verification_notes"] = DEMO_WARNING_TEXT
        if not d.get("source_name"):
            d["source_name"] = "Demo / Sample Seed Catalog (Unverified)"
    d["display_size"] = d.get("display_size_inch") or 6.7
    d["rear_camera"] = d.get("main_camera") or "50 MP Triple Camera"
    d["front_camera"] = d.get("selfie_camera") or "32 MP Selfie Camera"
    d["charging_specs"] = d.get("charging") or "45W Fast Charging"
    d["network_bands"] = d.get("network") or "4G LTE / 5G Sub-6"
    d["os_version"] = d.get("os") or "Android 14 / iOS 18"

    d["last_verified_at"] = d.get("last_verified_at") or None
    cat_st = str(d.get("catalog_status") or "CURRENT").strip().upper()
    if cat_st not in ("CURRENT", "OLDER_AVAILABLE", "OUTDATED", "NEEDS_REVIEW"):
        cat_st = "CURRENT"
    d["catalog_status"] = cat_st

    # Sale / Offer fields & centralized computed properties
    d["sale_active"] = int(d.get("sale_active") or 0)
    raw_sp = d.get("sale_price_pkr")
    if raw_sp is not None and str(raw_sp).strip() != "":
        try:
            d["sale_price_pkr"] = int(raw_sp) if int(raw_sp) > 0 else None
        except Exception:
            d["sale_price_pkr"] = None
    else:
        d["sale_price_pkr"] = None
    d["sale_start_at"] = d.get("sale_start_at") or None
    d["sale_end_at"] = d.get("sale_end_at") or None
    d["sale_label"] = d.get("sale_label") or None

    d["is_sale_active"] = is_sale_active(d)
    d["display_price_pkr"] = get_display_price(d)
    d["discount_percent"] = get_discount_percent(d, require_active=True)
    d["configured_discount_percent"] = get_discount_percent(d, require_active=False)
    d["sale_status"] = get_sale_status(d)
    return d


def hash_password(password: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), PASSWORD_SALT.encode("utf-8"), 120000)
    return dk.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    computed = hash_password(password)
    return hmac.compare_digest(computed, stored_hash)


def verify_admin_credentials(username: str, password: str) -> Optional[str]:
    """
    Authenticate administrator using production environment variables first
    (PAK_MOBILE_ADMIN_USER + PAK_MOBILE_ADMIN_PASSWORD or PAK_MOBILE_ADMIN_HASH),
    falling back to the admin_users SQLite table.
    """
    clean_user = username.strip()
    env_user = os.environ.get("PAK_MOBILE_ADMIN_USER", "").strip()
    env_password = os.environ.get("PAK_MOBILE_ADMIN_PASSWORD", "")
    env_hash = os.environ.get("PAK_MOBILE_ADMIN_HASH", "").strip()

    if env_user and clean_user == env_user:
        if env_password and hmac.compare_digest(password, env_password):
            return env_user
        if env_hash and verify_password(password, env_hash):
            return env_user

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM admin_users WHERE username = ?", (clean_user,)).fetchone()
    conn.close()
    if row and verify_password(password, row["password_hash"]):
        return row["username"]
    return None


def save_media_asset_to_db(filename: str, content: bytes, mime_type: str = "image/svg+xml") -> None:
    """Persist image/SVG binary inside SQLite media_assets table so assets survive ephemeral container restarts."""
    try:
        conn = get_db_connection()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            INSERT INTO media_assets (filename, mime_type, content, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                mime_type = excluded.mime_type,
                content = excluded.content,
                updated_at = excluded.updated_at
            """,
            (filename, mime_type, sqlite3.Binary(content), now_str),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def restore_media_assets_from_db() -> int:
    """Restore any missing phone images from SQLite media_assets to static/images/phones on startup."""
    restored = 0
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT filename, content FROM media_assets").fetchall()
        conn.close()
        static_phones_dir = os.path.join(BASE_DIR, "static", "images", "phones")
        os.makedirs(static_phones_dir, exist_ok=True)
        uploads_dir = get_uploads_dir()
        for r in rows:
            fname = os.path.basename(r["filename"])
            for target_dir in {static_phones_dir, uploads_dir}:
                fpath = os.path.join(target_dir, fname)
                if not os.path.exists(fpath) and r["content"]:
                    with open(fpath, "wb") as f:
                        f.write(r["content"])
                    restored += 1
    except Exception:
        pass
    return restored


def migrate_db_schema(conn: sqlite3.Connection) -> None:
    """
    Non-destructive schema migration: adds missing columns/tables when an older database exists,
    without resetting, reseeding, or overwriting any existing phone prices, specs, or verification notes.
    """
    cursor = conn.cursor()
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(phones)").fetchall()}

    new_columns = [
        ("official_variant_name", "TEXT NOT NULL DEFAULT ''"),
        ("currency", "TEXT NOT NULL DEFAULT 'PKR'"),
        ("data_status", "TEXT NOT NULL DEFAULT 'DEMO/SAMPLE'"),
        ("source_name", "TEXT NOT NULL DEFAULT 'Demo / Sample Seed Catalog (Unverified)'"),
        ("source_url", "TEXT NOT NULL DEFAULT ''"),
        ("verification_notes", f"TEXT NOT NULL DEFAULT '{DEMO_WARNING_TEXT}'"),
        ("sale_active", "INTEGER NOT NULL DEFAULT 0"),
        ("sale_price_pkr", "INTEGER NULL"),
        ("sale_start_at", "TEXT NULL"),
        ("sale_end_at", "TEXT NULL"),
        ("sale_label", "TEXT NULL"),
        ("last_verified_at", "TEXT NULL"),
        ("catalog_status", "TEXT NOT NULL DEFAULT 'CURRENT'"),
    ]

    for col_name, col_def in new_columns:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE phones ADD COLUMN {col_name} {col_def};")

    # Only populate empty/NULL fields; NEVER overwrite existing customized values!
    cursor.execute(
        """
        UPDATE phones
        SET official_variant_name = model_name || ' (' || ram_gb || 'GB RAM / ' || storage_gb || 'GB Storage)'
        WHERE official_variant_name = '' OR official_variant_name IS NULL;
        """
    )
    cursor.execute(
        """
        UPDATE phones
        SET currency = 'PKR'
        WHERE currency = '' OR currency IS NULL;
        """
    )
    cursor.execute(
        """
        UPDATE phones
        SET data_status = CASE WHEN is_demo_data = 0 THEN 'VERIFIED' ELSE 'DEMO/SAMPLE' END
        WHERE data_status = '' OR data_status IS NULL;
        """
    )
    cursor.execute(
        """
        UPDATE phones
        SET verification_notes = ?
        WHERE is_demo_data = 1 AND (verification_notes = '' OR verification_notes IS NULL);
        """,
        (DEMO_WARNING_TEXT,),
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS data_feedback_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_id INTEGER NOT NULL,
            issue_type TEXT NOT NULL DEFAULT 'Price / Spec Correction',
            suggested_value TEXT NOT NULL DEFAULT '',
            source_reference TEXT NOT NULL DEFAULT '',
            reporter_note TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL,
            FOREIGN KEY (phone_id) REFERENCES phones(id) ON DELETE CASCADE
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS media_assets (
            filename TEXT PRIMARY KEY,
            mime_type TEXT NOT NULL DEFAULT 'image/svg+xml',
            content BLOB NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


def init_db() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            country TEXT NOT NULL DEFAULT '',
            tagline TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            accent_color TEXT NOT NULL DEFAULT '#2563eb',
            display_order INTEGER NOT NULL DEFAULT 10,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS phones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_id INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            official_variant_name TEXT NOT NULL DEFAULT '',
            slug TEXT NOT NULL UNIQUE,
            price_pkr INTEGER NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'PKR',
            pta_status TEXT NOT NULL DEFAULT 'PTA Approved / Official Warranty',
            availability TEXT NOT NULL DEFAULT 'Available',
            is_demo_data INTEGER NOT NULL DEFAULT 1,
            data_status TEXT NOT NULL DEFAULT 'DEMO/SAMPLE',
            source_name TEXT NOT NULL DEFAULT 'Demo / Sample Seed Catalog (Unverified)',
            source_url TEXT NOT NULL DEFAULT '',
            verification_notes TEXT NOT NULL DEFAULT '{DEMO_WARNING_TEXT}',
            data_source_note TEXT NOT NULL DEFAULT '{DEMO_WARNING_TEXT}',
            image_url TEXT NOT NULL DEFAULT '',
            gallery_json TEXT NOT NULL DEFAULT '[]',
            release_date TEXT NOT NULL DEFAULT '',
            ram_gb INTEGER NOT NULL DEFAULT 8,
            ram_display TEXT NOT NULL DEFAULT '8 GB',
            storage_gb INTEGER NOT NULL DEFAULT 128,
            storage_display TEXT NOT NULL DEFAULT '128 GB',
            processor TEXT NOT NULL DEFAULT '',
            display_type TEXT NOT NULL DEFAULT '',
            display_size_inch REAL NOT NULL DEFAULT 6.7,
            display_resolution TEXT NOT NULL DEFAULT '',
            refresh_rate TEXT NOT NULL DEFAULT '120Hz',
            main_camera TEXT NOT NULL DEFAULT '',
            selfie_camera TEXT NOT NULL DEFAULT '',
            battery_mah INTEGER NOT NULL DEFAULT 5000,
            charging TEXT NOT NULL DEFAULT '',
            network TEXT NOT NULL DEFAULT '2G / 3G / 4G LTE',
            is_5g INTEGER NOT NULL DEFAULT 0,
            os TEXT NOT NULL DEFAULT '',
            dimensions TEXT NOT NULL DEFAULT '',
            weight TEXT NOT NULL DEFAULT '',
            build_material TEXT NOT NULL DEFAULT '',
            sim_type TEXT NOT NULL DEFAULT 'Dual SIM (Nano-SIM, dual stand-by)',
            colors TEXT NOT NULL DEFAULT '',
            sensors TEXT NOT NULL DEFAULT 'Fingerprint, Accelerometer, Gyro, Proximity, Compass',
            summary_text TEXT NOT NULL DEFAULT '',
            is_latest INTEGER NOT NULL DEFAULT 0,
            is_popular INTEGER NOT NULL DEFAULT 0,
            views_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_phones_brand ON phones(brand_id);
        CREATE INDEX IF NOT EXISTS idx_phones_price ON phones(price_pkr);
        CREATE INDEX IF NOT EXISTS idx_phones_ram ON phones(ram_gb);
        CREATE INDEX IF NOT EXISTS idx_phones_storage ON phones(storage_gb);
        CREATE INDEX IF NOT EXISTS idx_phones_slug ON phones(slug);

        CREATE TABLE IF NOT EXISTS phone_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_id INTEGER NOT NULL,
            variant_label TEXT NOT NULL,
            ram_gb INTEGER NOT NULL DEFAULT 8,
            storage_gb INTEGER NOT NULL DEFAULT 128,
            price_pkr INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (phone_id) REFERENCES phones(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_id INTEGER NOT NULL,
            old_price_pkr INTEGER NOT NULL,
            new_price_pkr INTEGER NOT NULL,
            note TEXT NOT NULL DEFAULT 'Price updated via Admin Panel',
            changed_at TEXT NOT NULL,
            FOREIGN KEY (phone_id) REFERENCES phones(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Administrator',
            created_at TEXT NOT NULL
        );
        """
    )

    migrate_db_schema(conn)

    # Sync admin user from environment variables if provided, or create default if none exists
    admin_user_env = os.environ.get("PAK_MOBILE_ADMIN_USER", "admin").strip() or "admin"
    admin_pass_env = os.environ.get("PAK_MOBILE_ADMIN_PASSWORD", "")
    admin_hash_env = os.environ.get("PAK_MOBILE_ADMIN_HASH", "").strip()

    target_hash = (
        hash_password(admin_pass_env)
        if admin_pass_env
        else (admin_hash_env if admin_hash_env else DEFAULT_ADMIN_HASH)
    )
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT id FROM admin_users WHERE username = ?", (admin_user_env,))
    existing_admin = cursor.fetchone()
    if not existing_admin:
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (admin_user_env, target_hash, "Super Administrator", now_str),
        )
    elif admin_pass_env or admin_hash_env:
        cursor.execute(
            "UPDATE admin_users SET password_hash = ? WHERE username = ?",
            (target_hash, admin_user_env),
        )

    conn.commit()
    conn.close()
    restore_media_assets_from_db()


def format_pkr(amount: Any) -> str:
    try:
        val = int(amount)
        if val <= 0:
            return "Price TBA"
        return f"Rs. {val:,}"
    except Exception:
        return "Rs. 0"


def format_date_human(iso_str: str) -> str:
    if not iso_str:
        return "Recently Updated"
    try:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(iso_str[:19], fmt)
                return dt.strftime("%b %d, %Y")
            except ValueError:
                continue
        return iso_str
    except Exception:
        return iso_str


def get_all_brands() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT b.*,
               COUNT(p.id) as phone_count,
               MIN(p.price_pkr) as min_price_pkr,
               MAX(p.price_pkr) as max_price_pkr
        FROM brands b
        LEFT JOIN phones p ON p.brand_id = b.id
        GROUP BY b.id
        ORDER BY b.display_order ASC, b.name ASC
        """
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        bd = dict(r)
        bd["min_price"] = bd.get("min_price_pkr") or 0
        bd["max_price"] = bd.get("max_price_pkr") or 0
        result.append(bd)
    return result


def get_brand_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT b.*,
               COUNT(p.id) as phone_count,
               MIN(p.price_pkr) as min_price_pkr,
               MAX(p.price_pkr) as max_price_pkr
        FROM brands b
        LEFT JOIN phones p ON p.brand_id = b.id
        WHERE b.slug = ?
        GROUP BY b.id
        """,
        (slug,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    bd = dict(row)
    bd["min_price"] = bd.get("min_price_pkr") or 0
    bd["max_price"] = bd.get("max_price_pkr") or 0
    return bd


def get_phone_by_slug(slug: str, increment_view: bool = False) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    if increment_view:
        conn.execute("UPDATE phones SET views_count = views_count + 1 WHERE slug = ?", (slug,))
        conn.commit()
    row = conn.execute(
        """
        SELECT p.*, b.name as brand_name, b.slug as brand_slug, b.accent_color as brand_color
        FROM phones p
        JOIN brands b ON b.id = p.brand_id
        WHERE p.slug = ?
        """,
        (slug,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    phone = dict_from_row(row)
    variants = conn.execute(
        "SELECT * FROM phone_variants WHERE phone_id = ? ORDER BY price_pkr ASC",
        (phone["id"],),
    ).fetchall()
    history = conn.execute(
        "SELECT * FROM price_history WHERE phone_id = ? ORDER BY id DESC LIMIT 10",
        (phone["id"],),
    ).fetchall()
    conn.close()
    phone["variants"] = [dict(v) for v in variants]
    phone["price_history"] = [dict(h) for h in history]
    return phone


def get_phone_by_id(phone_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT p.*, b.name as brand_name, b.slug as brand_slug, b.accent_color as brand_color
        FROM phones p
        JOIN brands b ON b.id = p.brand_id
        WHERE p.id = ?
        """,
        (phone_id,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    phone = dict_from_row(row)
    variants = conn.execute(
        "SELECT * FROM phone_variants WHERE phone_id = ? ORDER BY price_pkr ASC",
        (phone["id"],),
    ).fetchall()
    history = conn.execute(
        "SELECT * FROM price_history WHERE phone_id = ? ORDER BY id DESC LIMIT 10",
        (phone["id"],),
    ).fetchall()
    conn.close()
    phone["variants"] = [dict(v) for v in variants]
    phone["price_history"] = [dict(h) for h in history]
    return phone


def query_phones(
    q: str = "",
    brand_slugs: Optional[List[str]] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    ram_list: Optional[List[int]] = None,
    storage_list: Optional[List[int]] = None,
    min_battery: Optional[int] = None,
    only_5g: bool = False,
    only_latest: bool = False,
    only_popular: bool = False,
    only_verified: bool = False,
    data_status_filter: Optional[str] = None,
    sale_filter: Optional[str] = None,
    sort_by: str = "latest",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    clauses = ["1=1"]
    params: List[Any] = []

    if q and q.strip():
        tokens = [t.strip() for t in q.strip().split() if t.strip()]
        searchable_expr = (
            "(b.name || ' ' || p.model_name || ' ' || IFNULL(p.official_variant_name, '') || ' ' || "
            "p.processor || ' ' || p.ram_display || ' ' || CAST(p.ram_gb AS TEXT) || 'GB ' || "
            "CAST(p.ram_gb AS TEXT) || ' GB ' || p.storage_display || ' ' || "
            "CAST(p.storage_gb AS TEXT) || 'GB ' || CAST(p.storage_gb AS TEXT) || ' GB')"
        )
        for token in tokens:
            clauses.append(f"{searchable_expr} LIKE ?")
            params.append(f"%{token}%")

    if brand_slugs:
        clean_slugs = [s.strip() for s in brand_slugs if s.strip()]
        if clean_slugs:
            placeholders = ",".join(["?"] * len(clean_slugs))
            clauses.append(f"b.slug IN ({placeholders})")
            params.extend(clean_slugs)

    if min_price is not None and min_price > 0:
        clauses.append("p.price_pkr >= ?")
        params.append(min_price)

    if max_price is not None and max_price > 0:
        clauses.append("p.price_pkr <= ?")
        params.append(max_price)

    if ram_list:
        clean_rams = [int(r) for r in ram_list if r]
        if clean_rams:
            placeholders = ",".join(["?"] * len(clean_rams))
            clauses.append(f"p.ram_gb IN ({placeholders})")
            params.extend(clean_rams)

    if storage_list:
        clean_storages = [int(s) for s in storage_list if s]
        if clean_storages:
            placeholders = ",".join(["?"] * len(clean_storages))
            clauses.append(f"p.storage_gb IN ({placeholders})")
            params.extend(clean_storages)

    if min_battery is not None and min_battery > 0:
        clauses.append("p.battery_mah >= ?")
        params.append(min_battery)

    if only_5g:
        clauses.append("p.is_5g = 1")

    if only_latest:
        clauses.append("p.is_latest = 1 AND IFNULL(p.catalog_status, 'CURRENT') = 'CURRENT' AND p.availability != 'Discontinued'")

    if only_popular:
        clauses.append("p.is_popular = 1")

    if only_verified or (data_status_filter and data_status_filter.upper() == "VERIFIED"):
        clauses.append("(p.is_demo_data = 0 OR p.data_status = 'VERIFIED')")
    elif data_status_filter and data_status_filter.upper() in ("DEMO", "DEMO/SAMPLE"):
        clauses.append("(p.is_demo_data = 1 AND p.data_status != 'VERIFIED')")
    elif data_status_filter and data_status_filter.upper() == "OUTDATED":
        clauses.append("(IFNULL(p.catalog_status, 'CURRENT') = 'OUTDATED' OR p.availability = 'Discontinued')")
    elif data_status_filter and data_status_filter.upper() in ("NEEDS_REVIEW", "NEEDS REVIEW"):
        clauses.append("IFNULL(p.catalog_status, 'CURRENT') = 'NEEDS_REVIEW'")
    elif data_status_filter and data_status_filter.upper() == "CURRENT":
        clauses.append("IFNULL(p.catalog_status, 'CURRENT') = 'CURRENT'")

    order_sql = "p.updated_at DESC, p.id DESC"
    if sort_by == "price_asc":
        order_sql = "p.price_pkr ASC"
    elif sort_by == "price_desc":
        order_sql = "p.price_pkr DESC"
    elif sort_by == "popular":
        order_sql = "p.is_popular DESC, p.views_count DESC, p.id DESC"
    elif sort_by == "ram_desc":
        order_sql = "p.ram_gb DESC, p.storage_gb DESC"
    elif sort_by == "latest":
        order_sql = (
            "CASE WHEN p.is_latest = 1 AND IFNULL(p.catalog_status, 'CURRENT') = 'CURRENT' THEN 1 ELSE 0 END DESC, "
            "p.is_demo_data ASC, p.release_date DESC, p.id DESC"
        )

    where_sql = " AND ".join(clauses)
    sql = f"""
        SELECT p.*, b.name as brand_name, b.slug as brand_slug, b.accent_color as brand_color
        FROM phones p
        JOIN brands b ON b.id = p.brand_id
        WHERE {where_sql}
        ORDER BY {order_sql}
    """
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    items = [dict_from_row(r) for r in rows]
    sf = (sale_filter or "").strip().lower()
    if sf == "on_sale":
        items = [it for it in items if it and it.get("is_sale_active")]
    elif sf == "no_sale":
        items = [it for it in items if it and not it.get("is_sale_active")]
    return items[:limit]


def get_data_quality_metrics() -> Dict[str, int]:
    """
    Calculate real-time Data Quality Dashboard metrics directly from the SQLite database.
    """
    conn = get_db_connection()
    total_phones = conn.execute("SELECT COUNT(*) FROM phones").fetchone()[0]
    verified_count = conn.execute(
        "SELECT COUNT(*) FROM phones WHERE is_demo_data = 0 OR data_status = 'VERIFIED'"
    ).fetchone()[0]
    demo_count = conn.execute(
        "SELECT COUNT(*) FROM phones WHERE is_demo_data = 1 AND data_status != 'VERIFIED'"
    ).fetchone()[0]
    needs_review_count = conn.execute(
        "SELECT COUNT(*) FROM phones WHERE IFNULL(catalog_status, 'CURRENT') = 'NEEDS_REVIEW'"
    ).fetchone()[0]
    latest_current_count = conn.execute(
        "SELECT COUNT(*) FROM phones WHERE is_latest = 1 AND IFNULL(catalog_status, 'CURRENT') = 'CURRENT' AND availability != 'Discontinued'"
    ).fetchone()[0]
    outdated_count = conn.execute(
        "SELECT COUNT(*) FROM phones WHERE IFNULL(catalog_status, 'CURRENT') = 'OUTDATED' OR availability = 'Discontinued'"
    ).fetchone()[0]
    missing_source_count = conn.execute(
        "SELECT COUNT(*) FROM phones WHERE source_url IS NULL OR TRIM(source_url) = '' OR source_name LIKE '%Unverified%'"
    ).fetchone()[0]
    missing_image_count = conn.execute(
        "SELECT COUNT(*) FROM phones WHERE image_url IS NULL OR TRIM(image_url) = ''"
    ).fetchone()[0]
    missing_price_count = conn.execute(
        "SELECT COUNT(*) FROM phones WHERE price_pkr IS NULL OR price_pkr <= 0"
    ).fetchone()[0]
    missing_specs_count = conn.execute(
        """
        SELECT COUNT(*) FROM phones
        WHERE processor IS NULL OR TRIM(processor) = ''
           OR main_camera IS NULL OR TRIM(main_camera) = ''
           OR battery_mah IS NULL OR battery_mah <= 0
           OR display_size_inch IS NULL OR display_size_inch <= 0
        """
    ).fetchone()[0]
    conn.close()
    return {
        "total_phones": total_phones,
        "verified_count": verified_count,
        "demo_count": demo_count,
        "needs_review_count": needs_review_count,
        "latest_current_count": latest_current_count,
        "outdated_count": outdated_count,
        "missing_source_count": missing_source_count,
        "missing_image_count": missing_image_count,
        "missing_price_count": missing_price_count,
        "missing_specs_count": missing_specs_count,
    }
