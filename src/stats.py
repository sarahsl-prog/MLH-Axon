import json

from js import Date, Response, Headers


async def get_stats(env):
    """Get aggregate statistics from D1 database"""
    try:
        # Get total requests
        total_result = await env.DB.prepare(
            "SELECT COUNT(*) as total FROM traffic"
        ).first()
        total_requests = total_result["total"] if total_result else 0

        # Get attacks blocked
        attacks_result = await env.DB.prepare(
            "SELECT COUNT(*) as attacks FROM traffic WHERE prediction = 'attack'"
        ).first()
        attacks_blocked = attacks_result["attacks"] if attacks_result else 0

        # Get legit traffic
        legit_result = await env.DB.prepare(
            "SELECT COUNT(*) as legit FROM traffic WHERE prediction = 'legit'"
        ).first()
        legit_traffic = legit_result["legit"] if legit_result else 0

        # Get requests in last hour
        one_hour_ago = Date.now() - (60 * 60 * 1000)
        recent_result = await env.DB.prepare(
            "SELECT COUNT(*) as recent FROM traffic WHERE timestamp > ?"
        ).bind(one_hour_ago).first()
        requests_last_hour = recent_result["recent"] if recent_result else 0

        # Get top attack types (based on path patterns)
        top_attacks = await env.DB.prepare(
            """
            SELECT path, COUNT(*) as count
            FROM traffic
            WHERE prediction = 'attack'
            GROUP BY path
            ORDER BY count DESC
            LIMIT 10
            """
        ).all()

        # Categorize attack types
        attack_types = {}
        if top_attacks and top_attacks.get("results"):
            for row in top_attacks["results"]:
                path = row["path"].lower()
                count = row["count"]

                # Categorize based on path
                if "wp-" in path or "wordpress" in path:
                    attack_types["wordpress_scan"] = attack_types.get("wordpress_scan", 0) + count
                elif ".env" in path or ".git" in path:
                    attack_types["sensitive_files"] = attack_types.get("sensitive_files", 0) + count
                elif "admin" in path or "login" in path:
                    attack_types["admin_access"] = attack_types.get("admin_access", 0) + count
                elif "php" in path:
                    attack_types["php_exploit"] = attack_types.get("php_exploit", 0) + count
                elif ".." in path or "%2e" in path:
                    attack_types["path_traversal"] = attack_types.get("path_traversal", 0) + count
                else:
                    attack_types["other"] = attack_types.get("other", 0) + count

        # Format top attack types
        top_attack_types = [
            {"type": k, "count": v}
            for k, v in sorted(attack_types.items(), key=lambda x: x[1], reverse=True)
        ]

        # Calculate attack rate
        attack_rate = (attacks_blocked / total_requests) if total_requests > 0 else 0

        stats = {
            "total_requests": total_requests,
            "attacks_blocked": attacks_blocked,
            "legit_traffic": legit_traffic,
            "attack_rate": round(attack_rate, 3),
            "requests_last_hour": requests_last_hour,
            "top_attack_types": top_attack_types[:5],  # Top 5
            "timestamp": Date.now()
        }

        headers = Headers.new({"Content-Type": "application/json"}.items())
        return Response.new(json.dumps(stats), headers=headers)

    except Exception as e:
        print(f"Error getting stats: {e}")
        error_response = json.dumps({
            "error": {
                "code": "STATS_ERROR",
                "message": str(e)
            }
        })
        headers = Headers.new({"Content-Type": "application/json"}.items())
        return Response.new(error_response, status=500, headers=headers)
