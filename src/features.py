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
