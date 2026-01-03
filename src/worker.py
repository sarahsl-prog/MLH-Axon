import json

from js import Response

from traffic_monitor import TrafficMonitor  # Import the Durable Object


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
        return Response.new(
            health_data,
            {"headers": {"Content-Type": "application/json"}}
        )

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
        try:
            # Read dashboard.html file
            with open("public/dashboard.html", "r") as f:
                html = f.read()

            # Inject the WebSocket URL dynamically
            # Extract the host from the request URL
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            ws_protocol = "wss" if parsed_url.scheme == "https" else "ws"
            ws_url = f"{ws_protocol}://{parsed_url.netloc}/ws"

            # Replace the placeholder WebSocket URL
            html = html.replace(
                "wss://axon.your-subdomain.workers.dev/ws",
                ws_url
            )

            return Response.new(html, {"headers": {"Content-Type": "text/html"}})
        except Exception as e:
            print(f"Error serving dashboard: {e}")
            return Response.new(
                f"Error loading dashboard: {str(e)}",
                {"status": 500, "headers": {"Content-Type": "text/plain"}}
            )

    # Everything else is honeypot traffic
    from honeypot import handle_honeypot_request

    return await handle_honeypot_request(request, env)
