import json

from js import Response

from traffic_monitor import TrafficMonitor  # Import the Durable Object


async def on_fetch(request, env):
    """Main Worker entry point - routes requests appropriately"""
    url = request.url

    # Parse path from URL
    path = url.split("/")[-1] if "/" in url else ""

    # WebSocket endpoint for dashboard
    if path == "ws":
        do_id = env.TRAFFIC_MONITOR.idFromName("global")
        stub = env.TRAFFIC_MONITOR.get(do_id)
        return await stub.fetch(request)

    # Serve dashboard HTML
    if path == "" or path == "dashboard":
        # TODO: In production, serve actual dashboard.html from R2 or Pages
        html = """
        <!DOCTYPE html>
        <html><body>
        <h1>Axon Dashboard</h1>
        <p>Dashboard coming soon. Deploy dashboard.html separately.</p>
        </body></html>
        """
        return Response.new(html, {"headers": {"Content-Type": "text/html"}})

    # Everything else is honeypot traffic
    from honeypot import handle_honeypot_request

    return await handle_honeypot_request(request, env)
