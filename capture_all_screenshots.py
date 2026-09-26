import os
import subprocess
import requests

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:8000"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(OUT_DIR, exist_ok=True)


def capture(url: str, filename: str, width: int = 1440, height: int = 1350):
    out_path = os.path.join(OUT_DIR, filename)
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--screenshot={out_path}",
        url,
    ]
    subprocess.run(cmd, check=True)
    print(f"[SCREENSHOT] {filename} -> {out_path} ({os.path.getsize(out_path):,} bytes)")


def main():
    # 1. Home Page
    capture(f"{BASE_URL}/", "after_home.png", 1440, 1450)

    # 2. Brand Page
    capture(f"{BASE_URL}/brand/samsung", "after_brands.png", 1440, 1150)

    # 3. Phone Finder Page
    capture(f"{BASE_URL}/phones", "after_finder.png", 1440, 1250)

    # 4. Phone Detail Page (iPhone 16 Pro Max matching reference)
    capture(f"{BASE_URL}/phone/apple-iphone-16-pro-max", "after_detail.png", 1440, 1350)

    # 5. Compare Page
    capture(f"{BASE_URL}/compare", "after_compare.png", 1440, 1080)

    # 6. Authenticated Admin Panel
    s = requests.Session()
    r_login = s.post(f"{BASE_URL}/admin/login", data={"username": "admin", "password": "admin123"}, allow_redirects=True)
    admin_html = r_login.text.replace("<head>", '<head><base href="http://127.0.0.1:8000/">', 1)
    temp_admin_html = os.path.join(OUT_DIR, "_admin_snapshot.html")
    with open(temp_admin_html, "w", encoding="utf-8") as f:
        f.write(admin_html)
    capture(f"file:///{temp_admin_html.replace(os.sep, '/')}", "after_admin.png", 1440, 1180)
    try:
        os.remove(temp_admin_html)
    except OSError:
        pass

    # 7. Mobile Responsive View (390x1200)
    capture(f"{BASE_URL}/", "after_mobile.png", 390, 1200)


if __name__ == "__main__":
    main()
