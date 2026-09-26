import json
import os
from datetime import datetime
from database import get_db_connection, init_db, BASE_DIR, DEMO_WARNING_TEXT
from seed_data import generate_phone_svg


ORPHAN_TEST_SVGS = [
    "samsung-galaxy-s24-fe-pk-edition-1548.svg",
    "samsung-galaxy-s24-fe-pk-edition-1608.svg",
    "samsung-galaxy-s24-fe-pk-edition-1703.svg",
    "samsung-galaxy-s24-fe-pk-edition-1815.svg",
    "samsung-galaxy-s24-fe-pk-edition.svg",
    "samsung-galaxy-s25-ultra-test-edition.svg",
]


# 14 Existing Phones Verified with Current Pakistan Market Prices & Official Distributor Sources
VERIFIED_EXISTING_UPDATES = {
    1: {
        "price_pkr": 524999,
        "official_variant_name": "A3296 (8GB RAM / 256GB Storage — Mercantile Official PTA Approved)",
        "pta_status": "PTA Approved / Mercantile Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 1,
        "is_popular": 1,
        "source_name": "Mercantile Apple Authorized Distributor PK / PriceOye",
        "source_url": "https://mercantile.com.pk/",
        "verification_notes": "Verified official Mercantile PTA-approved 256GB retail pricing and specifications in Pakistan.",
    },
    2: {
        "price_pkr": 339999,
        "official_variant_name": "A3287 (8GB RAM / 128GB Storage — Mercantile Official PTA Approved)",
        "pta_status": "PTA Approved / Mercantile Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 1,
        "is_popular": 1,
        "source_name": "Mercantile Apple Authorized Distributor PK / PriceOye",
        "source_url": "https://mercantile.com.pk/",
        "verification_notes": "Verified official Mercantile PTA-approved 128GB retail pricing and specifications in Pakistan.",
    },
    4: {
        "price_pkr": 419999,
        "official_variant_name": "SM-S928B/DS (12GB RAM / 256GB Storage — Samsung PK Official PTA)",
        "pta_status": "PTA Approved / Samsung Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 0,
        "is_popular": 1,
        "source_name": "Samsung Pakistan Official Store",
        "source_url": "https://www.samsung.com/pk/smartphones/galaxy-s/",
        "verification_notes": "Verified official Samsung Pakistan PTA-approved retail price (updated from Rs. 434,999 to Rs. 419,999 following Galaxy S25 Ultra launch).",
    },
    5: {
        "price_pkr": 129999,
        "official_variant_name": "SM-A556E/DS (8GB RAM / 256GB Storage — Samsung PK Official PTA)",
        "pta_status": "PTA Approved / Samsung Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "OLDER_AVAILABLE",
        "is_latest": 0,
        "is_popular": 1,
        "source_name": "Samsung Pakistan Official Store",
        "source_url": "https://www.samsung.com/pk/smartphones/galaxy-a/",
        "verification_notes": "Verified Samsung Pakistan retail price (Rs. 129,999); remains actively sold alongside the newer Galaxy A56 5G.",
    },
    8: {
        "price_pkr": 139999,
        "official_variant_name": "23090RA98G (12GB RAM / 512GB Storage — Xiaomi PK Official PTA)",
        "pta_status": "PTA Approved / MiStore Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "OLDER_AVAILABLE",
        "is_latest": 0,
        "is_popular": 1,
        "source_name": "MiStore Pakistan (Xiaomi Official Distributor)",
        "source_url": "https://mistore.pk/",
        "verification_notes": "Verified MiStore Pakistan 12GB/512GB official price (Rs. 139,999); remains available alongside Redmi Note 14 Pro+ 5G.",
    },
    10: {
        "price_pkr": 139999,
        "official_variant_name": "V2348 (12GB RAM / 256GB Storage — Vivo Pakistan Official PTA)",
        "pta_status": "PTA Approved / Vivo Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 1,
        "is_popular": 1,
        "source_name": "Vivo Pakistan Official",
        "source_url": "https://www.vivo.com/pk",
        "verification_notes": "Verified Vivo Pakistan ZEISS portrait flagship V40 5G (12GB/256GB) official retail price of Rs. 139,999.",
    },
    12: {
        "price_pkr": 56999,
        "official_variant_name": "V2327 (8GB RAM / 256GB Storage — Vivo Pakistan Official PTA)",
        "pta_status": "PTA Approved / Vivo Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "OLDER_AVAILABLE",
        "is_latest": 0,
        "is_popular": 0,
        "source_name": "Vivo Pakistan Official",
        "source_url": "https://www.vivo.com/pk",
        "verification_notes": "Verified Vivo Pakistan Y100 4G (8GB/256GB) current retail price (updated from Rs. 57,999 to Rs. 56,999).",
    },
    13: {
        "price_pkr": 159999,
        "official_variant_name": "CPH2625 (12GB RAM / 256GB Storage — Oppo Pakistan Official PTA)",
        "pta_status": "PTA Approved / Oppo Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 1,
        "is_popular": 1,
        "source_name": "Oppo Pakistan Official",
        "source_url": "https://www.oppo.com/pk/",
        "verification_notes": "Verified Oppo Pakistan official retail MSRP of Rs. 159,999 for Oppo Reno 12 5G (12GB/256GB).",
    },
    15: {
        "price_pkr": 54999,
        "official_variant_name": "CPH2631 (8GB RAM / 128GB Storage — Oppo Pakistan Official PTA)",
        "pta_status": "PTA Approved / Oppo Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 0,
        "is_popular": 0,
        "source_name": "Oppo Pakistan Official",
        "source_url": "https://www.oppo.com/pk/",
        "verification_notes": "Verified Oppo Pakistan official retail price of Rs. 54,999 for Oppo A60 (8GB/128GB).",
    },
    19: {
        "price_pkr": 149999,
        "official_variant_name": "RMX3851 (12GB RAM / 256GB Storage — Realme Pakistan Official PTA)",
        "pta_status": "PTA Approved / Realme Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 1,
        "is_popular": 1,
        "source_name": "Realme Pakistan Official",
        "source_url": "https://www.realme.com/pk/",
        "verification_notes": "Verified Realme Pakistan flagship killer Realme GT 6 5G (Snapdragon 8s Gen 3) official retail price.",
    },
    22: {
        "price_pkr": 99999,
        "official_variant_name": "X6871 (12GB RAM / 256GB Storage — Infinix Pakistan Official PTA)",
        "pta_status": "PTA Approved / Infinix Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 1,
        "is_popular": 1,
        "source_name": "Infinix Mobility Pakistan",
        "source_url": "https://pk.infinixmobility.com/",
        "verification_notes": "Verified Infinix Mobility Pakistan official gaming smartphone GT 20 Pro (Dimensity 8200 Ultimate) price of Rs. 99,999.",
    },
    23: {
        "price_pkr": 74999,
        "official_variant_name": "X6850 (12GB RAM / 256GB Storage — Infinix Pakistan Official PTA)",
        "pta_status": "PTA Approved / Infinix Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 0,
        "is_popular": 1,
        "source_name": "Infinix Mobility Pakistan",
        "source_url": "https://pk.infinixmobility.com/",
        "verification_notes": "Verified Infinix Pakistan Note 40 Pro (12GB/256GB) current retail price (updated from Rs. 69,999 to Rs. 74,999).",
    },
    25: {
        "price_pkr": 99999,
        "official_variant_name": "CL8 (12GB RAM / 512GB Storage — Tecno Pakistan Official PTA)",
        "pta_status": "PTA Approved / Tecno Mobile Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 1,
        "is_popular": 1,
        "source_name": "Tecno Mobile Pakistan",
        "source_url": "https://www.tecno-mobile.com/pk/",
        "verification_notes": "Verified Tecno Mobile Pakistan Camon 30 Pro 5G (Dimensity 8200 Ultimate, 12GB/512GB) official retail price.",
    },
    26: {
        "price_pkr": 57999,
        "official_variant_name": "CL6 (8GB RAM / 256GB Storage — Tecno Pakistan Official PTA)",
        "pta_status": "PTA Approved / Tecno Mobile Pakistan Official Warranty",
        "availability": "Available",
        "data_status": "VERIFIED",
        "is_demo_data": 0,
        "catalog_status": "CURRENT",
        "is_latest": 0,
        "is_popular": 0,
        "source_name": "Tecno Mobile Pakistan",
        "source_url": "https://www.tecno-mobile.com/pk/",
        "verification_notes": "Verified Tecno Mobile Pakistan Camon 30 (8GB/256GB) official retail price of Rs. 57,999.",
    },
}


# 15 Existing Phones Preserved as DEMO/SAMPLE (Unverified / Discontinued / Import-Variable)
DEMO_EXISTING_STATUS_UPDATES = {
    3: {"catalog_status": "OUTDATED", "availability": "Discontinued", "is_latest": 0},   # iPhone 15 Pro
    6: {"catalog_status": "OUTDATED", "availability": "Available", "is_latest": 0},      # Galaxy A15 (succeeded by A16)
    7: {"catalog_status": "OLDER_AVAILABLE", "availability": "Available", "is_latest": 0}, # Xiaomi 14 Ultra
    9: {"catalog_status": "OLDER_AVAILABLE", "availability": "Available", "is_latest": 0}, # Redmi Note 13
    11: {"catalog_status": "OUTDATED", "availability": "Available", "is_latest": 0},     # Vivo V30e 5G (succeeded by V40e)
    14: {"catalog_status": "OUTDATED", "availability": "Available", "is_latest": 0},     # Oppo Reno 11F 5G (succeeded by Reno 12F)
    16: {"catalog_status": "NEEDS_REVIEW", "availability": "Available", "is_latest": 0}, # OnePlus 12 5G (import PTA varies)
    17: {"catalog_status": "NEEDS_REVIEW", "availability": "Available", "is_latest": 0}, # OnePlus Nord 4 5G
    18: {"catalog_status": "OLDER_AVAILABLE", "availability": "Available", "is_latest": 0}, # OnePlus Nord CE 4 Lite
    20: {"catalog_status": "OLDER_AVAILABLE", "availability": "Available", "is_latest": 0}, # Realme 12 Pro+ 5G
    21: {"catalog_status": "OUTDATED", "availability": "Available", "is_latest": 0},     # Realme C67
    24: {"catalog_status": "OUTDATED", "availability": "Available", "is_latest": 0},     # Infinix Hot 40 Pro (succeeded by Hot 50 Pro+)
    27: {"catalog_status": "OUTDATED", "availability": "Available", "is_latest": 0},     # Tecno Spark 20 Pro+ (succeeded by Spark 30 Pro)
    34: {"catalog_status": "NEEDS_REVIEW", "availability": "Available", "is_latest": 0}, # Vivo V40 Pro
    35: {"catalog_status": "NEEDS_REVIEW", "availability": "Available", "is_latest": 0}, # Oppo Find X8
}


# 10 New Researched & Verified Current Pakistan Smartphones
NEW_CURRENT_PHONES = [
    {
        "brand_slug": "samsung",
        "model_name": "Galaxy S25 Ultra",
        "official_variant_name": "SM-S938B/DS (12GB RAM / 256GB Storage — Samsung PK Official PTA)",
        "slug": "samsung-galaxy-s25-ultra",
        "price_pkr": 459999,
        "release_date": "2025-02-07",
        "ram_gb": 12,
        "ram_display": "12 GB LPDDR5X",
        "storage_gb": 256,
        "storage_display": "256 GB UFS 4.0",
        "processor": "Qualcomm Snapdragon 8 Elite for Galaxy (3 nm)",
        "display_type": "Dynamic LTPO AMOLED 2X, 120Hz, HDR10+, 2600 nits",
        "display_size_inch": 6.9,
        "display_resolution": "1440 x 3120 pixels (QHD+)",
        "refresh_rate": "120Hz",
        "main_camera": "200 MP (wide, OIS) + 50 MP (5x periscope telephoto) + 10 MP (3x telephoto) + 50 MP (ultrawide)",
        "selfie_camera": "12 MP (Dual Pixel PDAF, 4K@60fps)",
        "battery_mah": 5000,
        "charging": "45W wired PD3.0, 25W Qi2 wireless, 4.5W reverse wireless",
        "network": "GSM / HSPA / LTE / 5G Sub-6",
        "is_5g": 1,
        "os": "Android 15, One UI 7",
        "dimensions": "162.8 x 77.6 x 8.2 mm",
        "weight": "218 g",
        "build_material": "Gorilla Armor 2 front/back, Grade 5 Titanium frame, IP68",
        "colors": "Titanium Silverblue, Titanium Black, Titanium Whitesilver, Titanium Gray",
        "source_name": "Samsung Pakistan Official Store",
        "source_url": "https://www.samsung.com/pk/smartphones/galaxy-s25-ultra/",
        "verification_notes": "Verified Samsung Pakistan flagship Galaxy S25 Ultra (Snapdragon 8 Elite, 12GB/256GB) official specifications and PKR price.",
        "is_latest": 1,
        "is_popular": 1,
        "variants": [
            {"variant_label": "12GB RAM / 256GB Storage (Official PTA)", "ram_gb": 12, "storage_gb": 256, "price_pkr": 459999},
            {"variant_label": "12GB RAM / 512GB Storage (Official PTA)", "ram_gb": 12, "storage_gb": 512, "price_pkr": 499999},
        ],
    },
    {
        "brand_slug": "samsung",
        "model_name": "Galaxy A56 5G",
        "official_variant_name": "SM-A566B/DS (8GB RAM / 256GB Storage — Samsung PK Official PTA)",
        "slug": "samsung-galaxy-a56-5g",
        "price_pkr": 126999,
        "release_date": "2025-03-19",
        "ram_gb": 8,
        "ram_display": "8 GB LPDDR5",
        "storage_gb": 256,
        "storage_display": "256 GB UFS 3.1",
        "processor": "Samsung Exynos 1580 (4 nm) — Xclipse 540 GPU",
        "display_type": "Super AMOLED, 120Hz, HDR10+, 1900 nits (peak)",
        "display_size_inch": 6.7,
        "display_resolution": "1080 x 2340 pixels (FHD+)",
        "refresh_rate": "120Hz",
        "main_camera": "50 MP (wide, OIS) + 12 MP (ultrawide) + 5 MP (macro)",
        "selfie_camera": "12 MP (wide, 10-bit HDR video)",
        "battery_mah": 5000,
        "charging": "45W Super Fast Charging 2.0",
        "network": "GSM / HSPA / LTE / 5G",
        "is_5g": 1,
        "os": "Android 15, One UI 7 (6 years OS upgrades)",
        "dimensions": "162.2 x 77.5 x 7.4 mm",
        "weight": "198 g",
        "build_material": "Gorilla Glass Victus+ front/back, Aluminum frame, IP67",
        "colors": "Awesome Lightgray, Awesome Graphite, Awesome Olive, Awesome Pink",
        "source_name": "Samsung Pakistan Official Store",
        "source_url": "https://www.samsung.com/pk/smartphones/galaxy-a/",
        "verification_notes": "Verified Samsung Pakistan Galaxy A56 5G (Exynos 1580, 45W charging, 8GB/256GB) official specifications and PKR price.",
        "is_latest": 1,
        "is_popular": 1,
        "variants": [
            {"variant_label": "8GB RAM / 256GB Storage", "ram_gb": 8, "storage_gb": 256, "price_pkr": 126999},
        ],
    },
    {
        "brand_slug": "samsung",
        "model_name": "Galaxy A16",
        "official_variant_name": "SM-A165F/DS (6GB RAM / 128GB Storage — Samsung PK Official PTA)",
        "slug": "samsung-galaxy-a16",
        "price_pkr": 55999,
        "release_date": "2024-11-15",
        "ram_gb": 6,
        "ram_display": "6 GB LPDDR4X",
        "storage_gb": 128,
        "storage_display": "128 GB (microSDXC slot)",
        "processor": "MediaTek Helio G99 (6 nm)",
        "display_type": "Super AMOLED, 90Hz, 800 nits",
        "display_size_inch": 6.7,
        "display_resolution": "1080 x 2340 pixels (FHD+)",
        "refresh_rate": "90Hz",
        "main_camera": "50 MP (wide) + 5 MP (ultrawide) + 2 MP (macro)",
        "selfie_camera": "13 MP (wide, 1080p@30fps)",
        "battery_mah": 5000,
        "charging": "25W wired fast charging",
        "network": "2G / 3G / 4G LTE",
        "is_5g": 0,
        "os": "Android 14, One UI 6.1 (6 major OS upgrades)",
        "dimensions": "164.4 x 77.9 x 7.9 mm",
        "weight": "200 g",
        "build_material": "Glass front, plastic back/frame, IP54 dust/splash resistant",
        "colors": "Midnight Blue, Light Gray, Light Green",
        "source_name": "Samsung Pakistan Official Store",
        "source_url": "https://www.samsung.com/pk/smartphones/galaxy-a/",
        "verification_notes": "Verified Samsung Pakistan Galaxy A16 (6.7-inch Super AMOLED, IP54, 6GB/128GB) official Pakistan retail price.",
        "is_latest": 1,
        "is_popular": 1,
        "variants": [
            {"variant_label": "6GB RAM / 128GB Storage", "ram_gb": 6, "storage_gb": 128, "price_pkr": 55999},
            {"variant_label": "8GB RAM / 256GB Storage", "ram_gb": 8, "storage_gb": 256, "price_pkr": 64999},
        ],
    },
    {
        "brand_slug": "xiaomi",
        "model_name": "Xiaomi 14T Pro",
        "official_variant_name": "2407FPN8EG (12GB RAM / 512GB Storage — MiStore PK Official PTA)",
        "slug": "xiaomi-14t-pro",
        "price_pkr": 229999,
        "release_date": "2024-10-10",
        "ram_gb": 12,
        "ram_display": "12 GB LPDDR5X",
        "storage_gb": 512,
        "storage_display": "512 GB UFS 4.0",
        "processor": "MediaTek Dimensity 9300+ (4 nm)",
        "display_type": "AMOLED, 144Hz, Dolby Vision, HDR10+, 4000 nits (peak)",
        "display_size_inch": 6.67,
        "display_resolution": "1220 x 2712 pixels (1.5K)",
        "refresh_rate": "144Hz",
        "main_camera": "50 MP Leica Light Fusion 900 (OIS) + 50 MP (2.6x Leica telephoto) + 12 MP (ultrawide)",
        "selfie_camera": "32 MP (wide, 4K@30fps)",
        "battery_mah": 5000,
        "charging": "120W HyperCharge wired (100% in 19 min), 50W wireless HyperCharge",
        "network": "GSM / HSPA / LTE / 5G",
        "is_5g": 1,
        "os": "Android 14, Xiaomi HyperOS",
        "dimensions": "160.4 x 75.1 x 8.4 mm",
        "weight": "209 g",
        "build_material": "Gorilla Glass 5, High-strength Aluminum alloy frame, IP68",
        "colors": "Titan Gray, Titan Blue, Titan Black",
        "source_name": "MiStore Pakistan (Xiaomi Official Distributor)",
        "source_url": "https://mistore.pk/",
        "verification_notes": "Verified MiStore Pakistan Xiaomi 14T Pro (Leica Optics, Dimensity 9300+, 12GB/512GB) official price of Rs. 229,999.",
        "is_latest": 1,
        "is_popular": 1,
        "variants": [
            {"variant_label": "12GB RAM / 512GB Storage", "ram_gb": 12, "storage_gb": 512, "price_pkr": 229999},
        ],
    },
    {
        "brand_slug": "xiaomi",
        "model_name": "Redmi Note 14 Pro+ 5G",
        "official_variant_name": "24115RA8EG (12GB RAM / 512GB Storage — MiStore PK Official PTA)",
        "slug": "xiaomi-redmi-note-14-pro-plus-5g",
        "price_pkr": 126999,
        "release_date": "2025-01-20",
        "ram_gb": 12,
        "ram_display": "12 GB LPDDR5",
        "storage_gb": 512,
        "storage_display": "512 GB UFS 3.1",
        "processor": "Qualcomm Snapdragon 7s Gen 3 (4 nm)",
        "display_type": "CrystalRes AMOLED, 120Hz, HDR10+, Dolby Vision, 3000 nits",
        "display_size_inch": 6.67,
        "display_resolution": "1220 x 2712 pixels (1.5K)",
        "refresh_rate": "120Hz",
        "main_camera": "200 MP (wide, OIS, 1/1.4\") + 8 MP (ultrawide) + 2 MP (macro)",
        "selfie_camera": "20 MP (wide, 1080p@60fps)",
        "battery_mah": 5110,
        "charging": "120W HyperCharge wired",
        "network": "GSM / HSPA / LTE / 5G",
        "is_5g": 1,
        "os": "Android 14, Xiaomi HyperOS",
        "dimensions": "162.5 x 74.7 x 8.8 mm",
        "weight": "205 g",
        "build_material": "Gorilla Glass Victus 2 front, IP68 dust/water resistant",
        "colors": "Spectre Blue, Midnight Black, Lavender Purple",
        "source_name": "MiStore Pakistan (Xiaomi Official Distributor)",
        "source_url": "https://mistore.pk/",
        "verification_notes": "Verified MiStore Pakistan Redmi Note 14 Pro+ 5G (Snapdragon 7s Gen 3, 200MP OIS, 5110 mAh, 120W) official price.",
        "is_latest": 1,
        "is_popular": 1,
        "variants": [
            {"variant_label": "12GB RAM / 512GB Storage", "ram_gb": 12, "storage_gb": 512, "price_pkr": 126999},
        ],
    },
    {
        "brand_slug": "xiaomi",
        "model_name": "Redmi 14C",
        "official_variant_name": "2409BRN2CG (6GB RAM / 128GB Storage — MiStore PK Official PTA)",
        "slug": "xiaomi-redmi-14c",
        "price_pkr": 29999,
        "release_date": "2024-10-05",
        "ram_gb": 6,
        "ram_display": "6 GB LPDDR4X",
        "storage_gb": 128,
        "storage_display": "128 GB eMMC 5.1",
        "processor": "MediaTek Helio G81 Ultra (12 nm)",
        "display_type": "IPS LCD, 120Hz, 600 nits (HBM)",
        "display_size_inch": 6.88,
        "display_resolution": "720 x 1640 pixels (HD+)",
        "refresh_rate": "120Hz",
        "main_camera": "50 MP (f/1.8 wide) + Auxiliary lens",
        "selfie_camera": "13 MP (f/2.0, HDR)",
        "battery_mah": 5160,
        "charging": "18W wired PD charging",
        "network": "2G / 3G / 4G LTE",
        "is_5g": 0,
        "os": "Android 14, Xiaomi HyperOS",
        "dimensions": "171.9 x 77.8 x 8.2 mm",
        "weight": "204 g",
        "build_material": "Glass front, glass/eco-leather back, side-mounted fingerprint",
        "colors": "Midnight Black, Sage Green, Starry Blue",
        "source_name": "MiStore Pakistan (Xiaomi Official Distributor)",
        "source_url": "https://mistore.pk/",
        "verification_notes": "Verified MiStore Pakistan budget smartphone Redmi 14C (6GB/128GB, 6.88\" 120Hz, 5160 mAh) official retail price.",
        "is_latest": 1,
        "is_popular": 0,
        "variants": [
            {"variant_label": "4GB RAM / 128GB Storage", "ram_gb": 4, "storage_gb": 128, "price_pkr": 26999},
            {"variant_label": "6GB RAM / 128GB Storage", "ram_gb": 6, "storage_gb": 128, "price_pkr": 29999},
        ],
    },
    {
        "brand_slug": "vivo",
        "model_name": "Vivo V40e 5G",
        "official_variant_name": "V2403 (8GB RAM / 256GB Storage — Vivo Pakistan Official PTA)",
        "slug": "vivo-v40e-5g",
        "price_pkr": 99999,
        "release_date": "2024-11-02",
        "ram_gb": 8,
        "ram_display": "8 GB LPDDR4X (+8 GB Extended RAM)",
        "storage_gb": 256,
        "storage_display": "256 GB UFS 2.2",
        "processor": "MediaTek Dimensity 7300 (4 nm)",
        "display_type": "3D Curved AMOLED, 120Hz, HDR10+, 4500 nits peak",
        "display_size_inch": 6.77,
        "display_resolution": "1080 x 2392 pixels (FHD+)",
        "refresh_rate": "120Hz",
        "main_camera": "50 MP Sony IMX882 (OIS) + 8 MP (ultrawide, Aura Light)",
        "selfie_camera": "50 MP (Eye AF Group Selfie, 4K video)",
        "battery_mah": 5500,
        "charging": "80W FlashCharge wired",
        "network": "GSM / HSPA / LTE / 5G",
        "is_5g": 1,
        "os": "Android 14, Funtouch OS 14",
        "dimensions": "163.7 x 75.0 x 7.5 mm",
        "weight": "183 g",
        "build_material": "Ultra-slim 3D curved glass, IP64 dust/water resistance",
        "colors": "Royal Bronze, Mint Green",
        "source_name": "Vivo Pakistan Official",
        "source_url": "https://www.vivo.com/pk",
        "verification_notes": "Verified Vivo Pakistan V40e 5G (Dimensity 7300, 5500 mAh BlueVolt battery, 80W FlashCharge) official price of Rs. 99,999.",
        "is_latest": 1,
        "is_popular": 1,
        "variants": [
            {"variant_label": "8GB RAM / 256GB Storage", "ram_gb": 8, "storage_gb": 256, "price_pkr": 99999},
        ],
    },
    {
        "brand_slug": "oppo",
        "model_name": "Oppo Reno 12F 5G",
        "official_variant_name": "CPH2637 (8GB RAM / 256GB Storage — Oppo Pakistan Official PTA)",
        "slug": "oppo-reno-12f-5g",
        "price_pkr": 79999,
        "release_date": "2024-10-18",
        "ram_gb": 8,
        "ram_display": "8 GB LPDDR4X",
        "storage_gb": 256,
        "storage_display": "256 GB UFS 2.2",
        "processor": "MediaTek Dimensity 6300 (6 nm)",
        "display_type": "AMOLED, 120Hz, 2100 nits (peak), Asahi Glass AGC DT-Star2",
        "display_size_inch": 6.67,
        "display_resolution": "1080 x 2400 pixels (FHD+)",
        "refresh_rate": "120Hz",
        "main_camera": "50 MP (wide) + 8 MP (ultrawide) + 2 MP (macro) with Halo Light",
        "selfie_camera": "32 MP (wide, 1080p@30fps)",
        "battery_mah": 5000,
        "charging": "45W SUPERVOOC Flash Charge",
        "network": "GSM / HSPA / LTE / 5G",
        "is_5g": 1,
        "os": "Android 14, ColorOS 14",
        "dimensions": "163.1 x 75.8 x 7.8 mm",
        "weight": "187 g",
        "build_material": "All-Round Armour Body, IP64 dust/water resistant",
        "colors": "Amber Orange, Olive Green",
        "source_name": "Oppo Pakistan Official",
        "source_url": "https://www.oppo.com/pk/",
        "verification_notes": "Verified Oppo Pakistan Reno 12F 5G (8GB/256GB, Dimensity 6300, 45W SUPERVOOC) official retail price of Rs. 79,999.",
        "is_latest": 1,
        "is_popular": 0,
        "variants": [
            {"variant_label": "8GB RAM / 256GB Storage", "ram_gb": 8, "storage_gb": 256, "price_pkr": 79999},
        ],
    },
    {
        "brand_slug": "infinix",
        "model_name": "Infinix Hot 50 Pro+",
        "official_variant_name": "X6880 (8GB RAM / 256GB Storage — Infinix Pakistan Official PTA)",
        "slug": "infinix-hot-50-pro-plus",
        "price_pkr": 52999,
        "release_date": "2024-11-12",
        "ram_gb": 8,
        "ram_display": "8 GB LPDDR4X (+8 GB Extended RAM)",
        "storage_gb": 256,
        "storage_display": "256 GB UFS 2.2",
        "processor": "MediaTek Helio G100 (6 nm)",
        "display_type": "3D-Curved AMOLED, 120Hz, 1300 nits, Gorilla Glass",
        "display_size_inch": 6.78,
        "display_resolution": "1080 x 2436 pixels (FHD+)",
        "refresh_rate": "120Hz",
        "main_camera": "50 MP (f/1.6 wide) + 2 MP (depth)",
        "selfie_camera": "13 MP (f/2.2, LED flash)",
        "battery_mah": 5000,
        "charging": "33W Advanced FastCharge, Bypass Charging",
        "network": "2G / 3G / 4G LTE",
        "is_5g": 0,
        "os": "Android 14, XOS 14.5",
        "dimensions": "164.1 x 74.4 x 6.8 mm",
        "weight": "162 g",
        "build_material": "6.8mm SlimEdge 3D-Curved architecture, IP54 rating, JBL Dual Speakers",
        "colors": "Titanium Grey, Sleek Black, Dreamy Purple",
        "source_name": "Infinix Mobility Pakistan",
        "source_url": "https://pk.infinixmobility.com/",
        "verification_notes": "Verified Infinix Mobility Pakistan Hot 50 Pro+ (6.8mm 3D-Curved AMOLED, Helio G100, 8GB/256GB) official price.",
        "is_latest": 1,
        "is_popular": 1,
        "variants": [
            {"variant_label": "8GB RAM / 256GB Storage", "ram_gb": 8, "storage_gb": 256, "price_pkr": 52999},
        ],
    },
    {
        "brand_slug": "tecno",
        "model_name": "Tecno Spark 30 Pro",
        "official_variant_name": "KL7 (8GB RAM / 256GB Storage — Tecno Pakistan Official PTA)",
        "slug": "tecno-spark-30-pro",
        "price_pkr": 41999,
        "release_date": "2024-11-08",
        "ram_gb": 8,
        "ram_display": "8 GB LPDDR4X (+8 GB Extended RAM)",
        "storage_gb": 256,
        "storage_display": "256 GB Internal Storage",
        "processor": "MediaTek Helio G100 (6 nm)",
        "display_type": "AMOLED, 120Hz, 1700 nits (peak), TUV Eye Care",
        "display_size_inch": 6.78,
        "display_resolution": "1080 x 2436 pixels (FHD+)",
        "refresh_rate": "120Hz",
        "main_camera": "108 MP (f/1.9 main sensor, 3x lossless zoom) + Quad LED flash",
        "selfie_camera": "13 MP (Dual color temperature flash)",
        "battery_mah": 5000,
        "charging": "33W Super Charge wired",
        "network": "2G / 3G / 4G LTE",
        "is_5g": 0,
        "os": "Android 14, HiOS 14.5",
        "dimensions": "166.6 x 77.0 x 7.4 mm",
        "weight": "188 g",
        "build_material": "7.4mm ultra-thin frame, IP54 dust/splash resistance, Dolby Atmos stereo",
        "colors": "Obsidian Edge, Arctic Glow",
        "source_name": "Tecno Mobile Pakistan",
        "source_url": "https://www.tecno-mobile.com/pk/",
        "verification_notes": "Verified Tecno Mobile Pakistan Spark 30 Pro (Helio G100, 108MP camera, 120Hz AMOLED, 8GB/256GB) official price.",
        "is_latest": 1,
        "is_popular": 0,
        "variants": [
            {"variant_label": "8GB RAM / 256GB Storage", "ram_gb": 8, "storage_gb": 256, "price_pkr": 41999},
        ],
    },
]


def run_phase2_upgrade():
    init_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Remove confirmed orphan test SVG files
    phones_img_dir = os.path.join(BASE_DIR, "static", "images", "phones")
    removed_orphans = 0
    for orphan in ORPHAN_TEST_SVGS:
        path = os.path.join(phones_img_dir, orphan)
        if os.path.exists(path):
            os.remove(path)
            removed_orphans += 1

    conn = get_db_connection()
    cursor = conn.cursor()

    for orphan in ORPHAN_TEST_SVGS:
        cursor.execute("DELETE FROM media_assets WHERE filename = ?", (orphan,))

    # 2. Update 14 existing models with verified Pakistan prices & official sources
    updated_existing_count = 0
    for phone_id, upd in VERIFIED_EXISTING_UPDATES.items():
        row = cursor.execute("SELECT * FROM phones WHERE id = ?", (phone_id,)).fetchone()
        if not row:
            continue
        old_price = row["price_pkr"]
        new_price = upd["price_pkr"]

        cursor.execute(
            """
            UPDATE phones SET
                price_pkr = ?,
                official_variant_name = ?,
                pta_status = ?,
                availability = ?,
                data_status = ?,
                is_demo_data = ?,
                catalog_status = ?,
                is_latest = ?,
                is_popular = ?,
                source_name = ?,
                source_url = ?,
                verification_notes = ?,
                data_source_note = ?,
                last_verified_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                new_price,
                upd["official_variant_name"],
                upd["pta_status"],
                upd["availability"],
                upd["data_status"],
                upd["is_demo_data"],
                upd["catalog_status"],
                upd["is_latest"],
                upd["is_popular"],
                upd["source_name"],
                upd["source_url"],
                upd["verification_notes"],
                upd["verification_notes"],
                now_str,
                now_str,
                phone_id,
            ),
        )
        if old_price != new_price:
            cursor.execute(
                """
                INSERT INTO price_history (phone_id, old_price_pkr, new_price_pkr, note, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    phone_id,
                    old_price,
                    new_price,
                    f"Phase 2 Catalog Verification ({upd['source_name']})",
                    now_str,
                ),
            )
        updated_existing_count += 1

    # 3. Update 15 remaining existing models to keep DEMO/SAMPLE + set accurate catalog_status & is_latest=0
    for phone_id, st_upd in DEMO_EXISTING_STATUS_UPDATES.items():
        cursor.execute(
            """
            UPDATE phones SET
                catalog_status = ?,
                availability = ?,
                is_latest = ?,
                is_demo_data = 1,
                data_status = 'DEMO/SAMPLE'
            WHERE id = ?
            """,
            (
                st_upd["catalog_status"],
                st_upd["availability"],
                st_upd["is_latest"],
                phone_id,
            ),
        )

    conn.commit()

    # 4. Add 10 new current researched & verified models (idempotent by slug)
    added_new_count = 0
    added_images_count = 0
    for item in NEW_CURRENT_PHONES:
        brand_row = cursor.execute(
            "SELECT * FROM brands WHERE slug = ?", (item["brand_slug"],)
        ).fetchone()
        if not brand_row:
            continue

        conn.commit()
        img_url = generate_phone_svg(
            slug=item["slug"],
            brand_name=brand_row["name"],
            model_name=item["model_name"],
            accent_hex=brand_row["accent_color"],
            secondary_hex="#0f172a",
            is_demo=False,
        )
        added_images_count += 1

        summary_text = (
            f"{brand_row['name']} {item['model_name']} ({item['official_variant_name']}) is officially available in Pakistan "
            f"featuring a {item['display_size_inch']}-inch {item['display_type']} display, {item['processor']}, "
            f"{item['ram_display']} RAM, {item['storage_display']} storage, and a {item['battery_mah']} mAh battery."
        )

        existing = cursor.execute(
            "SELECT id FROM phones WHERE slug = ?", (item["slug"],)
        ).fetchone()

        if existing:
            target_id = existing["id"]
            cursor.execute(
                """
                UPDATE phones SET
                    brand_id = ?, model_name = ?, official_variant_name = ?,
                    price_pkr = ?, currency = 'PKR', pta_status = 'PTA Approved / Official Warranty',
                    availability = 'Available', is_demo_data = 0, data_status = 'VERIFIED',
                    catalog_status = 'CURRENT', last_verified_at = ?,
                    source_name = ?, source_url = ?, verification_notes = ?, data_source_note = ?,
                    image_url = ?, gallery_json = ?, release_date = ?,
                    ram_gb = ?, ram_display = ?, storage_gb = ?, storage_display = ?,
                    processor = ?, display_type = ?, display_size_inch = ?, display_resolution = ?,
                    refresh_rate = ?, main_camera = ?, selfie_camera = ?, battery_mah = ?,
                    charging = ?, network = ?, is_5g = ?, os = ?, dimensions = ?, weight = ?,
                    build_material = ?, colors = ?, summary_text = ?,
                    is_latest = ?, is_popular = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    brand_row["id"], item["model_name"], item["official_variant_name"],
                    item["price_pkr"], now_str,
                    item["source_name"], item["source_url"], item["verification_notes"], item["verification_notes"],
                    img_url, json.dumps([img_url]), item["release_date"],
                    item["ram_gb"], item["ram_display"], item["storage_gb"], item["storage_display"],
                    item["processor"], item["display_type"], item["display_size_inch"], item["display_resolution"],
                    item["refresh_rate"], item["main_camera"], item["selfie_camera"], item["battery_mah"],
                    item["charging"], item["network"], item["is_5g"], item["os"], item["dimensions"], item["weight"],
                    item["build_material"], item["colors"], summary_text,
                    item["is_latest"], item["is_popular"], now_str,
                    target_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO phones (
                    brand_id, model_name, official_variant_name, slug,
                    price_pkr, currency, pta_status, availability,
                    is_demo_data, data_status, catalog_status, last_verified_at,
                    source_name, source_url, verification_notes, data_source_note,
                    image_url, gallery_json, release_date,
                    ram_gb, ram_display, storage_gb, storage_display, processor,
                    display_type, display_size_inch, display_resolution, refresh_rate,
                    main_camera, selfie_camera, battery_mah, charging, network, is_5g,
                    os, dimensions, weight, build_material, sim_type, colors, sensors,
                    summary_text, is_latest, is_popular,
                    sale_active, sale_price_pkr, sale_start_at, sale_end_at, sale_label,
                    views_count, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, 'PKR', 'PTA Approved / Official Warranty', 'Available',
                    0, 'VERIFIED', 'CURRENT', ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, 'Dual SIM (Nano-SIM, dual stand-by)', ?, 'In-display Fingerprint, Accelerometer, Gyro, Proximity, Compass',
                    ?, ?, ?,
                    0, NULL, NULL, NULL, NULL,
                    25, ?, ?
                )
                """,
                (
                    brand_row["id"], item["model_name"], item["official_variant_name"], item["slug"],
                    item["price_pkr"], now_str,
                    item["source_name"], item["source_url"], item["verification_notes"], item["verification_notes"],
                    img_url, json.dumps([img_url]), item["release_date"],
                    item["ram_gb"], item["ram_display"], item["storage_gb"], item["storage_display"], item["processor"],
                    item["display_type"], item["display_size_inch"], item["display_resolution"], item["refresh_rate"],
                    item["main_camera"], item["selfie_camera"], item["battery_mah"], item["charging"], item["network"], item["is_5g"],
                    item["os"], item["dimensions"], item["weight"], item["build_material"], item["colors"],
                    summary_text, item["is_latest"], item["is_popular"],
                    now_str, now_str,
                ),
            )
            target_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO price_history (phone_id, old_price_pkr, new_price_pkr, note, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    target_id,
                    item["price_pkr"],
                    item["price_pkr"],
                    f"Initial Verified Pakistan Launch Price ({item['source_name']})",
                    now_str,
                ),
            )
            added_new_count += 1

        cursor.execute("DELETE FROM phone_variants WHERE phone_id = ?", (target_id,))
        for v in item.get("variants", []):
            cursor.execute(
                """
                INSERT INTO phone_variants (phone_id, variant_label, ram_gb, storage_gb, price_pkr)
                VALUES (?, ?, ?, ?, ?)
                """,
                (target_id, v["variant_label"], v["ram_gb"], v["storage_gb"], v["price_pkr"]),
            )

    conn.commit()
    conn.close()
    print(
        f"[OK] Phase 2 Upgrade Complete: Updated {updated_existing_count} verified existing phones, "
        f"added {added_new_count} new current phones, generated {added_images_count} model-specific SVGs, "
        f"removed {removed_orphans} orphan test SVGs."
    )


if __name__ == "__main__":
    run_phase2_upgrade()
