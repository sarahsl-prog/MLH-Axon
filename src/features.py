import math
from collections import Counter


def get_request_entropy(url):
    """Calculate Shannon entropy of URL path"""
    if not url:
        return 0

    # Get path from URL
    path = url.split("?")[0].split("#")[0]

    # Calculate entropy
    counts = Counter(path)
    length = len(path)

    entropy = 0
    for count in counts.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return round(entropy, 2)


def parse_user_agent(ua_string):
    """Simple user agent parsing"""
    if not ua_string:
        return {"is_bot": True, "client": "unknown"}

    ua_lower = ua_string.lower()

    # Known bot patterns
    bot_patterns = ["bot", "crawler", "spider", "scraper", "curl", "wget", "python"]
    is_bot = any(pattern in ua_lower for pattern in bot_patterns)

    # Detect client
    if "chrome" in ua_lower:
        client = "chrome"
    elif "firefox" in ua_lower:
        client = "firefox"
    elif "safari" in ua_lower:
        client = "safari"
    else:
        client = "other"

    return {"is_bot": is_bot, "client": client}


def detect_sql_injection(path, query_string=""):
    """Detect potential SQL injection attempts"""
    full_string = (path + query_string).lower()

    sql_patterns = [
        "union", "select", "insert", "update", "delete", "drop",
        "exec", "execute", "--", "/*", "*/", "xp_",
        "sp_", "0x", "char(", "waitfor", "delay",
        "1=1", "' or '", "\" or \"", "or 1=1"
    ]

    matches = sum(1 for pattern in sql_patterns if pattern in full_string)

    return {
        "has_sql_pattern": matches > 0,
        "sql_pattern_count": matches,
        "risk_level": "high" if matches >= 3 else "medium" if matches >= 1 else "low"
    }


def detect_path_traversal(path):
    """Detect path traversal attempts"""
    path_lower = path.lower()

    traversal_patterns = [
        "..", "%2e%2e", "..%2f", "..\\", "%2e%2e%2f",
        "%2e%2e/", "..%5c", "%2e%2e\\",
        "/etc/", "/bin/", "/usr/", "/var/",
        "c:\\", "c:/", "%systemroot%"
    ]

    matches = sum(1 for pattern in traversal_patterns if pattern in path_lower)

    return {
        "has_traversal": matches > 0,
        "traversal_count": matches,
        "risk_level": "high" if matches >= 2 else "medium" if matches >= 1 else "low"
    }


def detect_sensitive_files(path):
    """Detect attempts to access sensitive files"""
    path_lower = path.lower()

    sensitive_patterns = [
        ".env", ".git", ".svn", ".htaccess", ".htpasswd",
        "web.config", "config.php", "database.yml",
        "credentials", "secrets", "private_key",
        "id_rsa", ".ssh", "backup", ".sql", ".bak"
    ]

    matches = [pattern for pattern in sensitive_patterns if pattern in path_lower]

    return {
        "accesses_sensitive": len(matches) > 0,
        "sensitive_files": matches,
        "count": len(matches)
    }


def detect_common_exploits(path):
    """Detect common web exploits and scans"""
    path_lower = path.lower()

    exploit_patterns = {
        "wordpress": ["wp-admin", "wp-login", "wp-content", "wp-includes", "xmlrpc"],
        "php_exploits": ["phpinfo", "phpmyadmin", "phpunit", "php-cgi"],
        "admin_scans": ["admin", "administrator", "login", "portal", "manager"],
        "shell_access": ["shell", "cmd", "bash", "powershell", "execute"],
        "injection": ["<script", "javascript:", "onerror=", "onclick=", "eval("]
    }

    detected = {}
    total_matches = 0

    for category, patterns in exploit_patterns.items():
        matches = sum(1 for pattern in patterns if pattern in path_lower)
        if matches > 0:
            detected[category] = matches
            total_matches += matches

    return {
        "has_exploits": total_matches > 0,
        "exploit_categories": detected,
        "total_patterns": total_matches,
        "risk_level": "high" if total_matches >= 3 else "medium" if total_matches >= 1 else "low"
    }


def analyze_path_characteristics(path):
    """Analyze general path characteristics"""
    if not path:
        return {}

    # Remove protocol and domain
    if "://" in path:
        path = path.split("://", 1)[1]
        if "/" in path:
            path = "/" + path.split("/", 1)[1]

    return {
        "length": len(path),
        "num_slashes": path.count("/"),
        "num_dots": path.count("."),
        "num_dashes": path.count("-"),
        "num_underscores": path.count("_"),
        "has_query": "?" in path,
        "num_params": path.count("&") + 1 if "?" in path else 0,
        "has_fragment": "#" in path,
        "suspicious_chars": bool(set(path) & {"<", ">", "'", '"', ";", "|", "&", "$"})
    }
