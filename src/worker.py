import json
import uuid

from js import Response, Headers, Request, Date, WebSocketPair
from workers import DurableObject


class TrafficMonitor(DurableObject):
    """Durable Object that coordinates WebSocket connections for real-time dashboard"""

    def __init__(self, ctx, env):
        self.ctx = ctx
        self.env = env
        self.sessions = []
        self.session_ids = {}  # Map WebSocket to session ID

    async def on_fetch(self, request):
        """Handle WebSocket upgrade requests"""
        if request.headers.get("Upgrade") == "websocket":
            # Create WebSocket pair
            pair_obj = WebSocketPair.new()
            # Convert JsProxy to Python list to access elements
            pair = list(pair_obj)
            client = pair[0]
            server = pair[1]

            # Accept the server-side WebSocket
            self.ctx.acceptWebSocket(server)
            self.sessions.append(server)

            # Generate session ID
            session_id = str(uuid.uuid4())
            self.session_ids[id(server)] = session_id

            print(f"New WebSocket connection. Total: {len(self.sessions)}")

            # Send connection confirmation
            try:
                confirmation = json.dumps({
                    "type": "connected",
                    "timestamp": Date.now(),
                    "session_id": session_id
                })
                server.send(confirmation)
            except Exception as e:
                print(f"Error sending confirmation: {e}")

            # Return client-side WebSocket with 101 status
            return Response.new(None, status=101, webSocket=client)

        return Response.new("Expected WebSocket", status=400)

    async def on_webSocketMessage(self, ws, message):
        """Handle incoming WebSocket messages from dashboard"""
        print(f"Received message: {message}")

        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            # Handle ping/pong
            if msg_type == "ping":
                response = json.dumps({
                    "type": "pong",
                    "timestamp": Date.now()
                })
                ws.send(response)

            # Handle stats request
            elif msg_type == "get_stats":
                # This would query D1 for stats, but for now send basic info
                response = json.dumps({
                    "type": "stats",
                    "total_connections": len(self.sessions),
                    "timestamp": Date.now()
                })
                ws.send(response)

            # Handle filter commands (future enhancement)
            elif msg_type == "filter":
                # Store filter preferences per session
                print(f"Filter requested: {data.get('prediction', 'all')}")
                ws.send(json.dumps({"type": "ack", "message": "Filter applied"}))

            else:
                # Unknown message type
                ws.send(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                    "code": 400
                }))

        except json.JSONDecodeError:
            # If not JSON, just echo it back
            ws.send(f"Echo: {message}")
        except Exception as e:
            print(f"Error handling message: {e}")
            ws.send(json.dumps({
                "type": "error",
                "message": str(e),
                "code": 500
            }))

    async def on_webSocketClose(self, ws, code, reason, wasClean):
        """Clean up closed WebSocket connections"""
        if ws in self.sessions:
            self.sessions.remove(ws)
            # Clean up session ID mapping
            ws_id = id(ws)
            if ws_id in self.session_ids:
                del self.session_ids[ws_id]
            print(f"WebSocket closed. Remaining: {len(self.sessions)}")

    async def on_webSocketError(self, ws, error):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {error}")
        if ws in self.sessions:
            self.sessions.remove(ws)
            # Clean up session ID mapping
            ws_id = id(ws)
            if ws_id in self.session_ids:
                del self.session_ids[ws_id]

    async def broadcast(self, message):
        """
        Broadcast classification data to all connected dashboard clients

        Args:
            message: JSON string containing classification info (timestamp, path, prediction, etc.)
        """
        # Message is already serialized as JSON string from RPC call
        dead_sessions = []

        for session in self.sessions:
            try:
                session.send(message)
            except Exception as e:
                print(f"Failed to send to session: {e}")
                dead_sessions.append(session)

        # Remove dead connections
        for session in dead_sessions:
            if session in self.sessions:
                self.sessions.remove(session)

        if dead_sessions:
            print(f"Cleaned up {len(dead_sessions)} dead sessions")


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
