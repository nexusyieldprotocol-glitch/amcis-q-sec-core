"""
AMCIS Q-Sec-Core WebSocket Handlers
===================================

Handles real-time stream multiplexing for the AMCIS 9.0 Dashboard.
Uses Redis Pub/Sub for inter-process event distribution.
"""

import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
from amcis_redis import RedisManager

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
redis_mgr = RedisManager()

async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time security telemetry.
    """
    await manager.connect(websocket)
    
    # Task to listen for Redis events and broadcast to this websocket
    async def listen_and_push():
        pubsub = redis_mgr.client.pubsub()
        pubsub.subscribe("security_events", "system_health", "pqc_logs")
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    await websocket.send_text(message['data'])
        except Exception as e:
            print(f"WS push error: {e}")
        finally:
            pubsub.close()

    push_task = asyncio.create_task(listen_and_push())

    try:
        while True:
            # Keep connection alive and handle client messages if needed
            data = await websocket.receive_text()
            # Echo or handle commands from UI
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        push_task.cancel()
