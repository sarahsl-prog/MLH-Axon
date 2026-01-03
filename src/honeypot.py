import json

from js import Date, Response, Headers


def extract_features(request):
    """Extract features from incoming request"""
    from features import (
        get_request_entropy,
        parse_user_agent,
        detect_sql_injection,
        detect_path_traversal,
        detect_sensitive_files,
        detect_common_exploits,
        analyze_path_characteristics,
    )

    headers = dict(request.headers)
    url = request.url
    path = url.split("?")[0]
    query = url.split("?")[1] if "?" in url else ""

    return {
        "path": path,
        "full_url": url,
        "method": request.method,
        "user_agent": headers.get("user-agent", ""),
        "ip": headers.get("cf-connecting-ip", ""),
        "country": headers.get("cf-ipcountry", ""),
        "timestamp": Date.now(),
        # Path analysis
        "path_entropy": get_request_entropy(url),
        "path_chars": analyze_path_characteristics(path),
        # User agent analysis
        "ua_parsed": parse_user_agent(headers.get("user-agent", "")),
        # Attack pattern detection
        "sql_injection": detect_sql_injection(path, query),
        "path_traversal": detect_path_traversal(path),
        "sensitive_files": detect_sensitive_files(path),
        "common_exploits": detect_common_exploits(path),
    }


def classify_request(features, cf_bot_score):
    """Enhanced heuristic-based classification"""
    score = 0
    reasons = []

    # Bot detection from User-Agent
    if features["ua_parsed"]["is_bot"]:
        score += 30
        reasons.append("bot_user_agent")

    # SQL injection patterns
    if features["sql_injection"]["has_sql_pattern"]:
        if features["sql_injection"]["risk_level"] == "high":
            score += 40
            reasons.append("sql_injection_high")
        elif features["sql_injection"]["risk_level"] == "medium":
            score += 25
            reasons.append("sql_injection_medium")

    # Path traversal attempts
    if features["path_traversal"]["has_traversal"]:
        if features["path_traversal"]["risk_level"] == "high":
            score += 40
            reasons.append("path_traversal_high")
        elif features["path_traversal"]["risk_level"] == "medium":
            score += 25
            reasons.append("path_traversal_medium")

    # Sensitive file access
    if features["sensitive_files"]["accesses_sensitive"]:
        score += 35
        reasons.append("sensitive_file_access")

    # Common exploits
    if features["common_exploits"]["has_exploits"]:
        if features["common_exploits"]["risk_level"] == "high":
            score += 35
            reasons.append("exploit_patterns_high")
        elif features["common_exploits"]["risk_level"] == "medium":
            score += 20
            reasons.append("exploit_patterns_medium")

    # High path entropy (obfuscation)
    if features["path_entropy"] > 4.5:
        score += 20
        reasons.append("high_entropy")

    # Suspicious characters
    if features["path_chars"].get("suspicious_chars"):
        score += 15
        reasons.append("suspicious_chars")

    # Use Cloudflare bot score if available
    if cf_bot_score < 30:
        score += 20
        reasons.append("cf_bot_score_low")

    # Determine label and confidence
    is_attack = score >= 40
    confidence = min(score / 100, 1.0)

    return {
        "label": "attack" if is_attack else "legit",
        "confidence": round(confidence, 3),
        "score": score,
        "bot_score": cf_bot_score,
        "reasons": reasons,
    }


async def handle_honeypot_request(request, env):
    """Process honeypot traffic and classify"""

    # Extract features
    features = extract_features(request)

    # Get Cloudflare bot score if available
    cf_bot_score = 50  # default neutral score
    try:
        if hasattr(request, "cf") and hasattr(request.cf, "botManagement"):
            cf_bot_score = request.cf.botManagement.score
    except Exception as e:
        print(f"Error getting CF bot score: {e}")

    # Classify the request using enhanced heuristics
    # TODO: Switch to Workers AI once model is trained
    prediction = classify_request(features, cf_bot_score)

    # Log to D1
    try:
        await (
            env.DB.prepare(
                """INSERT INTO traffic
               (timestamp, path, method, ip, country, user_agent, prediction, confidence, bot_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            )
            .bind(
                features["timestamp"],
                features["path"],
                features["method"],
                features["ip"],
                features["country"],
                features["user_agent"],
                prediction["label"],
                prediction["confidence"],
                prediction["bot_score"],
            )
            .run()
        )
    except Exception as e:
        print(f"DB error: {e}")

    # Broadcast to connected dashboards
    try:
        do_id = env.TRAFFIC_MONITOR.idFromName("global")
        stub = env.TRAFFIC_MONITOR.get(do_id)
        await stub.broadcast(
            {
                "type": "classification",
                "timestamp": features["timestamp"],
                "path": features["path"],
                "method": features["method"],
                "ip": features["ip"],
                "country": features["country"],
                "user_agent": features["user_agent"],
                "prediction": prediction["label"],
                "confidence": round(prediction["confidence"], 2),
                "bot_score": prediction["bot_score"],
            }
        )
    except Exception as e:
        print(f"Broadcast error: {e}")

    # Return boring response (don't tip off attackers)
    headers = Headers.new({"Content-Type": "text/plain"}.items())
    return Response.new("OK", status=200, headers=headers)
