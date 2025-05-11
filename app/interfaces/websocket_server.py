# app/websocket_server.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set

router = APIRouter()

# Maintain separate connection pools by role
active_connections: Dict[str, Set[WebSocket]] = {
    "frontend": set(),
    "speaker": set(),
    "discord": set()
}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Expect client to identify its role first
        init_msg = await websocket.receive_json()
        role = init_msg.get("listen_as", "frontend")
        print(f"New {role} connection")
        active_connections.setdefault(role, set()).add(websocket)

        while True:
            data = await websocket.receive_text()
            print(f"[{role}] Received from client: {data}")
            await websocket.send_text(f"Echo ({role}): {data}")

    except WebSocketDisconnect:
        for role, connections in active_connections.items():
            if websocket in connections:
                connections.remove(websocket)
                print(f"{role} client disconnected")

# Broadcast to all clients listening under a given role
async def broadcast_message(message: str, to: str = "frontend"):
    connections = active_connections.get(to, set())
    print(f"Broadcasting to {to}: {message} ({len(connections)} clients)")
    for connection in list(connections):
        try:
            await connection.send_text(message)
        except Exception:
            connections.remove(connection)
