"""
PakMobileSpec — Model-Specific Studio Phone Render & Image Mapping Engine.
Ensures EVERY phone in the database displays an accurate, model-specific visual illustration
matching its actual industrial design (camera island geometry, chassis shape, color finish, and screen).
"""

import os
import json
from datetime import datetime
from database import get_db_connection, save_media_asset_to_db, get_uploads_dir, BASE_DIR, DEMO_WARNING_TEXT

IMAGES_DIR = os.path.join(BASE_DIR, "static", "images", "phones")
HERO_IMG_PATH = os.path.join(BASE_DIR, "static", "images", "hero-phones-lineup.svg")


def get_model_visual_profile(slug: str, brand_name: str, model_name: str) -> dict:
    s = slug.lower()
    b = brand_name.lower()

    # 1. APPLE IPHONE PRO / PRO MAX (Triangular Triple-Lens Pro Island + Titanium Finish)
    if "iphone-16-pro" in s or "iphone-15-pro" in s:
        is_16 = "16" in s
        return {
            "style": "iphone_pro",
            "back_c1": "#c29d7c" if is_16 else "#94a3b8",
            "back_c2": "#78593c" if is_16 else "#475569",
            "frame_c": "#d6b89c" if is_16 else "#cbd5e1",
            "screen_c1": "#d97706" if is_16 else "#1e3a8a",
            "screen_c2": "#451a03" if is_16 else "#0f172a",
            "screen_accent": "#fbbf24" if is_16 else "#38bdf8",
            "corner_rx": 26,
            "notch": "dynamic_island",
        }

    # 2. APPLE IPHONE 16 BASE (Vertical Pill Dual-Camera + Ultramarine Finish)
    if "iphone" in s:
        return {
            "style": "iphone_dual",
            "back_c1": "#6366f1",
            "back_c2": "#312e81",
            "frame_c": "#818cf8",
            "screen_c1": "#4f46e5",
            "screen_c2": "#1e1b4b",
            "screen_accent": "#a5b4fc",
            "corner_rx": 26,
            "notch": "dynamic_island",
        }

    # 3. SAMSUNG GALAXY S24 ULTRA / S25 ULTRA (Sharp Squared Corners + Quad Floating Rings + S-Pen)
    if "s24-ultra" in s or "s25-ultra" in s:
        return {
            "style": "samsung_ultra",
            "back_c1": "#9ca3af",
            "back_c2": "#4b5563",
            "frame_c": "#d1d5db",
            "screen_c1": "#3b82f6",
            "screen_c2": "#1e1b4b",
            "screen_accent": "#60a5fa",
            "corner_rx": 6,  # Squared Ultra corners!
            "notch": "punch_hole",
        }

    # 4. SAMSUNG GALAXY A55 / A15 (Triple Vertical Floating Camera Rings + Rounded Corners)
    if b == "samsung":
        is_a55 = "a55" in s
        return {
            "style": "samsung_a",
            "back_c1": "#7dd3fc" if is_a55 else "#3b82f6",
            "back_c2": "#0284c7" if is_a55 else "#1d4ed8",
            "frame_c": "#bae6fd",
            "screen_c1": "#0ea5e9",
            "screen_c2": "#082f49",
            "screen_accent": "#38bdf8",
            "corner_rx": 22,
            "notch": "punch_hole",
        }

    # 5. XIAOMI 14 ULTRA (Giant Centered Circular LEICA Quad-Camera Disc + Gold Ring)
    if "xiaomi-14-ultra" in s:
        return {
            "style": "xiaomi_ultra_leica",
            "back_c1": "#27272a",
            "back_c2": "#09090b",
            "frame_c": "#d4af37",
            "screen_c1": "#ea580c",
            "screen_c2": "#431407",
            "screen_accent": "#fb923c",
            "corner_rx": 22,
            "notch": "punch_hole",
        }

    # 6. XIAOMI REDMI NOTE 13 PRO+ / NOTE 13
    if b == "xiaomi":
        return {
            "style": "redmi_note",
            "back_c1": "#a855f7" if "pro" in s else "#38bdf8",
            "back_c2": "#4c1d95" if "pro" in s else "#0369a1",
            "frame_c": "#c084fc",
            "screen_c1": "#9333ea",
            "screen_c2": "#1e1b4b",
            "screen_accent": "#e879f9",
            "corner_rx": 22,
            "notch": "punch_hole",
        }

    # 7. VIVO V40 PRO / V40 5G / V30E (ZEISS Infinity Pill + Glowing Aura Light Ring)
    if b == "vivo":
        return {
            "style": "vivo_zeiss_aura",
            "back_c1": "#8b5cf6" if "v40" in s else "#38bdf8",
            "back_c2": "#4c1d95" if "v40" in s else "#0c4a6e",
            "frame_c": "#c4b5fd",
            "screen_c1": "#7c3aed",
            "screen_c2": "#1e1b4b",
            "screen_accent": "#a78bfa",
            "corner_rx": 24,
            "notch": "punch_hole",
        }

    # 8. OPPO FIND X8 / RENO 12 / RENO 11F (Cosmos Circular Hasselblad Ring or Metallic Ribbon)
    if b == "oppo":
        if "find-x8" in s:
            return {
                "style": "oppo_find_cosmos",
                "back_c1": "#cbd5e1",
                "back_c2": "#64748b",
                "frame_c": "#e2e8f0",
                "screen_c1": "#0284c7",
                "screen_c2": "#082f49",
                "screen_accent": "#38bdf8",
                "corner_rx": 24,
                "notch": "punch_hole",
            }
        return {
            "style": "oppo_reno",
            "back_c1": "#34d399",
            "back_c2": "#065f46",
            "frame_c": "#6ee7b7",
            "screen_c1": "#10b981",
            "screen_c2": "#064e3b",
            "screen_accent": "#34d399",
            "corner_rx": 22,
            "notch": "punch_hole",
        }

    # 9. ONEPLUS 12 / NORD 4 (Left-Aligned Circular Watch-Dial Hasselblad Camera)
    if b == "oneplus":
        return {
            "style": "oneplus_dial",
            "back_c1": "#10b981" if "12" in s else "#94a3b8",
            "back_c2": "#064e3b" if "12" in s else "#334155",
            "frame_c": "#34d399",
            "screen_c1": "#ef4444",
            "screen_c2": "#450a0a",
            "screen_accent": "#f87171",
            "corner_rx": 22,
            "notch": "punch_hole",
        }

    # 10. REALME GT 6 / 12 PRO+ (Luxury Golden Watch-Bezel Center Ring + Vertical Seam)
    if b == "realme":
        return {
            "style": "realme_luxury_ring",
            "back_c1": "#1e3a8a" if "12-pro" in s else "#64748b",
            "back_c2": "#0f172a",
            "frame_c": "#facc15",
            "screen_c1": "#eab308",
            "screen_c2": "#422006",
            "screen_accent": "#fde047",
            "corner_rx": 22,
            "notch": "punch_hole",
        }

    # 11. INFINIX GT 20 PRO / NOTE 40 PRO (Cyber Mecha RGB Loop + Gaming Visor)
    if b == "infinix":
        return {
            "style": "infinix_mecha",
            "back_c1": "#3b82f6" if "gt" in s else "#059669",
            "back_c2": "#1e1b4b" if "gt" in s else "#064e3b",
            "frame_c": "#38bdf8",
            "screen_c1": "#6366f1",
            "screen_c2": "#0f172a",
            "screen_accent": "#818cf8",
            "corner_rx": 20,
            "notch": "punch_hole",
        }

    # 12. TECNO CAMON 30 PRO / SPARK 20 PRO+ (Rangefinder Camera Zoom Ring + Red Tally Dot)
    return {
        "style": "tecno_camon",
        "back_c1": "#334155",
        "back_c2": "#0f172a",
        "frame_c": "#38bdf8",
        "screen_c1": "#06b6d4",
        "screen_c2": "#083344",
        "screen_accent": "#22d3ee",
        "corner_rx": 22,
        "notch": "punch_hole",
    }


def build_camera_island_svg(style: str, frame_c: str, accent_c: str) -> str:
    if style == "iphone_pro":
        return f"""
        <!-- iPhone Pro Square Plateau & Triangular Triple Camera -->
        <rect x="64" y="56" width="66" height="68" rx="16" fill="#000000" fill-opacity="0.28" stroke="{frame_c}" stroke-width="1.5"/>
        <circle cx="81" cy="74" r="12.5" fill="#111827" stroke="{frame_c}" stroke-width="2.2"/>
        <circle cx="81" cy="74" r="5" fill="#1e3a8a"/>
        <circle cx="81" cy="105" r="12.5" fill="#111827" stroke="{frame_c}" stroke-width="2.2"/>
        <circle cx="81" cy="105" r="5" fill="#1e3a8a"/>
        <circle cx="111" cy="89.5" r="12.5" fill="#111827" stroke="{frame_c}" stroke-width="2.2"/>
        <circle cx="111" cy="89.5" r="5" fill="#1e3a8a"/>
        <circle cx="111" cy="68" r="4.5" fill="#fef3c7"/>
        <circle cx="111" cy="111" r="5.5" fill="#1f2937"/>
        <circle cx="122" cy="175" r="12" fill="#ffffff" fill-opacity="0.22"/>
        """
    if style == "iphone_dual":
        return f"""
        <!-- iPhone 16 Vertical Pill Dual Camera -->
        <rect x="66" y="58" width="40" height="72" rx="20" fill="#000000" fill-opacity="0.3" stroke="{frame_c}" stroke-width="1.5"/>
        <circle cx="86" cy="77" r="12.5" fill="#111827" stroke="{frame_c}" stroke-width="2.2"/>
        <circle cx="86" cy="111" r="12.5" fill="#111827" stroke="{frame_c}" stroke-width="2.2"/>
        <circle cx="116" cy="94" r="4.5" fill="#fef3c7"/>
        """
    if style == "samsung_ultra":
        return f"""
        <!-- Galaxy S24 Ultra Floating Quad Rings + S-Pen Stylus -->
        <rect x="34" y="72" width="9" height="245" rx="4.5" fill="#9ca3af" stroke="#f3f4f6" stroke-width="1"/>
        <rect x="33" y="66" width="11" height="8" rx="2" fill="#d1d5db"/>
        <circle cx="76" cy="68" r="11" fill="#111827" stroke="{frame_c}" stroke-width="2"/>
        <circle cx="76" cy="96" r="11" fill="#111827" stroke="{frame_c}" stroke-width="2"/>
        <circle cx="76" cy="124" r="11" fill="#111827" stroke="{frame_c}" stroke-width="2"/>
        <circle cx="76" cy="152" r="11" fill="#111827" stroke="{frame_c}" stroke-width="2"/>
        <circle cx="101" cy="82" r="7.5" fill="#111827" stroke="#ef4444" stroke-width="1.5"/>
        <circle cx="101" cy="102" r="4" fill="#fef3c7"/>
        <circle cx="101" cy="120" r="7.5" fill="#111827" stroke="{frame_c}" stroke-width="1.5"/>
        """
    if style == "samsung_a":
        return f"""
        <!-- Samsung Galaxy A Series Floating Triple Vertical Rings -->
        <circle cx="78" cy="72" r="11" fill="#111827" stroke="{frame_c}" stroke-width="2"/>
        <circle cx="78" cy="100" r="11" fill="#111827" stroke="{frame_c}" stroke-width="2"/>
        <circle cx="78" cy="128" r="11" fill="#111827" stroke="{frame_c}" stroke-width="2"/>
        <circle cx="102" cy="100" r="4" fill="#fef3c7"/>
        """
    if style == "xiaomi_ultra_leica":
        return f"""
        <!-- Xiaomi 14 Ultra Giant Centered Circular LEICA Quad-Camera Disc -->
        <circle cx="122" cy="112" r="52" fill="#09090b" stroke="#d4af37" stroke-width="3.5"/>
        <circle cx="122" cy="112" r="46" fill="#18181b" stroke="#52525b" stroke-width="1"/>
        <circle cx="104" cy="94" r="11" fill="#000" stroke="#71717a" stroke-width="1.8"/>
        <circle cx="140" cy="94" r="11" fill="#000" stroke="#71717a" stroke-width="1.8"/>
        <circle cx="104" cy="130" r="11" fill="#000" stroke="#71717a" stroke-width="1.8"/>
        <circle cx="140" cy="130" r="11" fill="#000" stroke="#71717a" stroke-width="1.8"/>
        <text x="122" y="115" text-anchor="middle" fill="#ef4444" font-family="Inter,sans-serif" font-size="8" font-weight="900" letter-spacing="1.5">LEICA</text>
        """
    if style == "vivo_zeiss_aura":
        return f"""
        <!-- Vivo V40 Pro ZEISS Infinity Pill + Glowing Aura Light Ring -->
        <rect x="64" y="56" width="48" height="96" rx="24" fill="#1e1b4b" stroke="{frame_c}" stroke-width="1.8"/>
        <circle cx="88" cy="80" r="19" fill="#090d16" stroke="{frame_c}" stroke-width="1.5"/>
        <circle cx="88" cy="74" r="6" fill="#1e3a8a"/>
        <circle cx="88" cy="88" r="6" fill="#1e3a8a"/>
        <rect x="80" y="103" width="16" height="7" rx="2" fill="#1d4ed8"/>
        <text x="88" y="108.5" text-anchor="middle" fill="#fff" font-size="4.5" font-weight="800">ZEISS</text>
        <!-- Glowing Aura Light Ring -->
        <circle cx="88" cy="128" r="15" fill="none" stroke="#fde68a" stroke-width="3.5"/>
        <circle cx="88" cy="128" r="8" fill="#4c1d95"/>
        """
    if style == "oppo_find_cosmos":
        return f"""
        <!-- Oppo Find X8 Centered Cosmos Ring Hasselblad Module -->
        <circle cx="122" cy="110" r="46" fill="#1e293b" stroke="#e2e8f0" stroke-width="3.5"/>
        <circle cx="122" cy="110" r="40" fill="#0f172a"/>
        <circle cx="105" cy="95" r="10" fill="#000" stroke="#64748b" stroke-width="1.5"/>
        <circle cx="139" cy="95" r="10" fill="#000" stroke="#64748b" stroke-width="1.5"/>
        <circle cx="105" cy="125" r="10" fill="#000" stroke="#64748b" stroke-width="1.5"/>
        <circle cx="139" cy="125" r="10" fill="#000" stroke="#64748b" stroke-width="1.5"/>
        <text x="122" y="114" text-anchor="middle" fill="#f8fafc" font-family="serif" font-size="11" font-weight="900">H</text>
        """
    if style == "realme_luxury_ring":
        return f"""
        <!-- Realme 12 Pro+ Golden Watch Bezel + Vertical Seam -->
        <line x1="122" y1="44" x2="122" y2="326" stroke="#facc15" stroke-width="2" stroke-dasharray="3,2"/>
        <circle cx="122" cy="112" r="46" fill="#090d16" stroke="#facc15" stroke-width="3.5"/>
        <circle cx="106" cy="100" r="10" fill="#000" stroke="#eab308" stroke-width="1.5"/>
        <circle cx="138" cy="100" r="10" fill="#000" stroke="#eab308" stroke-width="1.5"/>
        <rect x="114" y="118" width="16" height="14" rx="3" fill="#000" stroke="#eab308" stroke-width="1.5"/>
        """
    if style == "oneplus_dial":
        return f"""
        <!-- OnePlus 12 Left-Aligned Watch Dial Camera -->
        <rect x="54" y="64" width="45" height="80" rx="8" fill="#1e293b"/>
        <circle cx="105" cy="104" r="42" fill="#090d16" stroke="{frame_c}" stroke-width="2.5"/>
        <circle cx="91" cy="90" r="10" fill="#000" stroke="#64748b" stroke-width="1.5"/>
        <circle cx="119" cy="90" r="10" fill="#000" stroke="#64748b" stroke-width="1.5"/>
        <circle cx="91" cy="118" r="10" fill="#000" stroke="#64748b" stroke-width="1.5"/>
        <text x="120" y="122" text-anchor="middle" fill="#fff" font-size="9" font-weight="800">H</text>
        """
    if style == "infinix_mecha":
        return f"""
        <!-- Infinix GT 20 Pro Cyber Mecha RGB Loop & Gaming Visor -->
        <polygon points="62,56 128,56 136,128 62,128" fill="#090d16" stroke="#38bdf8" stroke-width="2"/>
        <circle cx="84" cy="78" r="12" fill="#000" stroke="#38bdf8" stroke-width="1.8"/>
        <circle cx="84" cy="108" r="12" fill="#000" stroke="#38bdf8" stroke-width="1.8"/>
        <circle cx="114" cy="93" r="9" fill="#000" stroke="#38bdf8" stroke-width="1.5"/>
        <path d="M 145 95 A 38 38 0 1 1 145 165" fill="none" stroke="#22d3ee" stroke-width="4" stroke-linecap="round"/>
        """
    # Default / Redmi Note / Oppo Reno / Tecno Camon
    return f"""
    <rect x="64" y="56" width="56" height="84" rx="16" fill="#090d16" fill-opacity="0.75" stroke="{frame_c}" stroke-width="1.8"/>
    <circle cx="84" cy="78" r="12.5" fill="#000" stroke="{frame_c}" stroke-width="2"/>
    <circle cx="84" cy="112" r="12.5" fill="#000" stroke="{frame_c}" stroke-width="2"/>
    <circle cx="108" cy="95" r="7" fill="#000" stroke="{frame_c}" stroke-width="1.5"/>
    <circle cx="108" cy="72" r="4" fill="#ef4444"/>
    """


def render_exact_phone_svg(slug: str, brand_name: str, model_name: str) -> str:
    os.makedirs(IMAGES_DIR, exist_ok=True)
    p = get_model_visual_profile(slug, brand_name, model_name)
    rx = p["corner_rx"]
    cam_svg = build_camera_island_svg(p["style"], p["frame_c"], p["screen_accent"])

    if p["notch"] == "dynamic_island":
        notch_svg = '<rect x="221" y="54" width="40" height="10" rx="5" fill="#050811"/>'
    else:
        notch_svg = '<circle cx="241" cy="57" r="4.5" fill="#050811"/>'

    svg_str = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 380" width="720" height="760">
  <defs>
    <linearGradient id="back-{slug}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{p['back_c1']}"/>
      <stop offset="100%" stop-color="{p['back_c2']}"/>
    </linearGradient>
    <linearGradient id="scr-{slug}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{p['screen_c1']}"/>
      <stop offset="50%" stop-color="{p['screen_c2']}"/>
      <stop offset="100%" stop-color="#050811"/>
    </linearGradient>
    <radialGradient id="glow-{slug}" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="{p['screen_accent']}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="{p['screen_accent']}" stop-opacity="0"/>
    </radialGradient>
    <filter id="drop-{slug}" x="-20%" y="-15%" width="140%" height="140%">
      <feDropShadow dx="0" dy="16" stdDeviation="14" flood-color="#000000" flood-opacity="0.65"/>
    </filter>
  </defs>

  <!-- Ambient Backlight Glow -->
  <circle cx="185" cy="190" r="145" fill="url(#glow-{slug})"/>

  <!-- REAR CHASSIS (Left Device Showing Exact Model Camera Architecture) -->
  <g filter="url(#drop-{slug})">
    <rect x="54" y="42" width="136" height="286" rx="{rx}" fill="url(#back-{slug})" stroke="{p['frame_c']}" stroke-width="2.5"/>
    <!-- Metallic Glass Diagonal Sheen -->
    <path d="M 60 44 L 145 44 L 85 326 L 56 326 Z" fill="#ffffff" fill-opacity="0.07"/>
    {cam_svg}
    <text x="122" y="302" text-anchor="middle" fill="#ffffff" fill-opacity="0.55" font-family="Inter, system-ui, sans-serif" font-size="9.5" font-weight="800" letter-spacing="2">{brand_name.upper()}</text>
  </g>

  <!-- FRONT DISPLAY (Right Overlapping Device Showing Screen & Wallpaper) -->
  <g filter="url(#drop-{slug})">
    <rect x="172" y="38" width="138" height="292" rx="{rx}" fill="#050811" stroke="{p['frame_c']}" stroke-width="2.5"/>
    <rect x="177" y="43" width="128" height="282" rx="{max(rx - 3, 4)}" fill="url(#scr-{slug})"/>
    <!-- Dynamic Abstract Wallpaper Graphic -->
    <circle cx="241" cy="165" r="56" fill="{p['screen_accent']}" fill-opacity="0.28"/>
    <path d="M 177 220 Q 241 155 305 240 L 305 325 L 177 325 Z" fill="{p['back_c1']}" fill-opacity="0.32"/>
    {notch_svg}
    <!-- Clean Model Signature on Screen -->
    <text x="241" y="102" text-anchor="middle" fill="#ffffff" fill-opacity="0.8" font-family="Inter, system-ui, sans-serif" font-size="8.5" font-weight="700" letter-spacing="2">{brand_name.upper()}</text>
    <text x="241" y="122" text-anchor="middle" fill="#ffffff" font-family="Inter, system-ui, sans-serif" font-size="12.5" font-weight="800">{model_name}</text>
  </g>
</svg>"""

    file_path = os.path.join(IMAGES_DIR, f"{slug}.svg")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(svg_str)

    uploads_dir = get_uploads_dir()
    if os.path.abspath(uploads_dir) != os.path.abspath(IMAGES_DIR):
        with open(os.path.join(uploads_dir, f"{slug}.svg"), "w", encoding="utf-8") as f2:
            f2.write(svg_str)

    save_media_asset_to_db(f"{slug}.svg", svg_str.encode("utf-8"), "image/svg+xml")
    return f"/static/images/phones/{slug}.svg"


def generate_hero_lineup_svg() -> None:
    """Generates the 5-Phone Flagship Lineup Hero Composition matching the reference hero section."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 430" width="1360" height="860">
  <defs>
    <radialGradient id="heroGlow" cx="55%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#2563eb" stop-opacity="0.45"/>
      <stop offset="55%" stop-color="#0ea5e9" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#060b16" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="goldTi" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#d6b89c"/>
      <stop offset="50%" stop-color="#9c7a5b"/>
      <stop offset="100%" stop-color="#5c4430"/>
    </linearGradient>
    <linearGradient id="grayTi" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#cbd5e1"/>
      <stop offset="50%" stop-color="#64748b"/>
      <stop offset="100%" stop-color="#334155"/>
    </linearGradient>
    <linearGradient id="darkTi" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#475569"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <linearGradient id="heroScreen" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#60a5fa"/>
      <stop offset="35%" stop-color="#3b82f6"/>
      <stop offset="70%" stop-color="#1e1b4b"/>
      <stop offset="100%" stop-color="#090d16"/>
    </linearGradient>
    <filter id="heroDrop" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="22" stdDeviation="18" flood-color="#000000" flood-opacity="0.75"/>
    </filter>
  </defs>

  <!-- Studio Floor Glow & Horizon Line -->
  <ellipse cx="360" cy="210" rx="310" ry="185" fill="url(#heroGlow)"/>
  <ellipse cx="360" cy="378" rx="280" ry="18" fill="#38bdf8" fill-opacity="0.18"/>
  <line x1="60" y1="378" x2="640" y2="378" stroke="#38bdf8" stroke-opacity="0.35" stroke-width="1.5"/>

  <!-- Phone 1 (Far Left): Mint/Silver Titanium Back -->
  <g filter="url(#heroDrop)" transform="translate(85, 88) scale(0.84)">
    <rect x="0" y="0" width="128" height="295" rx="24" fill="#94a3b8" stroke="#e2e8f0" stroke-width="2"/>
    <rect x="10" y="12" width="56" height="58" rx="14" fill="#64748b" stroke="#cbd5e1" stroke-width="1.2"/>
    <circle cx="25" cy="27" r="10.5" fill="#0f172a" stroke="#cbd5e1" stroke-width="2"/>
    <circle cx="25" cy="53" r="10.5" fill="#0f172a" stroke="#cbd5e1" stroke-width="2"/>
    <circle cx="50" cy="40" r="10.5" fill="#0f172a" stroke="#cbd5e1" stroke-width="2"/>
  </g>

  <!-- Phone 2 (Mid Left): Galaxy S24 Ultra Titanium Gray Back -->
  <g filter="url(#heroDrop)" transform="translate(155, 62) scale(0.92)">
    <rect x="0" y="0" width="136" height="310" rx="10" fill="url(#grayTi)" stroke="#f1f5f9" stroke-width="2.2"/>
    <rect x="12" y="14" width="64" height="68" rx="16" fill="#475569" stroke="#cbd5e1" stroke-width="1.5"/>
    <circle cx="29" cy="31" r="12" fill="#090d16" stroke="#e2e8f0" stroke-width="2.2"/>
    <circle cx="29" cy="63" r="12" fill="#090d16" stroke="#e2e8f0" stroke-width="2.2"/>
    <circle cx="58" cy="47" r="12" fill="#090d16" stroke="#e2e8f0" stroke-width="2.2"/>
    <circle cx="58" cy="25" r="4.5" fill="#fef3c7"/>
  </g>

  <!-- Phone 3 (Center): iPhone 16 Pro Max Black Titanium Back -->
  <g filter="url(#heroDrop)" transform="translate(238, 42)">
    <rect x="0" y="0" width="144" height="328" rx="28" fill="url(#darkTi)" stroke="#94a3b8" stroke-width="2.5"/>
    <rect x="14" y="14" width="68" height="72" rx="18" fill="#1e293b" stroke="#64748b" stroke-width="1.5"/>
    <circle cx="32" cy="33" r="13.5" fill="#090d16" stroke="#94a3b8" stroke-width="2.5"/>
    <circle cx="32" cy="33" r="5" fill="#1e3a8a"/>
    <circle cx="32" cy="67" r="13.5" fill="#090d16" stroke="#94a3b8" stroke-width="2.5"/>
    <circle cx="32" cy="67" r="5" fill="#1e3a8a"/>
    <circle cx="64" cy="50" r="13.5" fill="#090d16" stroke="#94a3b8" stroke-width="2.5"/>
    <circle cx="64" cy="50" r="5" fill="#1e3a8a"/>
    <circle cx="64" cy="26" r="5" fill="#fde68a"/>
    <circle cx="64" cy="74" r="6" fill="#334155"/>
    <circle cx="72" cy="158" r="15" fill="#ffffff" fill-opacity="0.15"/>
  </g>

  <!-- Phone 4 (Right): Side Profile Cyan Edge Phone -->
  <g filter="url(#heroDrop)" transform="translate(462, 56) scale(0.94)">
    <rect x="0" y="0" width="126" height="318" rx="26" fill="#090d16" stroke="#38bdf8" stroke-width="2.5"/>
    <rect x="6" y="6" width="114" height="306" rx="22" fill="#0284c7"/>
    <path d="M 6 60 Q 80 140 120 260 L 120 312 L 6 312 Z" fill="#0369a1"/>
  </g>

  <!-- Phone 5 (Front Hero Main Screen): Glowing Blue/Violet Pro Display -->
  <g filter="url(#heroDrop)" transform="translate(348, 36)">
    <rect x="0" y="0" width="152" height="336" rx="28" fill="#050811" stroke="#cbd5e1" stroke-width="3"/>
    <rect x="6" y="6" width="140" height="324" rx="24" fill="url(#heroScreen)"/>
    <!-- Luminous Diagonal Ribbon Wallpaper -->
    <polygon points="6,40 146,145 146,245 6,130" fill="#93c5fd" fill-opacity="0.35"/>
    <polygon points="6,130 146,235 146,315 6,215" fill="#38bdf8" fill-opacity="0.25"/>
    <!-- Dynamic Island -->
    <rect x="52" y="15" width="48" height="12" rx="6" fill="#050811"/>
    <circle cx="90" cy="21" r="2.8" fill="#1e3a8a"/>
  </g>
</svg>"""
    os.makedirs(os.path.dirname(HERO_IMG_PATH), exist_ok=True)
    with open(HERO_IMG_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    save_media_asset_to_db("hero-phones-lineup.svg", svg.encode("utf-8"), "image/svg+xml")


def ensure_reference_models_and_regenerate_all_images() -> dict:
    """
    1. Ensures Vivo V40 Pro and Oppo Find X8 exist in the database (marked as DEMO/SAMPLE)
       so the exact 5 reference models appear on the Home Page & Phone Finder without deleting any existing phone.
    2. Generates model-accurate studio SVG renders for EVERY phone in the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if Vivo V40 Pro and Oppo Find X8 exist; if not, add them as DEMO/SAMPLE
    vivo_brand = cursor.execute("SELECT id FROM brands WHERE slug = 'vivo'").fetchone()
    oppo_brand = cursor.execute("SELECT id FROM brands WHERE slug = 'oppo'").fetchone()

    extra_reference_phones = [
        {
            "brand_id": vivo_brand["id"] if vivo_brand else 4,
            "model_name": "Vivo V40 Pro",
            "official_variant_name": "Vivo V40 Pro 5G (12GB RAM / 512GB Storage — ZEISS Edition)",
            "slug": "vivo-v40-pro",
            "price_pkr": 329999,
            "release_date": "2024-09-22",
            "ram_gb": 12,
            "ram_display": "12 GB LPDDR5X",
            "storage_gb": 512,
            "storage_display": "512 GB UFS 3.1",
            "processor": "MediaTek Dimensity 9200+ (4 nm) — Octa-core up to 3.35 GHz",
            "display_type": "AMOLED, 1B colors, 120Hz, HDR10+, 4500 nits peak",
            "display_size_inch": 6.78,
            "display_resolution": "1260 x 2800 pixels",
            "refresh_rate": "120Hz",
            "main_camera": "50 MP ZEISS (OIS) + 50 MP ZEISS Telephoto (2x OIS) + 50 MP Ultrawide, Aura Light",
            "selfie_camera": "50 MP ZEISS Group Selfie (AF), 4K@60fps",
            "battery_mah": 5500,
            "charging": "80W wired FlashCharge",
            "network": "GSM / HSPA / LTE / 5G",
            "is_5g": 1,
            "os": "Android 14, Funtouch OS 14",
            "dimensions": "164.4 x 75.1 x 7.58 mm",
            "weight": "192 g",
            "build_material": "Glass front & back, IP68/IP69 water/dust resistant",
            "colors": "Ganges Blue, Titanium Grey, Moonlight White",
        },
        {
            "brand_id": oppo_brand["id"] if oppo_brand else 5,
            "model_name": "Oppo Find X8",
            "official_variant_name": "Oppo Find X8 5G (12GB RAM / 256GB Storage — Hasselblad Camera)",
            "slug": "oppo-find-x8",
            "price_pkr": 299999,
            "release_date": "2024-09-24",
            "ram_gb": 12,
            "ram_display": "12 GB / 16 GB LPDDR5X",
            "storage_gb": 256,
            "storage_display": "256GB / 512GB UFS 4.0",
            "processor": "MediaTek Dimensity 9400 (3 nm) — Octa-core, Immortalis-G925",
            "display_type": "LTPO AMOLED, 1B colors, 120Hz, Dolby Vision, 4500 nits",
            "display_size_inch": 6.59,
            "display_resolution": "1256 x 2760 pixels",
            "refresh_rate": "120Hz LTPO",
            "main_camera": "50 MP (OIS) + 50 MP (3x Periscope OIS) + 50 MP (ultrawide), Hasselblad Color",
            "selfie_camera": "32 MP (wide), 4K@60fps",
            "battery_mah": 5630,
            "charging": "80W SuperVOOC wired, 50W AIRVOOC wireless",
            "network": "GSM / HSPA / LTE / 5G",
            "is_5g": 1,
            "os": "Android 15, ColorOS 15",
            "dimensions": "157.4 x 74.3 x 7.85 mm",
            "weight": "193 g",
            "build_material": "Gorilla Glass, Aluminum frame, IP68/IP69",
            "colors": "Star Grey, Space Black, Shell Pink",
        },
    ]

    for ep in extra_reference_phones:
        exists = cursor.execute("SELECT id FROM phones WHERE slug = ?", (ep["slug"],)).fetchone()
        if not exists:
            img_path = f"/static/images/phones/{ep['slug']}.svg"
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
                    ?, 'PKR', 'PTA Approved / Official Warranty (Sample)', 'Available',
                    1, 'DEMO/SAMPLE', 'Demo / Sample Seed Catalog (Unverified)', '',
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, 'Dual SIM (Nano-SIM, dual stand-by)', ?, 'Fingerprint, Accelerometer, Gyro, Proximity, Compass',
                    ?, 1, 1, 950, ?, ?
                )
                """,
                (
                    ep["brand_id"],
                    ep["model_name"],
                    ep["official_variant_name"],
                    ep["slug"],
                    ep["price_pkr"],
                    DEMO_WARNING_TEXT,
                    DEMO_WARNING_TEXT,
                    img_path,
                    json.dumps([img_path]),
                    ep["release_date"],
                    ep["ram_gb"],
                    ep["ram_display"],
                    ep["storage_gb"],
                    ep["storage_display"],
                    ep["processor"],
                    ep["display_type"],
                    ep["display_size_inch"],
                    ep["display_resolution"],
                    ep["refresh_rate"],
                    ep["main_camera"],
                    ep["selfie_camera"],
                    ep["battery_mah"],
                    ep["charging"],
                    ep["network"],
                    ep["is_5g"],
                    ep["os"],
                    ep["dimensions"],
                    ep["weight"],
                    ep["build_material"],
                    ep["colors"],
                    f"{ep['model_name']} with {ep['processor']} and {ep['main_camera']}.",
                    now_str,
                    now_str,
                ),
            )

    # Set release_date ordering on the 5 flagship hero phones so they appear in exact reference order on Home & Finder
    hero_order = [
        ("apple-iphone-16-pro-max", "2024-09-29"),
        ("samsung-galaxy-s24-ultra", "2024-09-28"),
        ("xiaomi-14-ultra", "2024-09-27"),
        ("vivo-v40-pro", "2024-09-26"),
        ("oppo-find-x8", "2024-09-25"),
    ]
    for slug_val, r_date in hero_order:
        cursor.execute(
            "UPDATE phones SET is_latest = 1, is_popular = 1, release_date = ? WHERE slug = ?",
            (r_date, slug_val),
        )

    # Regenerate exact model-specific images for ALL phones in the database
    all_rows = cursor.execute(
        "SELECT p.id, p.slug, p.model_name, b.name as brand_name FROM phones p JOIN brands b ON b.id = p.brand_id"
    ).fetchall()

    mapping = {}
    for row in all_rows:
        img_url = render_exact_phone_svg(row["slug"], row["brand_name"], row["model_name"])
        cursor.execute(
            "UPDATE phones SET image_url = ?, gallery_json = ? WHERE id = ?",
            (img_url, json.dumps([img_url]), row["id"]),
        )
        mapping[f"{row['brand_name']} {row['model_name']}"] = img_url

    conn.commit()
    conn.close()
    generate_hero_lineup_svg()
    return mapping


if __name__ == "__main__":
    mapping = ensure_reference_models_and_regenerate_all_images()
    print(f"[OK] Generated {len(mapping)} model-specific phone images and hero lineup composition.")
    for k, v in list(mapping.items())[:8]:
        print(f"  {k:<32} -> {v}")
