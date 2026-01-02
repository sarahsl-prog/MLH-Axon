import json

from cloudflare.workers import DurableObject
from js import Object, WebSocketPair


class TrafficMonitor(DurableObject):
    """Durable Object that coordinates WebSocket connections for real-time dashboard"""

    def __init__(self, state, env):
        super().__init__(state, env)
        self.sessions = []

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

            print(f"New WebSocket connection. Total: {len(self.sessions)}")

            # Return client-side WebSocket with 101 status
            from js import Response

            return Response.new(None, {"status": 101, "webSocket": client})

        from js import Response

        return Response.new("Expected WebSocket", {"status": 400})

    async def webSocketMessage(self, ws, message):
        """Handle incoming WebSocket messages from dashboard"""
        print(f"Received message: {message}")
        # Could handle commands here like "get_stats", "clear_feed", etc.
        ws.send(f"Echo: {message}")

    async def webSocketClose(self, ws, code, reason, wasClean):
        """Clean up closed WebSocket connections"""
        if ws in self.sessions:
            self.sessions.remove(ws)
            print(f"WebSocket closed. Remaining: {len(self.sessions)}")

    async def webSocketError(self, ws, error):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {error}")
        if ws in self.sessions:
            self.sessions.remove(ws)

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
