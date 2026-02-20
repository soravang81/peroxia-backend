from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        # Dictionary to store active connections per project room.
        # Key: project_id (int), Value: List of WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, project_id: int):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
        print(f"Client connected to room {project_id}. Total: {len(self.active_connections[project_id])}")

    def disconnect(self, websocket: WebSocket, project_id: int):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast(self, message: dict, project_id: int):
        if project_id in self.active_connections:
            # Create a copy of the list to handle potential disconnections during iteration
            for connection in list(self.active_connections[project_id]):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to a client in room {project_id}: {e}")
                    self.disconnect(connection, project_id)

manager = ConnectionManager()
