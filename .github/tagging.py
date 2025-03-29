import json
import socket
import requests
import geoip2.database
import os
from pathlib import Path

# Configuration
CONFIG_PATH = "final.json"
BACKUP_CONFIG = "final_backup.json"
GEOIP_URL = "https://cdn.jsdelivr.net/gh/chocolate4u/Iran-sing-box-rules@release/geoip.db"
GEOIP_DB_PATH = ".github/geoip.db"
IP_API = "https://api.ip.sb/geoip"
TIMEOUT = 10

# CDN categories (aligned with geoip.db)
CDN_ASN_KEYWORDS = {
    "cloudflare", "google", "amazon", "microsoft",
    "oracle", "digitalocean", "linode", "akamai",
    "fastly", "stackpath", "incapsula", "leaseweb"
}

# Extensive Emoji Mapping (250+ countries)
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
    "eu": "🇪🇺", "un": "🇺🇳",
    "unknown": "🌐", "local": "🏠", "private": "🔒"
}

def download_geoip_db():
    """Download geoip.db with retry logic"""
    try:
        if not Path(GEOIP_DB_PATH).exists():
            print("⬇️ Downloading GeoIP database...")
            for attempt in range(3):
                try:
                    response = requests.get(GEOIP_URL, timeout=TIMEOUT)
                    response.raise_for_status()
                    with open(GEOIP_DB_PATH, "wb") as f:
                        f.write(response.content)
                    print("✅ GeoIP database downloaded")
                    return True
                except Exception as e:
                    if attempt == 2:
                        raise
                    print(f"⚠️ Attempt {attempt+1} failed, retrying...")
        return True
    except Exception as e:
        print(f"❌ Failed to download GeoIP DB: {e}")
        return False

def load_geoip_reader():
    """Load GeoIP reader with validation"""
    try:
        if not os.path.exists(GEOIP_DB_PATH):
            return None
        return geoip2.database.Reader(GEOIP_DB_PATH)
    except Exception as e:
        print(f"❌ GeoIP DB error: {e}")
        return None

def is_cdn_ip(geoip_reader, ip):
    """Enhanced CDN detection with ASN lookup"""
    if not geoip_reader:
        return False
    try:
        # First check if IP is in common CDN ranges
        if ip.startswith(('104.16.', '172.64.', '108.162.')):  # Cloudflare
            return True
        if ip.startswith(('34.64.', '35.184.', '130.176.')):  # Google Cloud
            return True
            
        # Then check ASN organization
        asn = geoip_reader.asn(ip)
        org = asn.autonomous_system_organization.lower()
        return any(keyword in org for keyword in CDN_ASN_KEYWORDS)
    except:
        return False

def resolve_ip(domain):
    """Resolve domain with caching and special cases"""
    if domain in ["localhost", "127.0.0.1"]:
        return "localhost"
    if domain.startswith(("10.", "172.16.", "192.168.")):
        return "private"
    try:
        return socket.gethostbyname(domain)
    except:
        return domain

def get_country_emoji(geoip_reader, ip):
    """Get emoji with priority: CDN > Private > Country > Unknown"""
    if ip == "localhost":
        return COUNTRY_EMOJIS["localhost"]
    if ip == "private":
        return COUNTRY_EMOJIS["private"]
        
    if geoip_reader and is_cdn_ip(geoip_reader, ip):
        return COUNTRY_EMOJIS["cdn"]
    
    country_code = "unknown"
    if geoip_reader:
        try:
            country = geoip_reader.country(ip)
            country_code = country.country.iso_code.lower()
        except:
            pass
    
    if country_code == "unknown":
        try:
            data = requests.get(f"{IP_API}/{ip}", timeout=5).json()
            country_code = data.get("country_code", "unknown").lower()
        except:
            pass
    
    return COUNTRY_EMOJIS.get(country_code, "🌐")

def process_proxies(config, geoip_reader):
    """Process all proxies with comprehensive logging"""
    seen = set()
    results = {
        "total": 0,
        "duplicates": 0,
        "cdn": 0,
        "countries": {}
    }
    
    for proxy in config.get("outbounds", []):
        if proxy["type"] not in ("vmess", "trojan", "shadowsocks", "vless", "hysteria", "hysteria2", "anytls", "tuic", "shadowtls"):
            continue
            
        results["total"] += 1
        server = proxy.get("server", "").strip()
        port = str(proxy.get("server_port", "")).strip()
        
        if not server or not port:
            continue
            
        # Resolve IP but keep original domain if available
        original_display = server
        ip = resolve_ip(server)
        
        # Handle duplicates based on IP:port (not domain:port)
        if (ip, port) in seen:
            print(f"➖ Duplicate: {proxy.get('tag','')} ({ip}:{port})")
            results["duplicates"] += 1
            continue
        seen.add((ip, port))
        
        # Get emoji and update stats
        emoji = get_country_emoji(geoip_reader, ip)
        if emoji == "🏴":
            results["cdn"] += 1
        else:
            results["countries"][emoji] = results["countries"].get(emoji, 0) + 1
        
        # Determine display address (domain if available, otherwise IP)
        display_address = f"{original_display}:{port}" if is_domain(server) else f"{ip}:{port}"

        # Update tag while preserving original domain if present
        proxy["tag"] = f"{emoji} - {display_address} [{proxy['type']}]"
    
    # Print summary
    print("\n📊 Results:")
    print(f"• Total proxies: {results['total']}")
    print(f"• Duplicates removed: {results['duplicates']}")
    print(f"• CDN proxies: {results['cdn']}")
    print("• Country distribution:")
    for emoji, count in sorted(results["countries"].items(), key=lambda x: -x[1]):
        print(f"  {emoji}: {count}")
    
    return config

def is_domain(address):
    """Check if the address is a domain name (not IP)"""
    try:
        # Simple check - if it's not an IP address, assume it's a domain
        socket.inet_aton(address)
        return False
    except socket.error:
        return True

def sort_proxies(config):
    """Sort proxies alphabetically by tag and organize in outbounds[1].outbounds"""
    if len(config.get("outbounds", [])) < 2:
        return config
    
    # Extract all proxy outbounds (excluding the first two special entries)
    proxies = [outbound for outbound in config["outbounds"][2:] 
               if outbound["type"] in ("vmess", "trojan", "shadowsocks", "vless", "hysteria", "hysteria2")]
    
    # Sort proxies by their tag
    proxies_sorted = sorted(proxies, key=lambda x: x.get("tag", "").lower())
    
    # Rebuild outbounds structure:
    # 1. Keep original first outbound (usually direct/dns)
    # 2. Create selector outbound with sorted tags
    # 3. Append sorted proxies
    new_outbounds = [
        config["outbounds"][0],  # Preserve first outbound (e.g., "direct")
        {
            "type": "selector",
            "tag": "proxy-selector",
            "outbounds": [p["tag"] for p in proxies_sorted],
            "default": proxies_sorted[0]["tag"] if proxies_sorted else ""
        },
        *proxies_sorted
    ]
    
    config["outbounds"] = new_outbounds
    return config

def main():
    print("🚀 Starting proxy tagging process...")
    
    # GeoIP setup
    if not download_geoip_db():
        print("⚠️ Proceeding without GeoIP database (limited functionality)")
    geoip_reader = load_geoip_reader()
    
    # Load config
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return
    
    # Process proxies
    updated_config = process_proxies(config, geoip_reader)

    # Sort and reorganize proxies
    updated_config = sort_proxies(updated_config)
    
    # Backup and save
    try:
        with open(BACKUP_CONFIG, "w") as f:
            json.dump(config, f, indent=2)
        with open(CONFIG_PATH, "w") as f:
            json.dump(updated_config, f, indent=2)
        print(f"\n✅ Config saved! Backup: {BACKUP_CONFIG}")
    except Exception as e:
        print(f"❌ Failed to save config: {e}")

if __name__ == "__main__":
    main()
