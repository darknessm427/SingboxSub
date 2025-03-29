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
import requests
import geoip2.database
import os
from pathlib import Path
from typing import Optional, Dict, Set, Tuple, Any, List

# Configuration Constants
CONFIG_PATH = "final.json"
BACKUP_CONFIG = "final_backup.json"
GEOIP_DB_PATH = ".github/geoip.db"
IP_API = "https://api.ip.sb/geoip"
TIMEOUT = 10

PROXY_TYPES = (
    "vmess", "trojan", "shadowsocks", "vless",
    "hysteria", "hysteria2", "tuic", "wireguard",
    "anytls", "shadowtls", "socks", "http"
)

# CDN categories (found in geoip.db)
CDN_CATEGORIES = {
    "cloudflare", "google", "amazon", "microsoft",
    "oracle", "digitalocean", "linode", "gcore"
}

class GeoIPProcessor:
    """Handles GeoIP-related operations"""
    
    def __init__(self, db_path: str = GEOIP_DB_PATH):
        self.reader = self._load_geoip_reader(db_path)
    
    @staticmethod
    def _load_geoip_reader(db_path: str) -> Optional[geoip2.database.Reader]:
        """Load GeoIP reader with validation"""
        try:
            if not os.path.exists(db_path):
                print(f"⚠️ GeoIP database not found at {db_path}")
                return None
            return geoip2.database.Reader(db_path)
        except Exception as e:
            print(f"❌ GeoIP DB error: {e}")
            return None
    
    def get_country_code(self, ip: str) -> Optional[str]:
        """Get country code for an IP address"""
        if not self.reader:
            return None
            
        try:
            country = self.reader.country(ip)
            return country.country.iso_code.lower() if country.country.iso_code else None
        except Exception:
            return None
    
    def is_cdn(self, ip: str) -> bool:
        """Check if IP belongs to a CDN using only geoip.db country names"""
        if not self.reader:
            return False
            
        try:
            country = self.reader.country(ip)
            if country.country.name and any(
                cdn_keyword.lower() in country.country.name.lower()
                for cdn_keyword in CDN_CATEGORIES
            ):
                return True
            return False
        except Exception:
            return False

class ProxyProcessor:
    """Handles proxy processing operations"""
    
    def __init__(self, geoip_processor: GeoIPProcessor):
        self.geoip = geoip_processor
        self.seen_proxies: Set[Tuple[str, str]] = set()
    
    @staticmethod
    def resolve_ip(domain: str) -> str:
        """Resolve domain to IP with special cases handling"""
        if domain in ["localhost", "127.0.0.1"]:
            return "localhost"
        if domain.startswith(("10.", "172.16.", "192.168.")):
            return "private"
        try:
            return socket.gethostbyname(domain)
        except socket.gaierror:
            return domain
    
    def get_country_emoji(self, ip: str) -> str:
        """Get emoji for IP with priority: CDN > Private > Country > Unknown"""
        if ip == "localhost":
            return "🏠"
        if ip == "private":
            return "🔒"
        
        if self.geoip.is_cdn(ip):
            return "🏴"
        
        country_code = self.geoip.get_country_code(ip)
        if not country_code:
            try:
                data = requests.get(f"{IP_API}/{ip}", timeout=5).json()
                country_code = data.get("country_code", "unknown").lower()
            except Exception:
                country_code = "unknown"
        
        return COUNTRY_EMOJIS.get(country_code, "🌐")
    
    def process_proxy(self, proxy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process individual proxy configuration"""
        if proxy.get("type") not in PROXY_TYPES:
            return None

        server = proxy.get("server", "").strip()
        port = str(proxy.get("server_port", "")).strip()
        ip = self.resolve_ip(server)

        if (ip, port) in self.seen_proxies:
            return None
        self.seen_proxies.add((ip, port))

        is_cdn = self.geoip.is_cdn(ip)
        emoji = self.get_country_emoji(ip)
        
        proxy["tag"] = f"{emoji} - {server}:{port} [{proxy['type']}]"
        return proxy

class ConfigManager:
    """Handles configuration file operations"""
    
    @staticmethod
    def load_config(path: str) -> Optional[Dict[str, Any]]:
        """Load JSON configuration file"""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            return None
    
    @staticmethod
    def save_config(config: Dict[str, Any], path: str) -> bool:
        """Save configuration to file"""
        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Failed to save config to {path}: {e}")
            return False
    
    @staticmethod
    def sort_proxies(config: Dict[str, Any]) -> Dict[str, Any]:
        """Sort proxies alphabetically by tag and organize in selector outbound"""
        if len(config.get("outbounds", [])) < 2:
            return config
        
        # Extract proxy outbounds
        proxies = [
            outbound for outbound in config["outbounds"][1:] 
            if outbound["type"] in PROXY_TYPES
        ]
        
        # Sort proxies by their tag
        proxies_sorted = sorted(proxies, key=lambda x: x.get("tag", "").lower())
        
        # Rebuild outbounds structure
        new_outbounds = [
            config["outbounds"][0],  # Preserve first outbound
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
    
    # Initialize components
    geoip = GeoIPProcessor()
    proxy_processor = ProxyProcessor(geoip)
    config_manager = ConfigManager()
    
    # Load configuration
    config = config_manager.load_config(CONFIG_PATH)
    if not config:
        return
    
    # Process proxies
    processed_proxies = []
    stats = {
        "total": 0,
        "duplicates": 0,
        "cdn_count": 0,
        "categories": {}
    }

    for proxy in config.get("outbounds", []):
        processed = proxy_processor.process_proxy(proxy)
        if not processed:
            if proxy.get("type") in PROXY_TYPES:
                stats["duplicates"] += 1
            continue
            
        processed_proxies.append(processed)
        stats["total"] += 1
        
        ip = proxy_processor.resolve_ip(processed["server"])
        if proxy_processor.geoip.is_cdn(ip):
            stats["cdn_count"] += 1
        
        country_code = proxy_processor.geoip.get_country_code(ip) or "unknown"
        stats["categories"][country_code] = stats["categories"].get(country_code, 0) + 1
    
    # Update config with processed proxies
    config["outbounds"] = [
        outbound for outbound in config["outbounds"]
        if outbound.get("type") not in PROXY_TYPES
    ] + processed_proxies
    
    # Sort and reorganize proxies
    config = config_manager.sort_proxies(config)
    
    # Print statistics
    print(f"\n📊 Processing Results:")
    print(f"✅ Total proxies: {stats['total']}")
    print(f"🚫 Duplicates removed: {stats['duplicates']}")
    print(f"🏴 CDN Proxies: {stats['cdn_count']}")
    print("🌍 GeoIP Categories:")
    for cat, count in sorted(stats["categories"].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    # Backup and save
    if config_manager.save_config(config, BACKUP_CONFIG):
        if config_manager.save_config(config, CONFIG_PATH):
            print(f"\n💾 Config saved! Backup: {BACKUP_CONFIG}")

if __name__ == "__main__":
    # Country emoji mapping (250+ countries)
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
    
    main()
