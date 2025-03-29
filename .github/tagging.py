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
from typing import Optional, Dict, Set, Tuple, Any, List

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

def load_geoip_reader() -> Optional[geoip2.database.Reader]:
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
    if not domain:  # check for empty domain
        return "unknown"
    domain = domain.strip()
    if domain.lower() in ["localhost", "127.0.0.1"]:
        return "localhost"
    if domain.startswith(("10.", "172.16.", "192.168.")):
        return "private"
    try:
        return socket.gethostbyname(domain)
    except (socket.gaierror, socket.timeout):
        return domain  # Return original domain if resolution fails

def get_ip_info(geoip_reader: Optional[geoip2.database.Reader], ip: str) -> Tuple[str, str]:
    if ip in ["localhost", "private", "unknown"]:
        return (ip, ip)
    
    country_code = "unknown"
    is_cdn = False
    
    if geoip_reader and ip.replace('.', '').isdigit():
        try:
            response = geoip_reader.country(ip)
            country_code = response.country.iso_code.lower() if response.country.iso_code else "unknown"
            
            if response.country.name and any(
                cdn_keyword.lower() in response.country.name.lower()
                for cdn_keyword in CDN_CATEGORIES
            ):
                is_cdn = True
                
        except Exception as e:
            print(f"⚠️ GeoIP lookup failed for {ip}: {str(e)}")
    
    return ("cdn" if is_cdn else country_code, country_code)

def process_proxies(config: Dict[str, Any], geoip_reader: Optional[geoip2.database.Reader]) -> Dict[str, Any]:
    """Process and tag all proxies"""
    seen = set()
    results = {
        "total": 0,
        "duplicates": 0,
        "cdn_count": 0,
        "countries": {}
    }

    if "outbounds" not in config:  # check for outbounds key
        print("⚠️ No outbounds found in config")
        return config

    for proxy in config.get("outbounds", []):
        if proxy.get("type") not in PROXY_TYPES:
            continue

        server = proxy.get("server", "").strip()
        if not server:  # Skip if server is empty
            continue
            
        port = str(proxy.get("server_port")).strip()
        ip = resolve_ip(server)

        # Skip duplicates
        proxy_key = (ip, port)
        if proxy_key in seen:
            results["duplicates"] += 1
            continue
        seen.add(proxy_key)

        # Get IP info
        ip_category, country_code = get_ip_info(geoip_reader, ip)
        
        # Get appropriate emoji
        emoji = COUNTRY_EMOJIS.get(ip_category, COUNTRY_EMOJIS["unknown"])
        
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
    for country, count in sorted(results["countries"].items(), key=lambda x: (-x[1], x[0])):
        emoji = COUNTRY_EMOJIS.get(country, "🌐")
        print(f"  {emoji} {country}: {count}")

    return config

def sort_proxies(config: Dict[str, Any]) -> Dict[str, Any]:
    """Sort proxies alphabetically by tag"""
    if "outbounds" not in config or len(config["outbounds"]) < 2:
        return config
    
    # Separate proxies from other outbounds
    proxies: List[Dict[str, Any]] = []
    others: List[Dict[str, Any]] = []
    
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

def main() -> None:  # Added return type hint
    print("🚀 Starting proxy processor...")
    
    # Load GeoIP database
    geoip_reader = load_geoip_reader()
    if not geoip_reader:
        print("⚠️ Proceeding without GeoIP database - all proxies will use 🌐 emoji")
    
    # Load config
    try:
        with open(CONFIG_PATH, "r", encoding='utf-8') as f:  # Added encoding
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {CONFIG_PATH}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config: {e}")
        return
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return
    
    # Process proxies
    config = process_proxies(config, geoip_reader)
    config = sort_proxies(config)
    
    # Save config
    try:
        
        with open(BACKUP_CONFIG, "w", encoding='utf-8') as f:  # Added encoding
            json.dump(config, f, indent=2, ensure_ascii=False)  # Added ensure_ascii=False for emojis
        with open(CONFIG_PATH, "w", encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Config saved! Backup: {BACKUP_CONFIG}")
    except Exception as e:
        print(f"❌ Failed to save config: {e}")

if __name__ == "__main__":
    main()
