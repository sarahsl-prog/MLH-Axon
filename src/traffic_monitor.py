import json
import uuid

from cloudflare.workers import DurableObject
from js import Date, Object, WebSocketPair


class TrafficMonitor(DurableObject):
    """Durable Object that coordinates WebSocket connections for real-time dashboard"""

    def __init__(self, state, env):
        super().__init__(state, env)
        self.sessions = []
        self.session_ids = {}  # Map WebSocket to session ID

    async def fetch(self, request):
        """Handle WebSocket upgrade requests"""
        if request.headers.get("Upgrade") == "websocket":
            # Create WebSocket pair
            pair = WebSocketPair.new()
            client = pair[0]
            server = pair[1]

            # Accept the server-side WebSocket
            self.state.acceptWebSocket(server)
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
            from js import Response

            return Response.new(None, {"status": 101, "webSocket": client})

        from js import Response

        return Response.new("Expected WebSocket", {"status": 400})

    async def webSocketMessage(self, ws, message):
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

    async def webSocketClose(self, ws, code, reason, wasClean):
        """Clean up closed WebSocket connections"""
        if ws in self.sessions:
            self.sessions.remove(ws)
            # Clean up session ID mapping
            ws_id = id(ws)
            if ws_id in self.session_ids:
                del self.session_ids[ws_id]
            print(f"WebSocket closed. Remaining: {len(self.sessions)}")

    async def webSocketError(self, ws, error):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {error}")
        if ws in self.sessions:
            self.sessions.remove(ws)
            # Clean up session ID mapping
            ws_id = id(ws)
            if ws_id in self.session_ids:
                del self.session_ids[ws_id]

    async def broadcast(self, data):
        """
        Broadcast classification data to all connected dashboard clients

        Args:
            data: Dictionary containing classification info (timestamp, path, prediction, etc.)
        """
        message = json.dumps(data)
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
