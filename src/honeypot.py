import json

from js import Date, Response


def extract_features(request):
    """Extract features from incoming request"""
    from features import get_request_entropy, parse_user_agent

    headers = dict(request.headers)

    return {
        "path": request.url,
        "method": request.method,
        "user_agent": headers.get("user-agent", ""),
        "ip": headers.get("cf-connecting-ip", ""),
        "country": headers.get("cf-ipcountry", ""),
        "timestamp": Date.now(),
        # Add more features
        "path_entropy": get_request_entropy(request.url),
        "ua_parsed": parse_user_agent(headers.get("user-agent", "")),
    }


async def handle_honeypot_request(request, env):
    """Process honeypot traffic and classify"""

    # Extract features
    features = extract_features(request)

    # TODO: Classify with Workers AI (once model is trained)
    # For now, use simple heuristics or Cloudflare's bot score
    cf_bot_score = request.cf.botManagement.score if hasattr(request, "cf") else 50

    prediction = {
        "label": "attack" if cf_bot_score < 30 else "legit",
        "confidence": abs(cf_bot_score - 50) / 50,
        "bot_score": cf_bot_score,
    }

    # Log to D1
    try:
        await (
            env.DB.prepare(
                """INSERT INTO traffic
               (timestamp, path, method, ip, country, prediction, confidence, bot_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
            )
            .bind(
                features["timestamp"],
                features["path"],
                features["method"],
                features["ip"],
                features["country"],
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
                "timestamp": features["timestamp"],
                "path": features["path"],
                "method": features["method"],
                "ip": features["ip"],
                "country": features["country"],
                "prediction": prediction["label"],
                "confidence": round(prediction["confidence"], 2),
            }
        )
    except Exception as e:
        print(f"Broadcast error: {e}")

    # Return boring response (don't tip off attackers)
    return Response.new(
        "OK", {"status": 200, "headers": {"Content-Type": "text/plain"}}
    )
