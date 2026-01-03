import json

from js import Response, Headers, Request

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
        try:
            # Fetch dashboard HTML from ASSETS binding
            dashboard_request = Request.new(f"{url.split('?')[0].rstrip('/')}/dashboard.html")
            dashboard_response = await env.ASSETS.fetch(dashboard_request)

            # Read the HTML content
            dashboard_html = await dashboard_response.text()

            # Inject the WebSocket URL dynamically
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
