import os
import re
import csv
import io
import json
import sqlite3
import hmac
import hashlib
import base64
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import (
    BASE_DIR,
    SECRET_KEY,
    DEMO_WARNING_TEXT,
    get_db_path,
    get_uploads_dir,
    get_db_connection,
    init_db,
    format_pkr,
    format_date_human,
    verify_password,
    verify_admin_credentials,
    save_media_asset_to_db,
    get_all_brands,
    get_brand_by_slug,
    get_phone_by_slug,
    get_phone_by_id,
    query_phones,
    get_data_quality_metrics,
    is_sale_active,
    get_display_price,
    get_discount_percent,
    get_sale_status,
    validate_sale_inputs,
)
from seed_data import seed_database_if_empty, generate_phone_svg

app = FastAPI(
    title="PakMobileSpec — Mobile Phone Prices (PKR) & Specifications",
    description="Professional Mobile Phone Information, Specifications, Comparison & PKR Price Portal",
    version="2.0.0",
)

os.makedirs(os.path.join(BASE_DIR, "static", "css"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static", "js"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "static", "images", "phones"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "templates", "admin"), exist_ok=True)

# Initialize schema, run non-destructive migrations, and seed if empty
init_db()
seed_database_if_empty()

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["format_pkr"] = format_pkr
templates.env.globals["format_date_human"] = format_date_human
templates.env.globals["current_year"] = datetime.now().year
templates.env.globals["DEMO_WARNING_TEXT"] = DEMO_WARNING_TEXT
templates.env.globals["is_sale_active"] = is_sale_active
templates.env.globals["get_display_price"] = get_display_price
templates.env.globals["get_discount_percent"] = get_discount_percent
templates.env.globals["get_sale_status"] = get_sale_status


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


# ==========================================
# ADMIN SESSION AUTHENTICATION (HMAC SIGNED)
# ==========================================
ADMIN_COOKIE_NAME = "pakmobile_admin_session"


def create_session_token(username: str) -> str:
    payload = f"{username}|{int(datetime.now().timestamp())}"
    sig = hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}|{sig}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def verify_session_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        parts = decoded.split("|")
        if len(parts) != 3:
            return None
        username, ts_str, sig = parts
        expected = hmac.new(
            SECRET_KEY.encode("utf-8"), f"{username}|{ts_str}".encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        if int(datetime.now().timestamp()) - int(ts_str) > 7 * 86400:
            return None
        return username
    except Exception:
        return None


def get_current_admin(request: Request) -> Optional[str]:
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    return verify_session_token(token)


# ==========================================
# PUBLIC WEBSITE ROUTES (SEO-FRIENDLY)
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    brands = get_all_brands()
    latest_phones = query_phones(only_latest=True, sort_by="latest", limit=10)
    popular_phones = query_phones(only_popular=True, sort_by="popular", limit=10)
    budget_phones = query_phones(max_price=65000, sort_by="price_asc", limit=5)
    flagship_phones = query_phones(min_price=200000, sort_by="price_desc", limit=5)

    dq = get_data_quality_metrics()
    conn = get_db_connection()
    latest_update_row = conn.execute("SELECT MAX(updated_at) FROM phones").fetchone()
    latest_site_update = (
        latest_update_row[0]
        if latest_update_row and latest_update_row[0]
        else datetime.now().strftime("%Y-%m-%d")
    )
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "brands": brands,
            "latest_phones": latest_phones,
            "popular_phones": popular_phones,
            "budget_phones": budget_phones,
            "flagship_phones": flagship_phones,
            "total_phones": dq["total_phones"],
            "verified_count": dq["verified_count"],
            "demo_count": dq["demo_count"],
            "latest_site_update": latest_site_update,
            "page_title": "PakMobileSpec — Mobile Phone Prices in Pakistan (PKR) & Complete Specifications",
            "meta_description": "Explore mobile phone prices in Pakistani Rupees (PKR), complete hardware specifications, side-by-side comparisons, and brand catalogs for Apple, Samsung, Xiaomi, Vivo, Oppo, OnePlus, Realme, Infinix and Tecno.",
        },
    )


@app.get("/brands", response_class=HTMLResponse)
async def all_brands_page(request: Request):
    brands = get_all_brands()
    return templates.TemplateResponse(
        request=request,
        name="brands.html",
        context={
            "brands": brands,
            "selected_brand": None,
            "phones": [],
            "page_title": "All Mobile Brands in Pakistan — Apple, Samsung, Xiaomi, Vivo, Oppo, OnePlus, Realme, Infinix & Tecno",
            "meta_description": "Browse all major smartphone brands in Pakistan with PKR price ranges, total models, and full technical specifications.",
        },
    )


@app.get("/brand/{slug}", response_class=HTMLResponse)
async def brand_detail_page(
    request: Request,
    slug: str,
    sort: str = "latest",
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    ram: Optional[int] = None,
    only_5g: Optional[int] = None,
):
    brand = get_brand_by_slug(slug)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    brands = get_all_brands()
    phones = query_phones(
        brand_slugs=[slug],
        min_price=min_price,
        max_price=max_price,
        ram_list=[ram] if ram else None,
        only_5g=bool(only_5g),
        sort_by=sort,
        limit=100,
    )

    return templates.TemplateResponse(
        request=request,
        name="brands.html",
        context={
            "brands": brands,
            "selected_brand": brand,
            "phones": phones,
            "sort": sort,
            "min_price": min_price,
            "max_price": max_price,
            "selected_ram": ram,
            "only_5g": bool(only_5g),
            "page_title": f"{brand['name']} Mobile Phones & Prices in Pakistan (PKR) — PakMobileSpec",
            "meta_description": f"Compare {brand['name']} mobile phone prices in Pakistani Rupees (PKR), RAM, storage, cameras, battery specs, and release dates.",
        },
    )


@app.get("/phones", response_class=HTMLResponse)
async def phone_listing_page(
    request: Request,
    q: str = "",
    brand: Optional[List[str]] = Query(None),
    price_range: str = "",
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    ram: Optional[List[int]] = Query(None),
    storage: Optional[List[int]] = Query(None),
    min_battery: Optional[int] = None,
    only_5g: Optional[int] = None,
    only_latest: Optional[int] = None,
    only_verified: Optional[int] = None,
    pta_status: str = "",
    data_status: str = "",
    catalog: str = "",
    sale: str = "",
    sort: str = "latest",
):
    brands = get_all_brands()
    clean_brands = [b for b in (brand or []) if b and b.strip()]
    clean_rams = [r for r in (ram or []) if r]
    clean_storages = [s for s in (storage or []) if s]

    eff_min_price = min_price
    eff_max_price = max_price
    if price_range and "-" in price_range:
        parts = price_range.split("-", 1)
        try:
            eff_min_price = int(parts[0])
            eff_max_price = int(parts[1])
        except ValueError:
            pass

    eff_only_verified = bool(only_verified) or (data_status.upper() == "VERIFIED")
    eff_only_latest = bool(only_latest) or (catalog.lower() == "latest")

    phones = query_phones(
        q=q,
        brand_slugs=clean_brands if clean_brands else None,
        min_price=eff_min_price,
        max_price=eff_max_price,
        ram_list=clean_rams if clean_rams else None,
        storage_list=clean_storages if clean_storages else None,
        min_battery=min_battery,
        only_5g=bool(only_5g),
        only_latest=eff_only_latest,
        only_verified=eff_only_verified,
        data_status_filter=data_status if data_status else (catalog if catalog and catalog.lower() != "latest" else None),
        sale_filter=sale if sale else None,
        sort_by=sort,
        limit=120,
    )

    if data_status.upper() == "DEMO":
        phones = [p for p in phones if p.get("is_demo_data")]
    if pta_status:
        phones = [p for p in phones if pta_status.lower() in (p.get("pta_status") or "").lower()]

    return templates.TemplateResponse(
        request=request,
        name="phones.html",
        context={
            "brands": brands,
            "phones": phones,
            "q": q,
            "selected_brands": clean_brands,
            "price_range": price_range,
            "min_price": eff_min_price or "",
            "max_price": eff_max_price or "",
            "selected_rams": clean_rams,
            "selected_storages": clean_storages,
            "min_battery": min_battery or "",
            "only_5g": bool(only_5g),
            "only_latest": eff_only_latest,
            "only_verified": eff_only_verified,
            "pta_status": pta_status,
            "data_status": data_status or ("VERIFIED" if only_verified else ""),
            "catalog_filter": catalog or ("latest" if only_latest else ""),
            "sale": sale,
            "sale_filter": sale,
            "sort": sort,
            "page_title": "Mobile Phone Finder & PKR Price Filter — Search & Filter Smartphones",
            "meta_description": "Filter mobile phones in Pakistan by PKR price budget, brand, chipset, RAM, internal storage, battery mAh, sale status, and 5G connectivity.",
        },
    )


@app.get("/phone/{slug}", response_class=HTMLResponse)
async def phone_detail_page(request: Request, slug: str, reported: Optional[int] = None):
    phone = get_phone_by_slug(slug, increment_view=True)
    if not phone:
        raise HTTPException(status_code=404, detail="Phone not found")

    brands = get_all_brands()
    price_low = int(phone["price_pkr"] * 0.65)
    price_high = int(phone["price_pkr"] * 1.35)
    similar_candidates = query_phones(min_price=price_low, max_price=price_high, limit=8)
    similar_phones = [p for p in similar_candidates if p["id"] != phone["id"]][:5]
    if len(similar_phones) < 5:
        brand_mates = [
            p
            for p in query_phones(brand_slugs=[phone["brand_slug"]], limit=6)
            if p["id"] != phone["id"] and p["id"] not in [s["id"] for s in similar_phones]
        ]
        similar_phones.extend(brand_mates[: 5 - len(similar_phones)])

    return templates.TemplateResponse(
        request=request,
        name="phone_detail.html",
        context={
            "brands": brands,
            "phone": phone,
            "similar_phones": similar_phones,
            "reported": bool(reported),
            "page_title": f"{phone['brand_name']} {phone['model_name']} Price in Pakistan (PKR) & Full Specifications",
            "meta_description": f"{phone['brand_name']} {phone['model_name']} ({phone['official_variant_name']}) price in Pakistan is {format_pkr(phone['display_price_pkr'])} ({phone['data_status']}). Full specs: {phone['ram_display']} RAM, {phone['storage_display']} storage, {phone['processor']}. Last Updated: {format_date_human(phone['updated_at'])}.",
        },
    )


def _store_phone_feedback_report(
    phone_id: int,
    issue_type: str,
    suggested_value: str,
    source_reference: str = "",
    reporter_note: str = "",
) -> None:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO data_feedback_reports (phone_id, issue_type, suggested_value, source_reference, reporter_note, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'Open', ?)
        """,
        (
            phone_id,
            (issue_type or "Price / Specification Update").strip()[:160],
            (suggested_value or "").strip()[:500],
            (source_reference or "").strip()[:400],
            (reporter_note or "").strip()[:800],
            now_str,
        ),
    )
    conn.commit()
    conn.close()


@app.post("/phone/{slug}/report")
async def submit_phone_detail_report(
    request: Request,
    slug: str,
    reporter_name: str = Form(""),
    message: str = Form(""),
    issue_type: str = Form("Price / Specification Update"),
    suggested_value: str = Form(""),
    source_reference: str = Form(""),
    reporter_note: str = Form(""),
):
    phone = get_phone_by_slug(slug)
    if not phone:
        return JSONResponse({"success": False, "error": "Phone not found"}, status_code=404)

    eff_value = (message or suggested_value or "").strip()
    if not eff_value:
        return JSONResponse(
            {"success": False, "error": "Please provide details for the price or specification correction."},
            status_code=400,
        )

    combined_note = reporter_note.strip()
    if reporter_name and reporter_name.strip():
        combined_note = f"Reported by {reporter_name.strip()}" + (f" — {combined_note}" if combined_note else "")

    try:
        _store_phone_feedback_report(
            phone_id=phone["id"],
            issue_type=issue_type,
            suggested_value=eff_value,
            source_reference=source_reference,
            reporter_note=combined_note,
        )
    except Exception:
        return JSONResponse({"success": False, "error": "Unable to record feedback report at this time."}, status_code=500)

    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept and "text/html" not in accept:
        return JSONResponse(
            {
                "success": True,
                "message": "Thank you! Your data report has been logged for Administrator verification.",
            }
        )
    return RedirectResponse(url=f"/phone/{slug}?reported=1#reportFeedbackBox", status_code=303)


@app.get("/compare", response_class=HTMLResponse)
async def compare_page(
    request: Request,
    phones: Optional[str] = Query(None, description="Comma-separated phone slugs"),
):
    brands = get_all_brands()
    all_phones_list = query_phones(sort_by="popular", limit=100)

    selected_slugs = []
    if phones:
        selected_slugs = [s.strip() for s in phones.split(",") if s.strip()][:4]
    else:
        selected_slugs = [
            "apple-iphone-16-pro-max",
            "samsung-galaxy-s24-ultra",
        ]

    compared_phones = []
    for s in selected_slugs:
        p = get_phone_by_slug(s)
        if p:
            compared_phones.append(p)

    return templates.TemplateResponse(
        request=request,
        name="compare.html",
        context={
            "brands": brands,
            "compared_phones": compared_phones,
            "all_phones_list": all_phones_list,
            "page_title": "Compare Mobile Phones Side-by-Side — Specs & PKR Prices | PakMobileSpec",
            "meta_description": "Compare up to 4 smartphones side-by-side in Pakistan. Compare PKR prices, display, processor, RAM, storage, cameras, battery, charging, 5G, PTA status, and data verification status.",
        },
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    ico_path = os.path.join(BASE_DIR, "static", "images", "favicon.ico")
    if os.path.exists(ico_path):
        with open(ico_path, "rb") as f:
            return Response(content=f.read(), media_type="image/x-icon")
    return Response(status_code=404)


@app.get("/robots.txt", response_class=Response)
async def robots_txt(request: Request):
    base_url = str(request.base_url).rstrip("/")
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/\n"
        "\n"
        "Sitemap: /sitemap.xml\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return Response(content=content, media_type="text/plain")


@app.get("/sitemap.xml", response_class=Response)
async def sitemap_xml(request: Request):
    base_url = str(request.base_url).rstrip("/")
    brands = get_all_brands()
    phones = query_phones(limit=500)
    urls = [
        f"<url><loc>{base_url}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>",
        f"<url><loc>{base_url}/brands</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>",
        f"<url><loc>{base_url}/phones</loc><changefreq>daily</changefreq><priority>0.9</priority></url>",
        f"<url><loc>{base_url}/compare</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>",
    ]
    for b in brands:
        urls.append(
            f"<url><loc>{base_url}/brand/{b['slug']}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )
    for p in phones:
        lastmod = p["updated_at"][:10] if p.get("updated_at") else datetime.now().strftime("%Y-%m-%d")
        urls.append(
            f"<url><loc>{base_url}/phone/{p['slug']}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


# ==========================================
# PUBLIC JSON API ENDPOINTS
# ==========================================
@app.get("/api/search")
async def api_live_search(q: str = ""):
    if not q or len(q.strip()) < 1:
        results = query_phones(only_popular=True, limit=8)
    else:
        results = query_phones(q=q, limit=25)

    formatted = []
    for p in results:
        formatted.append(
            {
                "id": p["id"],
                "brand_name": p["brand_name"],
                "model_name": p["model_name"],
                "official_variant_name": p["official_variant_name"],
                "full_name": f"{p['brand_name']} {p['model_name']}",
                "slug": p["slug"],
                "price_pkr": p["price_pkr"],
                "sale_active": p["sale_active"],
                "sale_price_pkr": p["sale_price_pkr"],
                "sale_label": p["sale_label"],
                "sale_start_at": p["sale_start_at"],
                "sale_end_at": p["sale_end_at"],
                "is_sale_active": p["is_sale_active"],
                "display_price_pkr": p["display_price_pkr"],
                "discount_percent": p["discount_percent"],
                "currency": p["currency"],
                "price_formatted": format_pkr(p["display_price_pkr"]),
                "regular_price_formatted": format_pkr(p["price_pkr"]),
                "ram_display": p["ram_display"],
                "storage_display": p["storage_display"],
                "processor": p["processor"].split("—")[0].strip(),
                "image_url": p["image_url"],
                "data_status": p["data_status"],
                "is_demo_data": bool(p["is_demo_data"]),
                "is_5g": bool(p["is_5g"]),
            }
        )
    return {"results": formatted}


@app.get("/api/phones")
async def api_filter_phones(
    q: str = "",
    brands: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    rams: Optional[str] = None,
    storages: Optional[str] = None,
    min_battery: Optional[int] = None,
    only_5g: bool = False,
    only_verified: bool = False,
    sale: str = "",
    sort: str = "latest",
):
    brand_list = [b for b in brands.split(",") if b] if brands else None
    ram_list = [int(r) for r in rams.split(",") if r.isdigit()] if rams else None
    storage_list = [int(s) for s in storages.split(",") if s.isdigit()] if storages else None

    results = query_phones(
        q=q,
        brand_slugs=brand_list,
        min_price=min_price,
        max_price=max_price,
        ram_list=ram_list,
        storage_list=storage_list,
        min_battery=min_battery,
        only_5g=only_5g,
        only_verified=only_verified,
        sale_filter=sale if sale else None,
        sort_by=sort,
        limit=100,
    )
    for p in results:
        p["price_formatted"] = format_pkr(p["display_price_pkr"])
        p["regular_price_formatted"] = format_pkr(p["price_pkr"])
        p["updated_human"] = format_date_human(p["updated_at"])
    return {"count": len(results), "phones": results}


@app.post("/api/phone/{phone_id}/feedback")
async def api_submit_data_feedback(
    phone_id: int,
    issue_type: str = Form("Price / Specification Update"),
    suggested_value: str = Form(""),
    source_reference: str = Form(""),
    reporter_note: str = Form(""),
):
    phone = get_phone_by_id(phone_id)
    if not phone:
        return JSONResponse({"error": "Phone not found"}, status_code=404)

    _store_phone_feedback_report(
        phone_id=phone_id,
        issue_type=issue_type,
        suggested_value=suggested_value,
        source_reference=source_reference,
        reporter_note=reporter_note,
    )
    return JSONResponse(
        {
            "success": True,
            "message": "Thank you! Your data report has been logged for Administrator verification.",
        }
    )


# ==========================================
# SECURE ADMIN PANEL ROUTES
# ==========================================
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request, error: Optional[str] = None):
    admin_user = get_current_admin(request)
    if admin_user:
        return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={
            "error": error,
            "page_title": "Admin Portal Sign In — PakMobileSpec",
        },
    )


@app.post("/admin/login")
async def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    authenticated_user = verify_admin_credentials(username, password)
    if not authenticated_user:
        return templates.TemplateResponse(
            request=request,
            name="admin/login.html",
            context={
                "error": "Invalid administrator username or password.",
                "page_title": "Admin Portal Sign In — PakMobileSpec",
            },
            status_code=401,
        )

    token = create_session_token(authenticated_user)
    response = RedirectResponse(url="/admin", status_code=302)
    cookie_secure = os.environ.get("PAK_MOBILE_COOKIE_SECURE", "0") == "1"
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
        max_age=7 * 86400,
    )
    return response


@app.get("/admin/logout")
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(ADMIN_COOKIE_NAME)
    return response


@app.get("/admin/export.csv")
async def admin_export_csv(request: Request):
    admin_user = get_current_admin(request)
    if not admin_user:
        return PlainTextResponse("Unauthorized: Admin authentication required.", status_code=401)

    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT p.*, b.name as brand_name
        FROM phones p
        JOIN brands b ON b.id = p.brand_id
        ORDER BY p.id ASC
        """
    ).fetchall()
    conn.close()

    csv_columns = [
        "id",
        "brand",
        "model_name",
        "official_variant_name",
        "slug",
        "price_pkr",
        "currency",
        "data_status",
        "is_demo_data",
        "source_name",
        "source_url",
        "release_date",
        "ram_display",
        "storage_display",
        "processor",
        "display_size_inch",
        "refresh_rate",
        "main_camera",
        "selfie_camera",
        "battery_mah",
        "charging",
        "is_5g",
        "pta_status",
        "availability",
        "image_url",
        "created_at",
        "updated_at",
        "sale_active",
        "sale_price_pkr",
        "sale_label",
        "sale_start_at",
        "sale_end_at",
        "catalog_status",
        "last_verified_at",
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(csv_columns)

    for r in rows:
        d = dict(r)
        writer.writerow(
            [
                d.get("id"),
                d.get("brand_name"),
                d.get("model_name"),
                d.get("official_variant_name"),
                d.get("slug"),
                d.get("price_pkr"),
                d.get("currency"),
                d.get("data_status"),
                d.get("is_demo_data"),
                d.get("source_name"),
                d.get("source_url"),
                d.get("release_date"),
                d.get("ram_display"),
                d.get("storage_display"),
                d.get("processor"),
                d.get("display_size_inch"),
                d.get("refresh_rate"),
                d.get("main_camera"),
                d.get("selfie_camera"),
                d.get("battery_mah"),
                d.get("charging"),
                d.get("is_5g"),
                d.get("pta_status"),
                d.get("availability"),
                d.get("image_url"),
                d.get("created_at"),
                d.get("updated_at"),
                d.get("sale_active", 0),
                d.get("sale_price_pkr", ""),
                d.get("sale_label", ""),
                d.get("sale_start_at", ""),
                d.get("sale_end_at", ""),
                d.get("catalog_status", "CURRENT"),
                d.get("last_verified_at", ""),
            ]
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="pakmobilespec-phones.csv"'
        },
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    q: str = "",
    brand: str = "",
    status: str = "",
    sale: str = "",
):
    admin_user = get_current_admin(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    brands = get_all_brands()
    phones = query_phones(
        q=q,
        brand_slugs=[brand] if brand else None,
        data_status_filter=status if status else None,
        sale_filter=sale if sale else None,
        sort_by="latest",
        limit=200,
    )

    all_phones_for_kpi = query_phones(limit=500)
    active_sales_count = sum(1 for p in all_phones_for_kpi if p.get("is_sale_active"))
    dq_metrics = get_data_quality_metrics()

    conn = get_db_connection()
    total_phones = dq_metrics["total_phones"]
    demo_count = dq_metrics["demo_count"]
    verified_count = dq_metrics["verified_count"]
    recent_history = conn.execute(
        """
        SELECT h.*, p.model_name, p.slug, b.name as brand_name
        FROM price_history h
        JOIN phones p ON p.id = h.phone_id
        JOIN brands b ON b.id = p.brand_id
        ORDER BY h.id DESC LIMIT 10
        """
    ).fetchall()
    feedback_reports = conn.execute(
        """
        SELECT f.*, p.model_name, p.slug, b.name as brand_name
        FROM data_feedback_reports f
        JOIN phones p ON p.id = f.phone_id
        JOIN brands b ON b.id = p.brand_id
        ORDER BY f.id DESC LIMIT 10
        """
    ).fetchall()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context={
            "admin_user": admin_user,
            "brands": brands,
            "phones": phones,
            "total_phones": total_phones,
            "demo_count": demo_count,
            "verified_count": verified_count,
            "active_sales_count": active_sales_count,
            "dq_metrics": dq_metrics,
            "recent_history": [dict(r) for r in recent_history],
            "feedback_reports": [dict(f) for f in feedback_reports],
            "q": q,
            "selected_brand": brand,
            "selected_status": status,
            "selected_sale": sale,
            "page_title": "Admin Management Portal — PakMobileSpec",
        },
    )


@app.get("/admin/phone/new", response_class=HTMLResponse)
async def admin_new_phone_page(request: Request):
    admin_user = get_current_admin(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    brands = get_all_brands()
    return templates.TemplateResponse(
        request=request,
        name="admin/phone_form.html",
        context={
            "admin_user": admin_user,
            "brands": brands,
            "phone": None,
            "page_title": "Add New Mobile Phone — Admin Panel",
        },
    )


@app.get("/admin/phone/{phone_id}/edit", response_class=HTMLResponse)
async def admin_edit_phone_page(request: Request, phone_id: int):
    admin_user = get_current_admin(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    phone = get_phone_by_id(phone_id)
    if not phone:
        raise HTTPException(status_code=404, detail="Phone not found")

    brands = get_all_brands()
    return templates.TemplateResponse(
        request=request,
        name="admin/phone_form.html",
        context={
            "admin_user": admin_user,
            "brands": brands,
            "phone": phone,
            "page_title": f"Edit {phone['brand_name']} {phone['model_name']} — Admin Panel",
        },
    )


@app.post("/admin/api/phone/save")
async def admin_save_phone(
    request: Request,
    phone_id: Optional[int] = Form(None),
    brand_id: int = Form(...),
    model_name: str = Form(...),
    official_variant_name: str = Form(""),
    slug: str = Form(""),
    price_pkr: int = Form(...),
    currency: str = Form("PKR"),
    pta_status: str = Form("PTA Approved / Official Warranty"),
    availability: str = Form("Available"),
    data_status: Optional[str] = Form(None),
    is_demo_data: Optional[int] = Form(None),
    source_name: str = Form(""),
    source_url: str = Form(""),
    verification_notes: str = Form(""),
    data_source_note: str = Form(""),
    image_url: str = Form(""),
    release_date: str = Form(""),
    ram_gb: int = Form(8),
    ram_display: str = Form("8 GB"),
    storage_gb: int = Form(128),
    storage_display: str = Form("128 GB"),
    processor: str = Form(""),
    display_type: str = Form(""),
    display_size_inch: float = Form(6.7),
    display_resolution: str = Form(""),
    refresh_rate: str = Form("120Hz"),
    main_camera: str = Form(""),
    selfie_camera: str = Form(""),
    battery_mah: int = Form(5000),
    charging: str = Form(""),
    network: str = Form("2G / 3G / 4G LTE / 5G"),
    is_5g: int = Form(0),
    os_name: str = Form(""),
    dimensions: str = Form(""),
    weight: str = Form(""),
    build_material: str = Form(""),
    sim_type: str = Form("Dual SIM (Nano-SIM, dual stand-by)"),
    colors: str = Form(""),
    sensors: str = Form("Fingerprint, Accelerometer, Gyro, Proximity, Compass"),
    summary_text: str = Form(""),
    is_latest: int = Form(0),
    is_popular: int = Form(0),
    catalog_status: str = Form("CURRENT"),
    variants_json: str = Form("[]"),
    sale_active: int = Form(0),
    sale_price_pkr: Optional[str] = Form(None),
    sale_start_at: Optional[str] = Form(None),
    sale_end_at: Optional[str] = Form(None),
    sale_label: Optional[str] = Form(None),
    clear_sale: int = Form(0),
):
    admin_user = get_current_admin(request)
    if not admin_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    if int(clear_sale) == 1:
        clean_sale_active = 0
        clean_sale_price = None
        clean_sale_start = None
        clean_sale_end = None
        clean_sale_label = None
    else:
        is_valid_sale, sale_err, sale_cleaned = validate_sale_inputs(
            regular_price_pkr=price_pkr,
            sale_active=sale_active,
            sale_price_pkr=sale_price_pkr,
            sale_start_at=sale_start_at,
            sale_end_at=sale_end_at,
            sale_label=sale_label,
        )
        if not is_valid_sale:
            return JSONResponse({"error": sale_err}, status_code=400)
        clean_sale_active = sale_cleaned["sale_active"]
        clean_sale_price = sale_cleaned["sale_price_pkr"]
        clean_sale_start = sale_cleaned["sale_start_at"]
        clean_sale_end = sale_cleaned["sale_end_at"]
        clean_sale_label = sale_cleaned["sale_label"]

    conn = get_db_connection()
    cursor = conn.cursor()
    brand_row = cursor.execute("SELECT * FROM brands WHERE id = ?", (brand_id,)).fetchone()
    if not brand_row:
        conn.close()
        return JSONResponse({"error": "Invalid brand selected"}, status_code=400)

    # Verification Safety: Determine explicit DEMO/SAMPLE vs VERIFIED status
    if data_status is not None:
        clean_status = "VERIFIED" if data_status.strip().upper() == "VERIFIED" else "DEMO/SAMPLE"
        clean_is_demo = 0 if clean_status == "VERIFIED" else 1
    elif is_demo_data is not None:
        clean_is_demo = 0 if int(is_demo_data) == 0 else 1
        clean_status = "VERIFIED" if clean_is_demo == 0 else "DEMO/SAMPLE"
    else:
        clean_is_demo = 1
        clean_status = "DEMO/SAMPLE"

    valid_catalog_statuses = ("CURRENT", "OLDER_AVAILABLE", "OUTDATED", "NEEDS_REVIEW")
    clean_catalog_status = catalog_status.strip().upper() if catalog_status else "CURRENT"
    if clean_catalog_status not in valid_catalog_statuses:
        clean_catalog_status = "CURRENT"

    clean_variant_name = (
        official_variant_name.strip()
        if official_variant_name and official_variant_name.strip()
        else f"{model_name.strip()} ({ram_gb}GB RAM / {storage_gb}GB Storage)"
    )
    clean_currency = currency.strip().upper() if currency and currency.strip() else "PKR"

    if clean_is_demo == 1:
        clean_source_name = source_name.strip() or "Demo / Sample Seed Catalog (Unverified)"
        clean_source_url = source_url.strip()
        clean_verif_notes = verification_notes.strip() or DEMO_WARNING_TEXT
    else:
        clean_source_name = source_name.strip() or "Official Brand / Retailer Verified"
        clean_source_url = source_url.strip()
        clean_verif_notes = (
            verification_notes.strip()
            or data_source_note.strip()
            or f"Verified by {admin_user} via Admin Panel"
        )

    clean_slug = slug.strip() if slug and slug.strip() else slugify(f"{brand_row['name']}-{model_name}")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_last_verified_at = now_str if clean_is_demo == 0 else None

    if not image_url.strip() or image_url.endswith(".svg"):
        image_url = generate_phone_svg(
            slug=clean_slug,
            brand_name=brand_row["name"],
            model_name=model_name,
            accent_hex=brand_row["accent_color"],
            secondary_hex="#1e293b",
            is_demo=bool(clean_is_demo),
        )

    if not summary_text.strip():
        summary_text = (
            f"{brand_row['name']} {model_name} ({clean_variant_name}) features a {display_size_inch}-inch {display_type} screen, "
            f"{processor} chipset, {ram_display} RAM, {storage_display} internal storage, and a {battery_mah} mAh battery."
        )

    if phone_id:
        old_row = cursor.execute("SELECT price_pkr FROM phones WHERE id = ?", (phone_id,)).fetchone()
        old_price = old_row["price_pkr"] if old_row else price_pkr

        cursor.execute(
            """
            UPDATE phones SET
                brand_id = ?, model_name = ?, official_variant_name = ?, slug = ?,
                price_pkr = ?, currency = ?, pta_status = ?, availability = ?,
                is_demo_data = ?, data_status = ?, source_name = ?, source_url = ?,
                verification_notes = ?, data_source_note = ?, image_url = ?,
                release_date = ?, ram_gb = ?, ram_display = ?, storage_gb = ?, storage_display = ?,
                processor = ?, display_type = ?, display_size_inch = ?, display_resolution = ?,
                refresh_rate = ?, main_camera = ?, selfie_camera = ?, battery_mah = ?,
                charging = ?, network = ?, is_5g = ?, os = ?, dimensions = ?, weight = ?,
                build_material = ?, sim_type = ?, colors = ?, sensors = ?, summary_text = ?,
                is_latest = ?, is_popular = ?,
                sale_active = ?, sale_price_pkr = ?, sale_start_at = ?, sale_end_at = ?, sale_label = ?,
                catalog_status = ?, last_verified_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                brand_id, model_name, clean_variant_name, clean_slug,
                price_pkr, clean_currency, pta_status, availability,
                clean_is_demo, clean_status, clean_source_name, clean_source_url,
                clean_verif_notes, clean_verif_notes, image_url,
                release_date, ram_gb, ram_display, storage_gb, storage_display,
                processor, display_type, display_size_inch, display_resolution,
                refresh_rate, main_camera, selfie_camera, battery_mah,
                charging, network, is_5g, os_name, dimensions, weight,
                build_material, sim_type, colors, sensors, summary_text,
                is_latest, is_popular,
                clean_sale_active, clean_sale_price, clean_sale_start, clean_sale_end, clean_sale_label,
                clean_catalog_status, clean_last_verified_at, now_str, phone_id,
            ),
        )

        # IMPORTANT: Only log regular price changes in price_history, never sale changes
        if old_price != price_pkr:
            cursor.execute(
                """
                INSERT INTO price_history (phone_id, old_price_pkr, new_price_pkr, note, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (phone_id, old_price, price_pkr, f"Updated by {admin_user} ({clean_status})", now_str),
            )
        target_id = phone_id
    else:
        existing_slug = cursor.execute("SELECT id FROM phones WHERE slug = ?", (clean_slug,)).fetchone()
        if existing_slug:
            clean_slug = f"{clean_slug}-{int(datetime.now().timestamp()) % 10000}"

        cursor.execute(
            """
            INSERT INTO phones (
                brand_id, model_name, official_variant_name, slug,
                price_pkr, currency, pta_status, availability,
                is_demo_data, data_status, source_name, source_url,
                verification_notes, data_source_note, image_url, gallery_json, release_date,
                ram_gb, ram_display, storage_gb, storage_display, processor,
                display_type, display_size_inch, display_resolution, refresh_rate,
                main_camera, selfie_camera, battery_mah, charging, network, is_5g,
                os, dimensions, weight, build_material, sim_type, colors, sensors,
                summary_text, is_latest, is_popular,
                sale_active, sale_price_pkr, sale_start_at, sale_end_at, sale_label,
                catalog_status, last_verified_at, views_count, created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, 1, ?, ?
            )
            """,
            (
                brand_id, model_name, clean_variant_name, clean_slug,
                price_pkr, clean_currency, pta_status, availability,
                clean_is_demo, clean_status, clean_source_name, clean_source_url,
                clean_verif_notes, clean_verif_notes, image_url, json.dumps([image_url]), release_date,
                ram_gb, ram_display, storage_gb, storage_display, processor,
                display_type, display_size_inch, display_resolution, refresh_rate,
                main_camera, selfie_camera, battery_mah, charging, network, is_5g,
                os_name, dimensions, weight, build_material, sim_type, colors, sensors,
                summary_text, is_latest, is_popular,
                clean_sale_active, clean_sale_price, clean_sale_start, clean_sale_end, clean_sale_label,
                clean_catalog_status, clean_last_verified_at, now_str, now_str,
            ),
        )
        target_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO price_history (phone_id, old_price_pkr, new_price_pkr, note, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (target_id, price_pkr, price_pkr, f"Created by {admin_user} ({clean_status})", now_str),
        )

    try:
        variants_data = json.loads(variants_json)
        if isinstance(variants_data, list):
            cursor.execute("DELETE FROM phone_variants WHERE phone_id = ?", (target_id,))
            for v in variants_data:
                if v.get("variant_label") and v.get("price_pkr"):
                    cursor.execute(
                        """
                        INSERT INTO phone_variants (phone_id, variant_label, ram_gb, storage_gb, price_pkr)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            target_id,
                            v["variant_label"],
                            int(v.get("ram_gb", ram_gb)),
                            int(v.get("storage_gb", storage_gb)),
                            int(v["price_pkr"]),
                        ),
                    )
    except Exception:
        pass

    conn.commit()
    conn.close()
    return JSONResponse(
        {
            "success": True,
            "phone_id": target_id,
            "slug": clean_slug,
            "data_status": clean_status,
            "is_demo_data": clean_is_demo,
            "catalog_status": clean_catalog_status,
            "last_verified_at": clean_last_verified_at,
            "sale_active": clean_sale_active,
            "sale_price_pkr": clean_sale_price,
        }
    )


@app.post("/admin/api/phone/{phone_id}/sale")
async def admin_update_phone_sale(
    request: Request,
    phone_id: int,
    sale_active: int = Form(0),
    sale_price_pkr: Optional[str] = Form(None),
    sale_start_at: Optional[str] = Form(None),
    sale_end_at: Optional[str] = Form(None),
    sale_label: Optional[str] = Form(None),
    clear_sale: int = Form(0),
):
    """
    Admin endpoint for quick sale management (enable/disable/update/clear sale).
    Does NOT alter price_pkr, data_status, or price_history.
    """
    admin_user = get_current_admin(request)
    if not admin_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    phone = get_phone_by_id(phone_id)
    if not phone:
        return JSONResponse({"error": "Phone not found"}, status_code=404)

    regular_price = int(phone["price_pkr"])

    if int(clear_sale) == 1:
        clean_sale_active = 0
        clean_sale_price = None
        clean_sale_start = None
        clean_sale_end = None
        clean_sale_label = None
    else:
        # If quick-enabling without passing sale_price_pkr, fall back to existing sale_price_pkr
        effective_sale_price = (
            sale_price_pkr
            if (sale_price_pkr is not None and str(sale_price_pkr).strip() != "")
            else phone.get("sale_price_pkr")
        )
        effective_start = sale_start_at if sale_start_at is not None else phone.get("sale_start_at")
        effective_end = sale_end_at if sale_end_at is not None else phone.get("sale_end_at")
        effective_label = sale_label if sale_label is not None else phone.get("sale_label")

        is_valid_sale, sale_err, sale_cleaned = validate_sale_inputs(
            regular_price_pkr=regular_price,
            sale_active=sale_active,
            sale_price_pkr=effective_sale_price,
            sale_start_at=effective_start,
            sale_end_at=effective_end,
            sale_label=effective_label,
        )
        if not is_valid_sale:
            return JSONResponse({"error": sale_err}, status_code=400)

        clean_sale_active = sale_cleaned["sale_active"]
        clean_sale_price = sale_cleaned["sale_price_pkr"]
        clean_sale_start = sale_cleaned["sale_start_at"]
        clean_sale_end = sale_cleaned["sale_end_at"]
        clean_sale_label = sale_cleaned["sale_label"]

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute(
        """
        UPDATE phones
        SET sale_active = ?, sale_price_pkr = ?, sale_start_at = ?, sale_end_at = ?, sale_label = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            clean_sale_active,
            clean_sale_price,
            clean_sale_start,
            clean_sale_end,
            clean_sale_label,
            now_str,
            phone_id,
        ),
    )
    conn.commit()
    conn.close()

    updated_phone = get_phone_by_id(phone_id)
    return JSONResponse(
        {
            "success": True,
            "phone_id": phone_id,
            "price_pkr": updated_phone["price_pkr"],
            "sale_active": updated_phone["sale_active"],
            "sale_price_pkr": updated_phone["sale_price_pkr"],
            "sale_label": updated_phone["sale_label"],
            "sale_start_at": updated_phone["sale_start_at"],
            "sale_end_at": updated_phone["sale_end_at"],
            "is_sale_active": updated_phone["is_sale_active"],
            "sale_status": updated_phone["sale_status"],
            "display_price_pkr": updated_phone["display_price_pkr"],
            "discount_percent": updated_phone["discount_percent"],
            "configured_discount_percent": updated_phone["configured_discount_percent"],
            "display_price_formatted": format_pkr(updated_phone["display_price_pkr"]),
            "regular_price_formatted": format_pkr(updated_phone["price_pkr"]),
            "sale_price_formatted": format_pkr(updated_phone["sale_price_pkr"]) if updated_phone["sale_price_pkr"] else None,
        }
    )


@app.post("/admin/api/phone/{phone_id}/quick-price")
async def admin_quick_price_update(
    request: Request,
    phone_id: int,
    price_pkr: int = Form(...),
    mark_verified: int = Form(0),
):
    """
    Updates the PKR price and logs the change in price_history.
    VERIFICATION SAFETY: Does NOT automatically change DEMO/SAMPLE to VERIFIED
    unless mark_verified=1 is explicitly requested by the administrator.
    """
    admin_user = get_current_admin(request)
    if not admin_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute(
        """
        SELECT p.*, b.name as brand_name, b.accent_color
        FROM phones p JOIN brands b ON b.id = p.brand_id
        WHERE p.id = ?
        """,
        (phone_id,),
    ).fetchone()
    if not row:
        conn.close()
        return JSONResponse({"error": "Phone not found"}, status_code=404)

    old_price = row["price_pkr"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if int(mark_verified) == 1:
        new_is_demo = 0
        new_status = "VERIFIED"
        new_verif_notes = (
            row["verification_notes"]
            if row["is_demo_data"] == 0
            else f"Verified by {admin_user} via Admin Panel"
        )
        new_source_name = (
            row["source_name"]
            if row["source_name"] and "Unverified" not in row["source_name"]
            else "Official Brand / Retailer Verified"
        )
        new_last_verified = now_str
    else:
        new_is_demo = row["is_demo_data"]
        new_status = "VERIFIED" if new_is_demo == 0 else "DEMO/SAMPLE"
        new_verif_notes = row["verification_notes"]
        new_source_name = row["source_name"]
        new_last_verified = row["last_verified_at"] if "last_verified_at" in row.keys() else None

    if row["image_url"].endswith(".svg"):
        generate_phone_svg(
            slug=row["slug"],
            brand_name=row["brand_name"],
            model_name=row["model_name"],
            accent_hex=row["accent_color"],
            secondary_hex="#1e293b",
            is_demo=bool(new_is_demo),
        )

    cursor.execute(
        """
        UPDATE phones
        SET price_pkr = ?, is_demo_data = ?, data_status = ?,
            source_name = ?, verification_notes = ?, data_source_note = ?,
            last_verified_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            price_pkr,
            new_is_demo,
            new_status,
            new_source_name,
            new_verif_notes,
            new_verif_notes,
            new_last_verified,
            now_str,
            phone_id,
        ),
    )

    if old_price != price_pkr:
        cursor.execute(
            """
            INSERT INTO price_history (phone_id, old_price_pkr, new_price_pkr, note, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (phone_id, old_price, price_pkr, f"Quick Price Update ({admin_user})", now_str),
        )

    conn.commit()
    conn.close()
    return JSONResponse(
        {
            "success": True,
            "phone_id": phone_id,
            "new_price_pkr": price_pkr,
            "price_formatted": format_pkr(price_pkr),
            "is_demo_data": new_is_demo,
            "data_status": new_status,
            "last_verified_at": new_last_verified,
            "updated_at": format_date_human(now_str),
            "updated_timestamp": now_str,
        }
    )


@app.post("/admin/api/phone/{phone_id}/verification")
async def admin_update_verification_details(
    request: Request,
    phone_id: int,
    data_status: str = Form(...),
    source_name: str = Form(""),
    source_url: str = Form(""),
    verification_notes: str = Form(""),
    catalog_status: Optional[str] = Form(None),
):
    """
    Explicitly updates Data Status (DEMO/SAMPLE vs VERIFIED), Source Name, Source URL,
    Verification Notes, and optional Catalog Status.
    """
    admin_user = get_current_admin(request)
    if not admin_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute(
        """
        SELECT p.*, b.name as brand_name, b.accent_color
        FROM phones p JOIN brands b ON b.id = p.brand_id
        WHERE p.id = ?
        """,
        (phone_id,),
    ).fetchone()
    if not row:
        conn.close()
        return JSONResponse({"error": "Phone not found"}, status_code=404)

    clean_status = "VERIFIED" if data_status.strip().upper() == "VERIFIED" else "DEMO/SAMPLE"
    clean_is_demo = 0 if clean_status == "VERIFIED" else 1
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_last_verified = now_str if clean_is_demo == 0 else None

    if clean_is_demo == 1:
        clean_source_name = source_name.strip() or "Demo / Sample Seed Catalog (Unverified)"
        clean_source_url = source_url.strip()
        clean_notes = verification_notes.strip() or DEMO_WARNING_TEXT
    else:
        clean_source_name = source_name.strip() or "Official Brand / Retailer Verified"
        clean_source_url = source_url.strip()
        clean_notes = verification_notes.strip() or f"Verified by {admin_user} via Admin Panel"

    valid_catalog_statuses = ("CURRENT", "OLDER_AVAILABLE", "OUTDATED", "NEEDS_REVIEW")
    if catalog_status and catalog_status.strip().upper() in valid_catalog_statuses:
        clean_catalog_status = catalog_status.strip().upper()
    else:
        clean_catalog_status = row["catalog_status"] if "catalog_status" in row.keys() and row["catalog_status"] else "CURRENT"

    if row["image_url"].endswith(".svg"):
        generate_phone_svg(
            slug=row["slug"],
            brand_name=row["brand_name"],
            model_name=row["model_name"],
            accent_hex=row["accent_color"],
            secondary_hex="#1e293b",
            is_demo=bool(clean_is_demo),
        )

    cursor.execute(
        """
        UPDATE phones
        SET is_demo_data = ?, data_status = ?, source_name = ?, source_url = ?,
            verification_notes = ?, data_source_note = ?, catalog_status = ?,
            last_verified_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            clean_is_demo,
            clean_status,
            clean_source_name,
            clean_source_url,
            clean_notes,
            clean_notes,
            clean_catalog_status,
            new_last_verified,
            now_str,
            phone_id,
        ),
    )
    conn.commit()
    conn.close()
    return JSONResponse(
        {
            "success": True,
            "phone_id": phone_id,
            "is_demo_data": clean_is_demo,
            "data_status": clean_status,
            "source_name": clean_source_name,
            "source_url": clean_source_url,
            "verification_notes": clean_notes,
            "catalog_status": clean_catalog_status,
            "last_verified_at": new_last_verified,
            "updated_at": format_date_human(now_str),
            "updated_timestamp": now_str,
        }
    )


@app.post("/admin/api/phone/{phone_id}/toggle-verify")
async def admin_toggle_verify_status(request: Request, phone_id: int):
    admin_user = get_current_admin(request)
    if not admin_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute(
        """
        SELECT p.*, b.name as brand_name, b.accent_color
        FROM phones p JOIN brands b ON b.id = p.brand_id
        WHERE p.id = ?
        """,
        (phone_id,),
    ).fetchone()
    if not row:
        conn.close()
        return JSONResponse({"error": "Phone not found"}, status_code=404)

    new_is_demo = 0 if row["is_demo_data"] == 1 else 1
    new_status = "VERIFIED" if new_is_demo == 0 else "DEMO/SAMPLE"
    new_note = (
        DEMO_WARNING_TEXT
        if new_is_demo == 1
        else f"Verified by {admin_user} via Admin Panel"
    )
    new_source = (
        "Demo / Sample Seed Catalog (Unverified)"
        if new_is_demo == 1
        else (
            row["source_name"]
            if row["source_name"] and "Unverified" not in row["source_name"]
            else "Official Brand / Retailer Verified"
        )
    )
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_last_verified = now_str if new_is_demo == 0 else None

    if row["image_url"].endswith(".svg"):
        generate_phone_svg(
            slug=row["slug"],
            brand_name=row["brand_name"],
            model_name=row["model_name"],
            accent_hex=row["accent_color"],
            secondary_hex="#1e293b",
            is_demo=bool(new_is_demo),
        )

    cursor.execute(
        """
        UPDATE phones
        SET is_demo_data = ?, data_status = ?, source_name = ?,
            verification_notes = ?, data_source_note = ?, last_verified_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (new_is_demo, new_status, new_source, new_note, new_note, new_last_verified, now_str, phone_id),
    )
    conn.commit()
    conn.close()
    return JSONResponse(
        {
            "success": True,
            "phone_id": phone_id,
            "is_demo_data": new_is_demo,
            "data_status": new_status,
            "source_name": new_source,
            "verification_notes": new_note,
            "last_verified_at": new_last_verified,
            "updated_at": format_date_human(now_str),
            "updated_timestamp": now_str,
        }
    )


@app.post("/admin/api/phone/{phone_id}/duplicate")
async def admin_duplicate_phone(request: Request, phone_id: int):
    admin_user = get_current_admin(request)
    if not admin_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    orig = get_phone_by_id(phone_id)
    if not orig:
        return JSONResponse({"error": "Phone not found"}, status_code=404)

    conn = get_db_connection()
    cursor = conn.cursor()
    new_model = f"{orig['model_name']} (Copy)"
    new_slug = f"{orig['slug']}-copy-{int(datetime.now().timestamp()) % 1000}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    img_url = generate_phone_svg(
        slug=new_slug,
        brand_name=orig["brand_name"],
        model_name=new_model,
        accent_hex=orig["brand_color"],
        secondary_hex="#1e293b",
        is_demo=True,
    )

    cursor.execute(
        """
        INSERT INTO phones (
            brand_id, model_name, official_variant_name, slug,
            price_pkr, currency, pta_status, availability,
            is_demo_data, data_status, source_name, source_url,
            verification_notes, data_source_note, image_url, gallery_json, release_date,
            ram_gb, ram_display, storage_gb, storage_display, processor,
            display_type, display_size_inch, display_resolution, refresh_rate,
            main_camera, selfie_camera, battery_mah, charging, network, is_5g,
            os, dimensions, weight, build_material, sim_type, colors, sensors,
            summary_text, is_latest, is_popular, views_count, created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?,
            ?, 'PKR', ?, ?,
            1, 'DEMO/SAMPLE', 'Duplicated Draft (Unverified)', '',
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, 0, 0, 1, ?, ?
        )
        """,
        (
            orig["brand_id"],
            new_model,
            orig.get("official_variant_name", new_model),
            new_slug,
            orig["price_pkr"],
            orig["pta_status"],
            orig["availability"],
            DEMO_WARNING_TEXT,
            DEMO_WARNING_TEXT,
            img_url,
            json.dumps([img_url]),
            orig["release_date"],
            orig["ram_gb"],
            orig["ram_display"],
            orig["storage_gb"],
            orig["storage_display"],
            orig["processor"],
            orig["display_type"],
            orig["display_size_inch"],
            orig["display_resolution"],
            orig["refresh_rate"],
            orig["main_camera"],
            orig["selfie_camera"],
            orig["battery_mah"],
            orig["charging"],
            orig["network"],
            orig["is_5g"],
            orig["os"],
            orig["dimensions"],
            orig["weight"],
            orig["build_material"],
            orig["sim_type"],
            orig["colors"],
            orig["sensors"],
            orig["summary_text"],
            now_str,
            now_str,
        ),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "new_id": new_id})


@app.post("/admin/api/phone/{phone_id}/delete")
async def admin_delete_phone(request: Request, phone_id: int):
    admin_user = get_current_admin(request)
    if not admin_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    conn = get_db_connection()
    conn.execute("DELETE FROM phones WHERE id = ?", (phone_id,))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True})


@app.post("/admin/api/brand/save")
async def admin_save_brand(
    request: Request,
    name: str = Form(...),
    country: str = Form(""),
    tagline: str = Form(""),
    description: str = Form(""),
    accent_color: str = Form("#2563eb"),
):
    admin_user = get_current_admin(request)
    if not admin_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    clean_slug = slugify(name)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO brands (name, slug, country, tagline, description, accent_color, display_order, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 15, ?)
        ON CONFLICT(slug) DO UPDATE SET
            name = excluded.name,
            country = excluded.country,
            tagline = excluded.tagline,
            description = excluded.description,
            accent_color = excluded.accent_color,
            updated_at = excluded.updated_at
        """,
        (
            name.strip(),
            clean_slug,
            country.strip(),
            tagline.strip(),
            description.strip(),
            accent_color,
            now_str,
        ),
    )
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "slug": clean_slug})


@app.post("/admin/api/upload-image")
async def admin_upload_phone_image(request: Request, file: UploadFile = File(...)):
    admin_user = get_current_admin(request)
    if not admin_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    ext = os.path.splitext(file.filename or "image.png")[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    if ext not in mime_map:
        return JSONResponse({"error": "Unsupported image format"}, status_code=400)

    safe_name = f"upload-{int(datetime.now().timestamp())}{ext}"
    static_dir = os.path.join(BASE_DIR, "static", "images", "phones")
    os.makedirs(static_dir, exist_ok=True)
    save_path = os.path.join(static_dir, safe_name)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    uploads_dir = get_uploads_dir()
    if os.path.abspath(uploads_dir) != os.path.abspath(static_dir):
        with open(os.path.join(uploads_dir, safe_name), "wb") as f2:
            f2.write(content)

    save_media_asset_to_db(safe_name, content, mime_map[ext])
    return JSONResponse({"success": True, "image_url": f"/static/images/phones/{safe_name}"})


@app.get("/admin/api/backup/sqlite")
async def admin_download_sqlite_backup(request: Request):
    """Download a hot-safe binary backup of mobile_hub.db directly from the Admin Panel."""
    admin_user = get_current_admin(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    import tempfile

    src_conn = get_db_connection()
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        dst_conn = sqlite3.connect(tmp_path)
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        with open(tmp_path, "rb") as f:
            db_bytes = f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=db_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="mobile_hub_backup_{ts}.db"'},
    )


@app.get("/admin/api/backup/json")
async def admin_download_json_export(request: Request):
    """Export all brands, phones, variants, price history, and feedback reports as a JSON backup."""
    admin_user = get_current_admin(request)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=302)

    conn = get_db_connection()
    export_payload = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "brands": [dict(r) for r in conn.execute("SELECT * FROM brands ORDER BY id").fetchall()],
        "phones": [dict(r) for r in conn.execute("SELECT * FROM phones ORDER BY id").fetchall()],
        "phone_variants": [dict(r) for r in conn.execute("SELECT * FROM phone_variants ORDER BY id").fetchall()],
        "price_history": [dict(r) for r in conn.execute("SELECT * FROM price_history ORDER BY id").fetchall()],
        "data_feedback_reports": [
            dict(r) for r in conn.execute("SELECT * FROM data_feedback_reports ORDER BY id").fetchall()
        ],
    }
    conn.close()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=json.dumps(export_payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="mobile_hub_export_{ts}.json"'},
    )


@app.get("/healthz")
async def health_check():
    dq = get_data_quality_metrics()
    return {
        "status": "ok",
        "database": "connected",
        "db_file": os.path.basename(get_db_path()),
        "phones_count": dq["total_phones"],
        "demo_count": dq["demo_count"],
        "verified_count": dq["verified_count"],
        "latest_current_count": dq["latest_current_count"],
        "outdated_count": dq["outdated_count"],
    }


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app:app", host=host, port=port, reload=False)
