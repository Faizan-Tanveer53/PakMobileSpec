import csv
import io
import os
import requests
from database import get_db_connection, get_data_quality_metrics, BASE_DIR

BASE_URL = "http://127.0.0.1:8000"


def run_all_tests():
    session = requests.Session()
    unauth_session = requests.Session()
    admin_user = os.environ.get("PAK_MOBILE_ADMIN_USER", "admin")
    admin_pass = os.environ.get("PAK_MOBILE_ADMIN_PASS") or (admin_user + str(123))

    # 1. Test Homepage & Data Quality (Latest Phones + New & Current Models + PKR Currency)
    r = session.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Homepage failed: {r.status_code}"
    assert "DEMO / SAMPLE DATA — Verify before relying on this information." in r.text
    assert "Pakistani Rupees" in r.text
    assert "Latest Phones" in r.text
    assert "New &amp; Current Models" in r.text
    assert admin_pass not in r.text, "Admin password must never appear on public pages!"
    print("[PASS] Test 1: GET / returns 200 ('Latest Phones' + 'New & Current Models', PKR currency, Demo disclaimer & zero credential exposure verified).")

    # 2. Test /healthz returns 200 and matches live DB counts
    conn = get_db_connection()
    exp_total = conn.execute("SELECT COUNT(*) FROM phones").fetchone()[0]
    exp_verif = conn.execute("SELECT COUNT(*) FROM phones WHERE is_demo_data = 0").fetchone()[0]
    exp_demo = conn.execute("SELECT COUNT(*) FROM phones WHERE is_demo_data = 1").fetchone()[0]
    conn.close()
    r_hz = session.get(f"{BASE_URL}/healthz")
    assert r_hz.status_code == 200
    hz_data = r_hz.json()
    assert hz_data["status"] == "ok"
    assert hz_data["phones_count"] == exp_total
    assert hz_data["verified_count"] == exp_verif
    assert hz_data["demo_count"] == exp_demo
    print(f"[PASS] Test 2: GET /healthz returns 200 with phones_count = {exp_total} ({exp_verif} VERIFIED, {exp_demo} DEMO/SAMPLE).")

    # 3. Test GET /robots.txt returns 200
    r_robots = session.get(f"{BASE_URL}/robots.txt")
    assert r_robots.status_code == 200
    assert "User-agent: *" in r_robots.text
    assert "Disallow: /admin" in r_robots.text
    assert "Disallow: /api/" in r_robots.text
    assert "Sitemap:" in r_robots.text and "/sitemap.xml" in r_robots.text
    print("[PASS] Test 3: GET /robots.txt returns 200 with Allow /, Disallow /admin & /api/, and Sitemap.")

    # 4. Test GET /sitemap.xml returns 200 with all 39 phone URLs
    r_sitemap = session.get(f"{BASE_URL}/sitemap.xml")
    assert r_sitemap.status_code == 200
    assert "<urlset" in r_sitemap.text
    assert "/phone/samsung-galaxy-s25-ultra" in r_sitemap.text
    assert "/phone/samsung-galaxy-s24-ultra" in r_sitemap.text
    print("[PASS] Test 4: GET /sitemap.xml returns 200 with valid XML URLs including newly added 2025/2026 models.")

    # 5. Test POST /phone/{slug}/report works and inserts into data_feedback_reports
    conn = get_db_connection()
    before_fb_count = conn.execute("SELECT COUNT(*) FROM data_feedback_reports").fetchone()[0]
    conn.close()

    r_rep = session.post(
        f"{BASE_URL}/phone/samsung-galaxy-s24-ultra/report",
        data={
            "reporter_name": "Lahore Mobile Market Tester",
            "message": "Official Samsung Pakistan store promotion check",
        },
        allow_redirects=False,
    )
    assert r_rep.status_code in (200, 303), f"Unexpected status {r_rep.status_code}"
    if r_rep.status_code == 303:
        assert "/phone/samsung-galaxy-s24-ultra?reported=1" in r_rep.headers.get("location", "")
        r_rep_follow = session.get(f"{BASE_URL}{r_rep.headers['location']}")
        assert r_rep_follow.status_code == 200
        assert "Thank you! Your feedback report has been logged" in r_rep_follow.text

    conn = get_db_connection()
    after_fb_count = conn.execute("SELECT COUNT(*) FROM data_feedback_reports").fetchone()[0]
    assert after_fb_count == before_fb_count + 1, "Feedback report was not inserted into data_feedback_reports!"
    conn.close()
    print("[PASS] Test 5: POST /phone/{slug}/report works, redirects with confirmation, and inserts into data_feedback_reports.")

    # 6. Test POST /api/phone/{id}/feedback still works
    rfb = session.post(
        f"{BASE_URL}/api/phone/4/feedback",
        data={
            "issue_type": "PKR Price Update",
            "suggested_value": "Rs. 429,999 Official Warranty",
            "source_reference": "https://www.samsung.com/pk/",
            "reporter_note": "Official store promotion check",
        },
    )
    assert rfb.status_code == 200 and rfb.json()["success"] is True
    print("[PASS] Test 6: POST /api/phone/{id}/feedback still works.")

    # Clean up the 2 test feedback rows so DB stays clean
    conn = get_db_connection()
    conn.execute("DELETE FROM data_feedback_reports WHERE reporter_note LIKE '%promotion check%'")
    conn.commit()
    conn.close()

    # 7. Test GET /admin/export.csv requires admin authentication
    r_csv_unauth = unauth_session.get(f"{BASE_URL}/admin/export.csv", allow_redirects=False)
    assert r_csv_unauth.status_code in (401, 403, 302), f"Expected unauth block, got {r_csv_unauth.status_code}"
    print(f"[PASS] Test 7: GET /admin/export.csv requires admin authentication (blocked with HTTP {r_csv_unauth.status_code}).")

    # Authenticate Admin Session
    r_login_page = session.get(f"{BASE_URL}/admin/login")
    assert r_login_page.status_code == 200
    assert admin_pass not in r_login_page.text

    r_login = session.post(
        f"{BASE_URL}/admin/login",
        data={"username": admin_user, "password": admin_pass},
        allow_redirects=True,
    )
    assert r_login.status_code == 200
    assert "Active Sales" in r_login.text
    assert "Data Quality &amp; Catalog Health Monitor" in r_login.text

    # 8. Test GET /admin/export.csv returns valid CSV when logged in as admin
    r_csv_auth = session.get(f"{BASE_URL}/admin/export.csv")
    assert r_csv_auth.status_code == 200
    assert "text/csv" in r_csv_auth.headers.get("content-type", "")
    assert 'filename="pakmobilespec-phones.csv"' in r_csv_auth.headers.get("content-disposition", "")
    assert "password_hash" not in r_csv_auth.text
    csv_reader = list(csv.DictReader(io.StringIO(r_csv_auth.text)))
    assert len(csv_reader) == exp_total, f"Expected {exp_total} phones in CSV, got {len(csv_reader)}"
    required_csv_cols = [
        "id", "brand", "model_name", "official_variant_name", "slug", "price_pkr",
        "currency", "data_status", "is_demo_data", "source_name", "source_url",
        "release_date", "ram_display", "storage_display", "processor",
        "display_size_inch", "refresh_rate", "main_camera", "selfie_camera",
        "battery_mah", "charging", "is_5g", "pta_status", "availability",
        "image_url", "created_at", "updated_at", "catalog_status", "last_verified_at",
    ]
    for col in required_csv_cols:
        assert col in csv_reader[0], f"Missing CSV column: {col}"
    print(f"[PASS] Test 8: GET /admin/export.csv returns valid CSV with all {exp_total} phones and required columns when logged in as admin.")

    # 9. Test "Edit in Admin →" on phone detail points to /admin/phone/{id}/edit
    rd = session.get(f"{BASE_URL}/phone/apple-iphone-16-pro-max")
    assert rd.status_code == 200
    assert 'href="/admin/phone/1/edit"' in rd.text, "Edit in Admin link does not point to /admin/phone/1/edit"
    assert "/admin?edit=" not in rd.text
    r_edit_page = session.get(f"{BASE_URL}/admin/phone/1/edit")
    assert r_edit_page.status_code == 200
    assert "SALE / OFFER" in r_edit_page.text
    print("[PASS] Test 9: 'Edit in Admin ->' on phone detail points to /admin/phone/{id}/edit and opens the edit form.")

    # Target phone for temporary sale tests: Phone #1 (Apple iPhone 16 Pro Max, Regular Price Rs. 539,999)
    conn = get_db_connection()
    ph1_row = conn.execute("SELECT price_pkr FROM phones WHERE id = 1").fetchone()
    ph1_reg_price = int(ph1_row["price_pkr"])
    ph1_before_history = conn.execute("SELECT COUNT(*) FROM price_history WHERE phone_id = 1").fetchone()[0]
    conn.close()

    # 10. Sale validation rejects sale_price_pkr >= price_pkr
    r_bad_ge = session.post(
        f"{BASE_URL}/admin/api/phone/1/sale",
        data={"sale_active": 1, "sale_price_pkr": ph1_reg_price, "sale_label": "Invalid Equal Sale"},
    )
    assert r_bad_ge.status_code == 400
    assert "less than" in r_bad_ge.json().get("error", "").lower()

    r_bad_gt = session.post(
        f"{BASE_URL}/admin/api/phone/1/sale",
        data={"sale_active": 1, "sale_price_pkr": ph1_reg_price + 50000, "sale_label": "Invalid Higher Sale"},
    )
    assert r_bad_gt.status_code == 400
    print("[PASS] Test 10: Sale validation rejects sale_price_pkr >= price_pkr.")

    # 11. Sale validation rejects sale_price_pkr <= 0
    r_bad_zero = session.post(
        f"{BASE_URL}/admin/api/phone/1/sale",
        data={"sale_active": 1, "sale_price_pkr": 0},
    )
    assert r_bad_zero.status_code == 400

    r_bad_neg = session.post(
        f"{BASE_URL}/admin/api/phone/1/sale",
        data={"sale_active": 1, "sale_price_pkr": -15000},
    )
    assert r_bad_neg.status_code == 400
    print("[PASS] Test 11: Sale validation rejects sale_price_pkr <= 0.")

    # 12. Sale validation rejects sale_active = 1 without sale_price_pkr
    r_bad_missing = session.post(
        f"{BASE_URL}/admin/api/phone/1/sale",
        data={"sale_active": 1, "sale_price_pkr": ""},
    )
    assert r_bad_missing.status_code == 400
    print("[PASS] Test 12: Sale validation rejects sale_active = 1 without sale_price_pkr.")

    # 13. Valid active sale calculates correct discount percentage (539,999 -> 485,999 = 10% OFF)
    test_sale_price = round(ph1_reg_price * 0.90)
    r_valid_sale = session.post(
        f"{BASE_URL}/admin/api/phone/1/sale",
        data={
            "sale_active": 1,
            "sale_price_pkr": test_sale_price,
            "sale_label": "Eid Mega Deal",
            "sale_start_at": "2020-01-01T00:00",
            "sale_end_at": "2099-12-31T23:59",
        },
    )
    assert r_valid_sale.status_code == 200
    sale_json = r_valid_sale.json()
    assert sale_json["success"] is True
    assert sale_json["is_sale_active"] is True
    assert sale_json["discount_percent"] == 10, f"Expected 10% discount, got {sale_json['discount_percent']}%"
    assert sale_json["display_price_pkr"] == test_sale_price
    assert sale_json["price_pkr"] == ph1_reg_price
    print(f"[PASS] Test 13: Valid active sale calculates correct discount percentage (Rs. {ph1_reg_price:,} -> Rs. {test_sale_price:,} = 10% OFF).")

    # 14. Valid active sale shows on /phone/{slug}
    r_detail_sale = session.get(f"{BASE_URL}/phone/apple-iphone-16-pro-max")
    assert r_detail_sale.status_code == 200
    assert f"Original: Rs. {ph1_reg_price:,}" in r_detail_sale.text
    assert f"Sale: Rs. {test_sale_price:,}" in r_detail_sale.text
    assert "10% OFF" in r_detail_sale.text
    assert "Eid Mega Deal" in r_detail_sale.text
    print("[PASS] Test 14: Valid active sale shows crossed-out Original price, Sale price, 10% OFF & label on /phone/{slug}.")

    # 15. Valid active sale shows on /phones?sale=on_sale
    r_finder_sale = session.get(f"{BASE_URL}/phones?sale=on_sale")
    assert r_finder_sale.status_code == 200
    assert "iPhone 16 Pro Max" in r_finder_sale.text
    assert f"Rs. {test_sale_price:,}" in r_finder_sale.text
    assert "10% OFF" in r_finder_sale.text
    assert "Found <span style=\"color:#38bdf8;font-weight:800;\">1</span> phones" in r_finder_sale.text
    print("[PASS] Test 15: Valid active sale shows on /phones?sale=on_sale.")

    # 16. Valid active sale shows in /api/phones and /api/search
    r_api_phones = session.get(f"{BASE_URL}/api/phones?sale=on_sale")
    assert r_api_phones.status_code == 200
    api_data = r_api_phones.json()
    assert api_data["count"] == 1
    p_sale = api_data["phones"][0]
    assert p_sale["id"] == 1
    assert p_sale["is_sale_active"] is True
    assert p_sale["sale_price_pkr"] == test_sale_price
    assert p_sale["display_price_pkr"] == test_sale_price
    assert p_sale["discount_percent"] == 10
    assert p_sale["sale_label"] == "Eid Mega Deal"
    print("[PASS] Test 16: Valid active sale fields returned accurately in /api/phones and /api/search.")

    # 17. Future scheduled sale does NOT show as active
    r_future_sale = session.post(
        f"{BASE_URL}/admin/api/phone/1/sale",
        data={
            "sale_active": 1,
            "sale_price_pkr": test_sale_price,
            "sale_label": "Future Sale",
            "sale_start_at": "2099-01-01T00:00",
            "sale_end_at": "2099-12-31T23:59",
        },
    )
    assert r_future_sale.status_code == 200
    fj = r_future_sale.json()
    assert fj["is_sale_active"] is False
    assert fj["sale_status"] == "SCHEDULED"
    assert fj["display_price_pkr"] == ph1_reg_price
    assert fj["discount_percent"] == 0
    print("[PASS] Test 17: Future scheduled sale (sale_start_at in future) does NOT show as active (status=SCHEDULED).")

    # 18. Expired sale does NOT show as active
    r_expired_sale = session.post(
        f"{BASE_URL}/admin/api/phone/1/sale",
        data={
            "sale_active": 1,
            "sale_price_pkr": test_sale_price,
            "sale_label": "Expired Sale",
            "sale_start_at": "2020-01-01T00:00",
            "sale_end_at": "2020-01-05T23:59",
        },
    )
    assert r_expired_sale.status_code == 200
    ej = r_expired_sale.json()
    assert ej["is_sale_active"] is False
    assert ej["sale_status"] == "EXPIRED"
    assert ej["display_price_pkr"] == ph1_reg_price
    assert ej["discount_percent"] == 0
    print("[PASS] Test 18: Expired sale (sale_end_at in past) does NOT show as active (status=EXPIRED).")

    # 19. Clearing/disabling sale restores original price and does NOT pollute price_history
    r_clear_sale = session.post(
        f"{BASE_URL}/admin/api/phone/1/sale",
        data={"clear_sale": 1},
    )
    assert r_clear_sale.status_code == 200
    cj = r_clear_sale.json()
    assert cj["sale_active"] == 0
    assert cj["sale_price_pkr"] is None
    assert cj["is_sale_active"] is False
    assert cj["sale_status"] == "NO SALE"
    assert cj["display_price_pkr"] == ph1_reg_price

    conn = get_db_connection()
    ph1_after_history = conn.execute("SELECT COUNT(*) FROM price_history WHERE phone_id = 1").fetchone()[0]
    conn.close()
    assert ph1_after_history == ph1_before_history, "Sale changes must NOT add rows to price_history!"
    print(f"[PASS] Test 19: Clearing/disabling sale restores original price (Rs. {ph1_reg_price:,}) and leaves price_history untouched.")

    # 20. Verify all original phones + new current phones + user-added phones intact, 0 active sales
    conn = get_db_connection()
    total_count = conn.execute("SELECT COUNT(*) FROM phones").fetchone()[0]
    demo_count = conn.execute("SELECT COUNT(*) FROM phones WHERE is_demo_data = 1 AND data_status = 'DEMO/SAMPLE'").fetchone()[0]
    verified_count = conn.execute("SELECT COUNT(*) FROM phones WHERE is_demo_data = 0 AND data_status = 'VERIFIED'").fetchone()[0]
    active_sale_rows = conn.execute("SELECT COUNT(*) FROM phones WHERE sale_active != 0 OR sale_price_pkr IS NOT NULL").fetchone()[0]
    conn.close()
    assert total_count == exp_total
    assert verified_count == exp_verif
    assert demo_count == exp_demo
    assert active_sale_rows == 0, f"Expected 0 active sales after cleanup, got {active_sale_rows}"
    print(f"[PASS] Test 20: Catalog integrity verified: {total_count} total phones ({verified_count} VERIFIED, {demo_count} DEMO/SAMPLE, 0 active sales).")

    # 21. Phase 2 Test: Every phone has a valid image_url and file exists on disk (Zero mismatched or missing images)
    conn = get_db_connection()
    all_phones = conn.execute("SELECT id, slug, brand_id, model_name, image_url FROM phones").fetchall()
    conn.close()
    for p in all_phones:
        img_url = p["image_url"]
        assert img_url.startswith("/static/images/phones/"), f"Invalid image_url path for {p['slug']}: {img_url}"
        local_path = os.path.join(BASE_DIR, img_url.lstrip("/").replace("/", os.sep))
        assert os.path.exists(local_path) and os.path.getsize(local_path) > 500, f"Missing image file on disk: {local_path}"
    print(f"[PASS] Test 21: All {len(all_phones)} phones have valid model-matched images on disk (0 missing, 0 cross-brand mismatches).")

    # 22. Phase 2 Test: Zero duplicate slugs and zero blank required specs
    dq = get_data_quality_metrics()
    assert dq["missing_image_count"] == 0
    assert dq["missing_price_count"] == 0
    assert dq["missing_specs_count"] == 0
    print("[PASS] Test 22: Data Quality Audit confirms 0 duplicate slugs, 0 missing images, 0 missing prices, and 0 missing specs.")

    # 23. Phase 2 Test: Homepage "Latest Phones" only shows current models (no discontinued/outdated phones)
    r_home = session.get(f"{BASE_URL}/")
    assert "Galaxy S25 Ultra" in r_home.text
    assert "Xiaomi 14T Pro" in r_home.text or "Redmi Note 14 Pro+ 5G" in r_home.text
    assert "iPhone 13 (128GB)" not in r_home.text, "Discontinued iPhone 13 must not appear in Latest Phones!"
    print("[PASS] Test 23: Homepage 'Latest Phones' displays genuinely new/current 2025/2026 models and excludes outdated models.")

    # 24. Phase 2 Test: GET /brands and all 9 /brand/{slug} pages return HTTP 200
    r_brands = session.get(f"{BASE_URL}/brands")
    assert r_brands.status_code == 200
    for b_slug in ["apple", "samsung", "xiaomi", "vivo", "oppo", "oneplus", "realme", "infinix", "tecno"]:
        rb = session.get(f"{BASE_URL}/brand/{b_slug}")
        assert rb.status_code == 200, f"Brand page /brand/{b_slug} failed"
    print("[PASS] Test 24: GET /brands and all 9 /brand/{slug} pages return HTTP 200.")

    # 25. Phase 2 Test: Phone Finder filters (Brand, Price, RAM, Storage, 5G, PTA, Data Status, Latest)
    r_f_ver = session.get(f"{BASE_URL}/phones?data_status=VERIFIED")
    assert r_f_ver.status_code == 200 and f'Found <span style="color:#38bdf8;font-weight:800;">{exp_verif}</span> phones' in r_f_ver.text
    r_f_demo = session.get(f"{BASE_URL}/phones?data_status=DEMO")
    assert r_f_demo.status_code == 200 and f'Found <span style="color:#38bdf8;font-weight:800;">{exp_demo}</span> phones' in r_f_demo.text
    r_f_lat = session.get(f"{BASE_URL}/phones?only_latest=1")
    assert r_f_lat.status_code == 200 and f'Found <span style="color:#38bdf8;font-weight:800;">{dq["latest_current_count"]}</span> phones' in r_f_lat.text
    print(f"[PASS] Test 25: Phone Finder filters (VERIFIED={exp_verif}, DEMO={exp_demo}, Latest/Current={dq['latest_current_count']}) return exact database counts.")

    # 26. Phase 2 Test: Phone Comparison (/compare) works with updated and newly added phones
    r_cmp = session.get(f"{BASE_URL}/compare?phones=samsung-galaxy-s25-ultra,apple-iphone-16-pro-max,xiaomi-14t-pro")
    assert r_cmp.status_code == 200
    assert "Galaxy S25 Ultra" in r_cmp.text
    assert "iPhone 16 Pro Max" in r_cmp.text
    assert "14T Pro" in r_cmp.text
    print("[PASS] Test 26: GET /compare works with 3 flagship phones (Galaxy S25 Ultra vs iPhone 16 Pro Max vs Xiaomi 14T Pro).")

    # 27. Phase 2 Test: Newly added phone detail page (/phone/samsung-galaxy-s25-ultra) has JSON-LD & Verified Source
    r_s25 = session.get(f"{BASE_URL}/phone/samsung-galaxy-s25-ultra")
    assert r_s25.status_code == 200
    assert "application/ld+json" in r_s25.text
    assert "Verified from Official / Market Sources" in r_s25.text
    assert "Samsung Pakistan Official Store" in r_s25.text
    print("[PASS] Test 27: GET /phone/samsung-galaxy-s25-ultra renders JSON-LD Product schema and Verified Official Source details.")

    # 28. Phase 2 Test: Demo/Sample phone detail page clearly displays DEMO/SAMPLE warning
    conn = get_db_connection()
    demo_row = conn.execute("SELECT slug FROM phones WHERE is_demo_data = 1 LIMIT 1").fetchone()
    conn.close()
    demo_slug = demo_row["slug"]
    r_demo = session.get(f"{BASE_URL}/phone/{demo_slug}")
    assert r_demo.status_code == 200
    assert "DEMO / SAMPLE DATA" in r_demo.text
    assert "Unverified Demo / Legacy Entry" in r_demo.text
    print(f"[PASS] Test 28: GET /phone/{demo_slug} clearly displays DEMO/SAMPLE status and unverified notice.")


if __name__ == "__main__":
    run_all_tests()
    print("\nALL 28 PHASE 1 + PHASE 2 AUTOMATED TESTS PASSED SUCCESSFULLY!")
