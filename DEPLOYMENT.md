# PakMobileSpec — Production Deployment & Operations Guide

This document provides complete instructions for configuring, securing, and deploying **PakMobileSpec** (Pakistani Mobile Phone Prices in PKR & Hardware Specification Portal) to local servers or free cloud hosting platforms.

---

## 1. Architecture & Runtime Overview

| Component | Technology / Specification |
| :--- | :--- |
| **Language & Runtime** | Python `3.11+` (`python-3.11.9`) |
| **Web Framework** | **FastAPI** (`>=0.110.0`) + **Jinja2** (`>=3.1.3`) |
| **ASGI Production Server** | **Uvicorn** (`uvicorn app:app --host 0.0.0.0 --port $PORT`) |
| **Application Entry Point** | `app:app` in `app.py` (or `python app.py`) |
| **Database Engine** | **SQLite 3** (`mobile_hub.db` in WAL mode with automatic schema migration) |
| **Health Check Endpoint** | `GET /healthz` (returns `{"status": "ok", "database": "connected", "phones_count": ...}`) |

---

## 2. Installing Dependencies

Create a virtual environment (recommended) and install the dependencies from `requirements.txt`:

```bash
# 1. Create and activate virtual environment (optional)
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 2. Install production dependencies
pip install -r requirements.txt
```

---

## 3. Database Initialization & Data Integrity

The database (`mobile_hub.db`) is initialized and migrated **automatically** when `app.py` starts (`init_db()` and `seed_database_if_empty()`).

* **Non-Destructive Schema Migration:** `init_db()` in `database.py` automatically runs `migrate_db_schema()` on startup, ensuring all columns (`official_variant_name`, `currency`, `data_status`, `source_name`, `source_url`, `verification_notes`, `sale_active`, `sale_price_pkr`, `sale_start_at`, `sale_end_at`, `sale_label`, `catalog_status`, `last_verified_at`) and tables (`phones`, `brands`, `phone_variants`, `price_history`, `data_feedback_reports`, `admin_users`, `media_assets`) exist without deleting any existing records.
* **Catalog & Verification Integrity:** Ships with a 40-phone catalog across 9 major Pakistan smartphone brands (`24` `VERIFIED` current models + `16` `DEMO/SAMPLE` models), model-specific studio SVG illustrations in `static/images/phones/`, full Favicon (`16x16`, `32x32`, `48x48`, `180x180`, `.ico`) support, Phase 1 Sale/Offer management, and a 10-Metric Data Quality Monitor in `/admin`.

---

## 4. Running Locally

### Option A: Direct Python Execution
```bash
python app.py
```

### Option B: Production ASGI Server (Uvicorn)
```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Once running, visit:
* **Public Website:** `http://127.0.0.1:8000`
* **Admin Panel:** `http://127.0.0.1:8000/admin`
* **Health Check:** `http://127.0.0.1:8000/healthz`

---

## 5. Creating or Changing Admin Credentials Securely

Admin passwords are **never stored in plaintext**; they are hashed using `PBKDF2-HMAC-SHA256` (120,000 iterations).

Use the included `manage_admin.py` CLI tool to securely change the administrator password or generate a password hash for production environment variables:

### 1. Interactive Password Rotation (Updates Local SQLite DB)
```bash
python manage_admin.py
```
*(You will be prompted to type and confirm the new password hidden from terminal history).*

### 2. Generate a Password Hash for Cloud Hosting (`PAK_MOBILE_ADMIN_HASH`)
```bash
python manage_admin.py --hash-only --password "YourStrongProductionPassword!"
```
Copy the resulting `PAK_MOBILE_ADMIN_HASH=...` string into your cloud platform's Environment Variables dashboard. When the server starts, `init_db()` automatically syncs the administrator account to match `PAK_MOBILE_ADMIN_USER` and `PAK_MOBILE_ADMIN_HASH` (or `PAK_MOBILE_ADMIN_PASS`).

---

## 6. Environment Variables for Production

Set these environment variables in your hosting provider's dashboard (or in a local `.env` file based on `.env.example`):

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `PAK_MOBILE_SECRET` | **Yes (Prod)** | Ephemeral random hex | 64-character secret key used to sign Admin HMAC session cookies. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `PAK_MOBILE_ADMIN_USER` | Optional | `admin` | Administrator login username |
| `PAK_MOBILE_ADMIN_PASS` | **Recommended** | Empty | Plaintext password automatically hashed (`PBKDF2-HMAC-SHA256`) on startup in cloud environments (`render.yaml`) |
| `PAK_MOBILE_ADMIN_HASH` | Optional | Pre-computed hash | PBKDF2-HMAC-SHA256 password hash generated via `python manage_admin.py --hash-only` |
| `PAK_MOBILE_DB_PATH` | Optional | `./mobile_hub.db` | Path to the SQLite database file (e.g., `/data/mobile_hub.db` when using a persistent volume mount) |
| `PORT` | Automatic | `8000` | HTTP port bound by Uvicorn (automatically injected by Render, Railway, Fly.io, Koyeb) |
| `HOST` | Optional | `0.0.0.0` | Network interface bound by Uvicorn |

---

## 7. Deploying to Free Hosting Platforms

Because **PakMobileSpec** uses lightweight Python (`FastAPI` + `SQLite` + local SVG/static assets) with zero heavy external database servers required, it can be deployed to several free hosting platforms:

### Option 1: Render.com (Free Web Service — `render.yaml` Included)
1. Push this project folder to a private or public GitHub/GitLab repository.
2. Log in to **Render.com** → **New +** → **Web Service** (or **Blueprint** to auto-detect `render.yaml`).
3. Configure settings:
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   * **Health Check Path:** `/healthz`
4. Under **Environment Variables**, add:
   * `PAK_MOBILE_SECRET` = *(click "Generate" or paste a 64-char hex string)*
   * `PAK_MOBILE_ADMIN_USER` = `admin`
   * `PAK_MOBILE_ADMIN_HASH` = *(output from `python manage_admin.py --hash-only`)*
5. Click **Deploy Web Service**.

### Option 2: Fly.io (Supports Free Persistent Volume for SQLite)
If you want Admin Panel edits in SQLite (`mobile_hub.db`) to persist across container restarts, **Fly.io** provides persistent volumes:
```bash
fly launch --no-deploy
fly volumes create pakmobile_data --size 1
fly secrets set PAK_MOBILE_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
fly secrets set PAK_MOBILE_DB_PATH=/data/mobile_hub.db
fly deploy
```

### Option 3: Koyeb / Railway (Free Trial / Hobby Tier)
* Both Koyeb and Railway automatically detect `Procfile` and `requirements.txt`.
* **Build Command:** `pip install -r requirements.txt`
* **Run Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`

### Option 4: Hugging Face Spaces (Free 16GB RAM CPU Container + Persistent `/data` or Repo Storage)
* Create a new Space on Hugging Face using the **Docker** template exposing port `7860`:
  * Start Command: `uvicorn app:app --host 0.0.0.0 --port 7860`

### Option 5: PythonAnywhere (Free Beginner Account — Persistent Disk Included)
* Upload the project folder to `/home/<yourusername>/pakmobilespec` — PythonAnywhere's filesystem is **100% persistent** on the free tier, meaning all SQLite (`mobile_hub.db`) price updates and uploaded images are saved permanently on disk.
