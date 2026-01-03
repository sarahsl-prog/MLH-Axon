import json
import os

from js import Response, Headers

from traffic_monitor import TrafficMonitor  # Import the Durable Object


# Load dashboard HTML at module level
DASHBOARD_HTML = None
try:
    # Get the directory of this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to project root and into public
    dashboard_path = os.path.join(current_dir, "..", "public", "dashboard.html")

    # Try alternate paths if first doesn't work
    possible_paths = [
        dashboard_path,
        os.path.join(current_dir, "public", "dashboard.html"),
        "public/dashboard.html",
        "../public/dashboard.html",
    ]

    for path in possible_paths:
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    DASHBOARD_HTML = f.read()
                print(f"Loaded dashboard from: {path}")
                break
        except Exception:
            continue

    if DASHBOARD_HTML is None:
        print("Warning: Could not load dashboard.html from any path")
except Exception as e:
    print(f"Error loading dashboard HTML: {e}")


async def on_fetch(request, env):
    """Main Worker entry point - routes requests appropriately"""
    url = request.url

    # Parse path from URL
    path = url.split("/")[-1] if "/" in url else ""

    # Health check endpoint
    if path == "health":
        from js import Date
        health_data = json.dumps({
            "status": "ok",
            "timestamp": Date.now(),
            "version": "1.0.0"
        })
        headers = Headers.new({"Content-Type": "application/json"}.items())
        return Response.new(health_data, headers=headers)

    # Stats API endpoint
    if "api/stats" in url:
        from stats import get_stats
        return await get_stats(env)

    # WebSocket endpoint for dashboard
    if path == "ws":
        do_id = env.TRAFFIC_MONITOR.idFromName("global")
        stub = env.TRAFFIC_MONITOR.get(do_id)
        return await stub.fetch(request)

    # Serve dashboard HTML
    if path == "" or path == "dashboard":
        # Try to get dashboard HTML from environment binding first, then fallback to loaded HTML
        dashboard_html = None
        if hasattr(env, "DASHBOARD"):
            dashboard_html = env.DASHBOARD
            print("Using dashboard from env.DASHBOARD binding")
        elif DASHBOARD_HTML is not None:
            dashboard_html = DASHBOARD_HTML
            print("Using dashboard from module-level load")
        else:
            headers = Headers.new({"Content-Type": "text/plain"}.items())
            return Response.new(
                "Dashboard HTML not loaded. Please ensure public/dashboard.html exists.",
                status=500,
                headers=headers
            )

        try:
            # Inject the WebSocket URL dynamically
            # Extract the host from the request URL
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            ws_protocol = "wss" if parsed_url.scheme == "https" else "ws"
            ws_url = f"{ws_protocol}://{parsed_url.netloc}/ws"

            # Replace the placeholder WebSocket URL
            html = dashboard_html.replace(
                "wss://axon.your-subdomain.workers.dev/ws",
                ws_url
            )

            # Return HTML response with proper content type
            headers = Headers.new({"Content-Type": "text/html; charset=utf-8"}.items())
            return Response.new(html, status=200, headers=headers)
        except Exception as e:
            print(f"Error serving dashboard: {e}")
            headers = Headers.new({"Content-Type": "text/plain"}.items())
            return Response.new(
                f"Error loading dashboard: {str(e)}",
                status=500,
                headers=headers
            )

    # Everything else is honeypot traffic
    from honeypot import handle_honeypot_request

    return await handle_honeypot_request(request, env)
