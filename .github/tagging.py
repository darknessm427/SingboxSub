#!/usr/bin/env python3
"""
Proxy Configuration Processor

This script processes proxy configurations by:
1. Tagging proxies with country emojis and CDN detection
2. Removing duplicates
3. Sorting proxies alphabetically
4. Organizing them into a selector outbound
"""

import json
import socket
import geoip2.database
import os
from typing import Optional, Dict, Set, Tuple, Any

# Configuration
CONFIG_PATH = "final.json"
BACKUP_CONFIG = "final_backup.json"
GEOIP_DB_PATH = ".github/geoip.db"
TIMEOUT = 10

PROXY_TYPES = (
    "vmess", "trojan", "shadowsocks", "vless",
    "hysteria", "hysteria2", "tuic", "wireguard",
    "anytls", "shadowtls", "socks", "http"
)

# CDN categories
CDN_CATEGORIES = {
    "cloudflare", "google", "amazon", "microsoft",
    "oracle", "digitalocean", "linode", "gcore"
}

# Country Emoji Mapping
COUNTRY_EMOJIS = {
        "ad": "🇦🇩", "ae": "🇦🇪", "af": "🇦🇫", "ag": "🇦🇬", "ai": "🇦🇮",
        "al": "🇦🇱", "am": "🇦🇲", "ao": "🇦🇴", "aq": "🇦🇶", "ar": "🇦🇷",
        "as": "🇦🇸", "at": "🇦🇹", "au": "🇦🇺", "aw": "🇦🇼", "ax": "🇦🇽",
        "az": "🇦🇿", "ba": "🇧🇦", "bb": "🇧🇧", "bd": "🇧🇩", "be": "🇧🇪",
        "bf": "🇧🇫", "bg": "🇧🇬", "bh": "🇧🇭", "bi": "🇧🇮", "bj": "🇧🇯",
        "bl": "🇧🇱", "bm": "🇧🇲", "bn": "🇧🇳", "bo": "🇧🇴", "bq": "🇧🇶",
        "br": "🇧🇷", "bs": "🇧🇸", "bt": "🇧🇹", "bv": "🇧🇻", "bw": "🇧🇼",
        "by": "🇧🇾", "bz": "🇧🇿", "ca": "🇨🇦", "cc": "🇨🇨", "cd": "🇨🇩",
        "cf": "🇨🇫", "cg": "🇨🇬", "ch": "🇨🇭", "ci": "🇨🇮", "ck": "🇨🇰",
        "cl": "🇨🇱", "cm": "🇨🇲", "cn": "🇨🇳", "co": "🇨🇴", "cr": "🇨🇷",
        "cu": "🇨🇺", "cv": "🇨🇻", "cw": "🇨🇼", "cx": "🇨🇽", "cy": "🇨🇾",
        "cz": "🇨🇿", "de": "🇩🇪", "dj": "🇩🇯", "dk": "🇩🇰", "dm": "🇩🇲",
        "do": "🇩🇴", "dz": "🇩🇿", "ec": "🇪🇨", "ee": "🇪🇪", "eg": "🇪🇬",
        "eh": "🇪🇭", "er": "🇪🇷", "es": "🇪🇸", "et": "🇪🇹", "fi": "🇫🇮",
        "fj": "🇫🇯", "fk": "🇫🇰", "fm": "🇫🇲", "fo": "🇫🇴", "fr": "🇫🇷",
        "ga": "🇬🇦", "gb": "🇬🇧", "gd": "🇬🇩", "ge": "🇬🇪", "gf": "🇬🇫",
        "gg": "🇬🇬", "gh": "🇬🇭", "gi": "🇬🇮", "gl": "🇬🇱", "gm": "🇬🇲",
        "gn": "🇬🇳", "gp": "🇬🇵", "gq": "🇬🇶", "gr": "🇬🇷", "gs": "🇬🇸",
        "gt": "🇬🇹", "gu": "🇬🇺", "gw": "🇬🇼", "gy": "🇬🇾", "hk": "🇭🇰",
        "hm": "🇭🇲", "hn": "🇭🇳", "hr": "🇭🇷", "ht": "🇭🇹", "hu": "🇭🇺",
        "id": "🇮🇩", "ie": "🇮🇪", "il": "🇮🇱", "im": "🇮🇲", "in": "🇮🇳",
        "io": "🇮🇴", "iq": "🇮🇶", "ir": "🇮🇷", "is": "🇮🇸", "it": "🇮🇹",
        "je": "🇯🇪", "jm": "🇯🇲", "jo": "🇯🇴", "jp": "🇯🇵", "ke": "🇰🇪",
        "kg": "🇰🇬", "kh": "🇰🇭", "ki": "🇰🇮", "km": "🇰🇲", "kn": "🇰🇳",
        "kp": "🇰🇵", "kr": "🇰🇷", "kw": "🇰🇼", "ky": "🇰🇾", "kz": "🇰🇿",
        "la": "🇱🇦", "lb": "🇱🇧", "lc": "🇱🇨", "li": "🇱🇮", "lk": "🇱🇰",
        "lr": "🇱🇷", "ls": "🇱🇸", "lt": "🇱🇹", "lu": "🇱🇺", "lv": "🇱🇻",
        "ly": "🇱🇾", "ma": "🇲🇦", "mc": "🇲🇨", "md": "🇲🇩", "me": "🇲🇪",
        "mf": "🇲🇫", "mg": "🇲🇬", "mh": "🇲🇭", "mk": "🇲🇰", "ml": "🇲🇱",
        "mm": "🇲🇲", "mn": "🇲🇳", "mo": "🇲🇴", "mp": "🇲🇵", "mq": "🇲🇶",
        "mr": "🇲🇷", "ms": "🇲🇸", "mt": "🇲🇹", "mu": "🇲🇺", "mv": "🇲🇻",
        "mw": "🇲🇼", "mx": "🇲🇽", "my": "🇲🇾", "mz": "🇲🇿", "na": "🇳🇦",
        "nc": "🇳🇨", "ne": "🇳🇪", "nf": "🇳🇫", "ng": "🇳🇬", "ni": "🇳🇮",
        "nl": "🇳🇱", "no": "🇳🇴", "np": "🇳🇵", "nr": "🇳🇷", "nu": "🇳🇺",
        "nz": "🇳🇿", "om": "🇴🇲", "pa": "🇵🇦", "pe": "🇵🇪", "pf": "🇵🇫",
        "pg": "🇵🇬", "ph": "🇵🇭", "pk": "🇵🇰", "pl": "🇵🇱", "pm": "🇵🇲",
        "pn": "🇵🇳", "pr": "🇵🇷", "ps": "🇵🇸", "pt": "🇵🇹", "pw": "🇵🇼",
        "py": "🇵🇾", "qa": "🇶🇦", "re": "🇷🇪", "ro": "🇷🇴", "rs": "🇷🇸",
        "ru": "🇷🇺", "rw": "🇷🇼", "sa": "🇸🇦", "sb": "🇸🇧", "sc": "🇸🇨",
        "sd": "🇸🇩", "se": "🇸🇪", "sg": "🇸🇬", "sh": "🇸🇭", "si": "🇸🇮",
        "sj": "🇸🇯", "sk": "🇸🇰", "sl": "🇸🇱", "sm": "🇸🇲", "sn": "🇸🇳",
        "so": "🇸🇴", "sr": "🇸🇷", "ss": "🇸🇸", "st": "🇸🇹", "sv": "🇸🇻",
        "sx": "🇸🇽", "sy": "🇸🇾", "sz": "🇸🇿", "tc": "🇹🇨", "td": "🇹🇩",
        "tf": "🇹🇫", "tg": "🇹🇬", "th": "🇹🇭", "tj": "🇹🇯", "tk": "🇹🇰",
        "tl": "🇹🇱", "tm": "🇹🇲", "tn": "🇹🇳", "to": "🇹🇴", "tr": "🇹🇷",
        "tt": "🇹🇹", "tv": "🇹🇻", "tw": "🇹🇼", "tz": "🇹🇿", "ua": "🇺🇦",
        "ug": "🇺🇬", "um": "🇺🇲", "us": "🇺🇸", "uy": "🇺🇾", "uz": "🇺🇿",
        "va": "🇻🇦", "vc": "🇻🇨", "ve": "🇻🇪", "vg": "🇻🇬", "vi": "🇻🇮",
        "vn": "🇻🇳", "vu": "🇻🇺", "wf": "🇼🇫", "ws": "🇼🇸", "xk": "🇽🇰",
        "ye": "🇾🇪", "yt": "🇾🇹", "za": "🇿🇦", "zm": "🇿🇲", "zw": "🇿🇼",
        
        # Special cases
        "eu": "🇪🇺", "un": "🇺🇳", "cdn": "🏴",
        "unknown": "🌐", "local": "🏠", "private": "🔒"
    }

def load_geoip_reader():
    """Load GeoIP reader with validation"""
    try:
        if not os.path.exists(GEOIP_DB_PATH):
            print("❌ GeoIP database not found")
            return None
        return geoip2.database.Reader(GEOIP_DB_PATH)
    except Exception as e:
        print(f"❌ GeoIP DB error: {e}")
        return None

def resolve_ip(domain: str) -> str:
    """Resolve domain to IP with special cases"""
    if domain.lower() in ["localhost", "127.0.0.1"]:
        return "localhost"
    if domain.startswith(("10.", "172.16.", "192.168.")):
        return "private"
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        return domain

def get_ip_info(geoip_reader, ip: str) -> Tuple[str, str]:
    """Get country code and CDN status for an IP"""
    if ip in ["localhost", "private"]:
        return (ip, ip)
    
    country_code = "unknown"
    is_cdn = False
    
    if geoip_reader:
        try:
            # Check country first
            country = geoip_reader.country(ip)
            country_code = country.country.iso_code.lower() if country.country.iso_code else "unknown"
            
            # Check if IP belongs to a known CDN
            if country.country.name and any(
                cdn_keyword.lower() in country.country.name.lower()
                for cdn_keyword in CDN_CATEGORIES
            ):
                is_cdn = True
                
        except Exception as e:
            print(f"⚠️ GeoIP lookup failed for {ip}: {str(e)}")
    
    return ("cdn" if is_cdn else country_code, country_code)

def process_proxies(config: Dict, geoip_reader) -> Dict:
    """Process and tag all proxies"""
    seen = set()
    results = {
        "total": 0,
        "duplicates": 0,
        "cdn_count": 0,
        "countries": {}
    }

    for proxy in config.get("outbounds", []):
        if proxy.get("type") not in PROXY_TYPES:
            continue

        server = proxy.get("server", "").strip()
        port = str(proxy.get("port", proxy.get("server_port", "")).strip()
        ip = resolve_ip(server)

        # Skip duplicates
        if (ip, port) in seen:
            results["duplicates"] += 1
            continue
        seen.add((ip, port))

        # Get IP info
        ip_category, country_code = get_ip_info(geoip_reader, ip)
        
        # Get appropriate emoji
        emoji = COUNTRY_EMOJIS.get(ip_category, "🌐")
        
        # Update tag (format: "🌐 - 103.104.247.47:8080")
        proxy["tag"] = f"{emoji} - {server}:{port}"
        
        # Update stats
        results["total"] += 1
        if ip_category == "cdn":
            results["cdn_count"] += 1
        results["countries"][country_code] = results["countries"].get(country_code, 0) + 1

    # Print statistics
    print(f"\n📊 Processing Results:")
    print(f"✅ Total proxies: {results['total']}")
    print(f"🚫 Duplicates removed: {results['duplicates']}")
    print(f"🏴 CDN Proxies: {results['cdn_count']}")
    print("🌍 Countries Detected:")
    for country, count in sorted(results["countries"].items(), key=lambda x: -x[1]):
        print(f"  {country}: {count}")

    return config

def sort_proxies(config: Dict) -> Dict:
    """Sort proxies alphabetically by tag"""
    if len(config.get("outbounds", [])) < 2:
        return config
    
    # Separate proxies from other outbounds
    proxies = []
    others = []
    
    for outbound in config["outbounds"]:
        if outbound.get("type") in PROXY_TYPES:
            proxies.append(outbound)
        else:
            others.append(outbound)
    
    # Sort proxies by tag
    proxies_sorted = sorted(proxies, key=lambda x: x.get("tag", "").lower())
    
    # Rebuild outbounds
    config["outbounds"] = others + proxies_sorted
    return config

def main():
    print("🚀 Starting proxy processor...")
    
    # Load GeoIP database
    geoip_reader = load_geoip_reader()
    if not geoip_reader:
        print("⚠️ Proceeding without GeoIP database - all proxies will use 🌐 emoji")
    
    # Load config
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return
    
    # Process proxies
    config = process_proxies(config, geoip_reader)
    config = sort_proxies(config)
    
    # Save config
    try:
        with open(BACKUP_CONFIG, "w") as f:
            json.dump(config, f, indent=2)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n💾 Config saved! Backup: {BACKUP_CONFIG}")
    except Exception as e:
        print(f"❌ Failed to save config: {e}")

if __name__ == "__main__":
    main()
