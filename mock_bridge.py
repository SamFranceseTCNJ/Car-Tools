# backend/mock_bridge.py
import asyncio
import json
import time
import random
import websockets

WS_HOST = "127.0.0.1"
WS_PORT = 8765
POLL_INTERVAL = 0.5

def now_ms():
    return int(time.time() * 1000)

async def mock_poll_loop(ws_clients):
    while True:
        message = {
            "ts": now_ms(),
            "rpm": random.randint(700, 4000),
            "speed_kph": random.randint(0, 120),
            "raw": {
                "010C": "41 0C {:02X} {:02X}".format(random.randint(0, 255), random.randint(0, 255)),
                "010D": "41 0D {:02X}".format(random.randint(0, 255))
            }
        }

        if ws_clients:
            data = json.dumps(message)
            dead = set()
            for ws in ws_clients:
                try:
                    await ws.send(data)
                except:
                    dead.add(ws)
            ws_clients -= dead

        await asyncio.sleep(POLL_INTERVAL)


# ✅ Updated handler (single argument)
async def ws_handler(websocket):
    ws_clients.add(websocket)
    try:
        await websocket.send(json.dumps({"type": "live", "data":{
            "ts": now_ms(),
            "rpm": 0,
            "speed_kph": 0,
            "raw": {}
        }}))

        async for _ in websocket:
            pass
    finally:
        ws_clients.discard(websocket)


async def main():
    global ws_clients
    ws_clients = set()

    # ✅ No lambda needed anymore
    server = await websockets.serve(ws_handler, WS_HOST, WS_PORT)

    print(f"Mock WebSocket server running at ws://{WS_HOST}:{WS_PORT}")

    asyncio.create_task(mock_poll_loop(ws_clients))
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())