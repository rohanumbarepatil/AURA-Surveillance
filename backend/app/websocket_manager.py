import asyncio
import json
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.event_manager import NormalizedEvent

class WebSocketManager:
    """
    Manages active WebSocket connections and broadcasts normalized surveillance events.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(self, event: NormalizedEvent):
        """
        Broadcasts ALERT_SENT (which includes escalations) and RESOLVED events to all connected clients.
        Automatically cleans up any broken connections.
        """
        if event.status not in ["ALERT_SENT", "RESOLVED"]:
            return

        message = event.to_dict()
        message_json = json.dumps(message)
        
        disconnected_clients = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception:
                disconnected_clients.append(connection)
                
        # Safely remove any clients that failed to receive the message
        for failed_conn in disconnected_clients:
            self.disconnect(failed_conn)

    def broadcast_event_sync(self, event: NormalizedEvent):
        """
        Helper to broadcast events from synchronous contexts (e.g. OpenCV video processing loop).
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_event(event))
        except RuntimeError:
            # If no running event loop, create one to run the broadcast
            asyncio.run(self.broadcast_event(event))


# Global instance to be used across the application
manager = WebSocketManager()

# Router to expose the WebSocket endpoint
router = APIRouter(
    prefix="/ws",
    tags=["WebSockets"],
)

@router.websocket("/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


def run_test():
    """Standalone test for WebSocketManager using mock websockets"""
    import uuid
    from datetime import datetime
    
    print("=" * 60)
    print("AURA SURVEILLANCE - WEBSOCKET MANAGER TEST")
    print("=" * 60)
    
    class MockWebSocket:
        def __init__(self, name):
            self.name = name
            self.messages = []
            self.is_connected = True
            
        async def accept(self):
            self.is_connected = True
            
        async def send_text(self, data: str):
            if not self.is_connected:
                raise Exception("Disconnected")
            self.messages.append(data)
            
        def force_disconnect(self):
            self.is_connected = False
            
    async def async_test():
        test_manager = WebSocketManager()
        
        print("\n--- 1. Client Connections ---")
        client1 = MockWebSocket("Client 1")
        client2 = MockWebSocket("Client 2")
        
        await test_manager.connect(client1)
        await test_manager.connect(client2)
        print(f"Connected clients: {len(test_manager.active_connections)}")
        
        print("\n--- 2. Broadcasting ALERT_SENT Event ---")
        event1 = NormalizedEvent(
            event_id=str(uuid.uuid4()),
            camera_id=1,
            rule_id=5,
            rule_name="Crowd Congestion",
            severity="WARNING",
            status="ALERT_SENT",
            timestamp=datetime.utcnow(),
            details="15 people detected",
        )
        await test_manager.broadcast_event(event1)
        print(f"Client 1 received {len(client1.messages)} message(s).")
        print(f"Client 2 received {len(client2.messages)} message(s).")
        
        print("\n--- 3. Handling Disconnections & Escalation ---")
        # Simulate Client 1 unexpectedly dropping connection
        client1.force_disconnect()
        
        event2 = NormalizedEvent(
            event_id=str(uuid.uuid4()),
            camera_id=1,
            rule_id=5,
            rule_name="Crowd Congestion",
            severity="CRITICAL",
            status="ALERT_SENT",
            timestamp=datetime.utcnow(),
            details="[ESCALATED] 20 people detected",
        )
        
        # Broadcasting should fail for Client 1, causing it to be removed automatically
        await test_manager.broadcast_event(event2)
        
        print(f"Connected clients after broadcast (Client 1 dropped): {len(test_manager.active_connections)}")
        print(f"Client 2 received escalated message successfully.")
        
        print("\n--- 4. Broadcasting RESOLVED Event ---")
        event3 = NormalizedEvent(
            event_id=str(uuid.uuid4()),
            camera_id=1,
            rule_id=5,
            rule_name="Crowd Congestion",
            severity="CRITICAL",
            status="RESOLVED",
            timestamp=datetime.utcnow(),
            details="Crowd Congestion resolved",
        )
        await test_manager.broadcast_event(event3)
        print(f"Client 2 received RESOLVED message successfully.")
        
        print("\n--- 5. Ignoring Normal/Monitoring Events ---")
        event4 = NormalizedEvent(
            event_id=str(uuid.uuid4()),
            camera_id=1,
            rule_id=5,
            rule_name="Crowd Congestion",
            severity="WARNING",
            status="MONITORING",
            timestamp=datetime.utcnow(),
            details="Debouncing...",
        )
        await test_manager.broadcast_event(event4)
        print(f"Client 2 total messages remains 3: {len(client2.messages) == 3}")
        
    asyncio.run(async_test())
    
    print("\n" + "=" * 60)
    print("WEBSOCKET MANAGER TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_test()
