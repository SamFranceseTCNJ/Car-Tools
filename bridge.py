import asyncio
import json
import time
from typing import Optional

from bleak import BleakClient, BleakScanner
import websockets

# ---------- CONFIG ----------
DEVICE_NAME_HINT = "IOS-Vlink"
SCAN_TIMEOUT = 6.0
WS_HOST = "127.0.0.1"
WS_PORT = 8765
POLL_INTERVAL = 0.5
# ---------------------------

DTC_PREFIXES = {
    "0": "P0", "1": "P1", "2": "P2", "3": "P3",
    "4": "C0", "5": "C1", "6": "C2", "7": "C3",
    "8": "B0", "9": "B1", "A": "B2", "B": "B3",
    "C": "U0", "D": "U1", "E": "U2", "F": "U3",
}

def now_ms() -> int:
    return int(time.time() * 1000)


class ELM327Bridge:
    def __init__(self):
        self.client: Optional[BleakClient] = None
        self.device_address: Optional[str] = None

        self.write_char_uuid: Optional[str] = None
        self.notify_char_uuid: Optional[str] = None

        self._rx_buffer = ""
        self._response_queue = asyncio.Queue()

        self.latest = {
            "ts": now_ms(),
            "rpm": None,
            "speed_kph": None,
            "raw": None,
            "dtcs": []
        }

        self.ws_clients = set()

    async def find_device(self) -> str:
        """Scan BLE devices and pick the first matching DEVICE_NAME_HINT."""
        devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT)

        print("\nDiscovered BLE devices:")
        for d in devices:
            print(f"  - {d.name!r}  addr={d.address}")
        print("")

        for d in devices:
            if d.name and DEVICE_NAME_HINT.lower() in d.name.lower():
                print(f"Selected device: {d.name} ({d.address})")
                return d.address

        raise RuntimeError(
            f"Could not find a BLE device with name containing '{DEVICE_NAME_HINT}'. "
            f"Try changing DEVICE_NAME_HINT to match your scan output."
        )

    async def connect(self):
        if not self.device_address:
            self.device_address = await self.find_device()

        self.client = BleakClient(self.device_address)
        print("Connecting...")
        await self.client.connect()
        print("Connected.")

        await self._discover_chars()
        await self._start_notify()

        # Initialize ELM to make responses easier to parse
        await self.send_elm("ATZ")   # reset
        await self.send_elm("ATE0")  # echo off
        await self.send_elm("ATL0")  # linefeeds off
        await self.send_elm("ATS0")  # spaces off
        await self.send_elm("ATH0")  # headers off (often helpful)
        await self.send_elm("ATSP0") # automatic protocol

        print("ELM init complete.")
        
        # Read DTCs on connect
        dtcs = await self.read_dtcs()
        if dtcs:
            print(f"Active fault codes: {dtcs}")
        else:
            print("No fault codes found.")

    async def _discover_chars(self):
        assert self.client is not None

        services = self.client.services
        print("Services/Characteristics:")
        write_candidates = []
        notify_candidates = []

        for s in services:
            print(f"- Service {s.uuid}")
            for c in s.characteristics:
                props = ",".join(c.properties)
                print(f"    Char {c.uuid}  props=[{props}]")

                if "notify" in c.properties:
                    notify_candidates.append(c.uuid)
                if "write" in c.properties or "write-without-response" in c.properties:
                    write_candidates.append(c.uuid)

        if not write_candidates or not notify_candidates:
            raise RuntimeError(
                "Could not find suitable write/notify characteristics automatically. "
                "Paste the printed characteristic list here and I’ll tell you which UUIDs to use."
            )

        self.write_char_uuid = write_candidates[0]
        self.notify_char_uuid = notify_candidates[0]

        print(f"\nChosen write char:  {self.write_char_uuid}")
        print(f"Chosen notify char: {self.notify_char_uuid}\n")

    async def _start_notify(self):
        assert self.client is not None
        assert self.notify_char_uuid is not None

        def on_notify(_, data: bytearray):
            try:
                chunk = data.decode("utf-8", errors="ignore")
            except Exception:
                chunk = ""

            if not chunk:
                return

            self._rx_buffer += chunk

            while ">" in self._rx_buffer:
                full, rest = self._rx_buffer.split(">", 1)
                self._rx_buffer = rest
                cleaned = full.strip()
                if cleaned:
                    self._response_queue.put_nowait(cleaned)

        print("Enabling notifications...")
        await self.client.start_notify(self.notify_char_uuid, on_notify)
        print("Notifications enabled.")

    async def write_line(self, line: str):
        assert self.client is not None
        assert self.write_char_uuid is not None

        payload = (line + "\r").encode("utf-8")
        await self.client.write_gatt_char(self.write_char_uuid, payload, response=False)

    async def send_elm(self, cmd: str, timeout: float = 2.0) -> str:
        """Send an ELM command and wait for the response (until '>')."""

        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except Exception:
                break

        await self.write_line(cmd)

        try:
            resp = await asyncio.wait_for(self._response_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            resp = ""

        return resp

    async def poll_loop(self):
        """Poll RPM and speed forever."""
        while True:
            try:
                rpm_resp = await self.send_elm("010C")
                spd_resp = await self.send_elm("010D")

                rpm = self.parse_rpm(rpm_resp)
                speed = self.parse_speed_kph(spd_resp)

                self.latest = {
                    "ts": now_ms(),
                    "rpm": rpm,
                    "speed_kph": speed,
                    "raw": {"010C": rpm_resp, "010D": spd_resp}
                }
                print(self.latest)

                await self.broadcast(self.latest)

            except Exception as e:
                print(f"[poll_loop] error: {e}")

            await asyncio.sleep(POLL_INTERVAL)

    @staticmethod
    def _extract_hex_bytes(resp: str):
        """
        Convert a response like:
          '41 0C 1A F8'  or  '410C1AF8'  or '41 0C 1A F8\r\n...'
        into a list of byte ints.
        """

        filtered = []
        for ch in resp:
            if ch in "0123456789abcdefABCDEF ":
                filtered.append(ch)
        s = "".join(filtered).strip()

        if " " in s:
            parts = [p for p in s.split() if p]
        else:

            parts = [s[i:i+2] for i in range(0, len(s), 2)]

        out = []
        for p in parts:
            if len(p) == 2:
                try:
                    out.append(int(p, 16))
                except ValueError:
                    pass
        return out

    def parse_rpm(self, resp: str):
        b = self._extract_hex_bytes(resp)

        try:
            i = b.index(0x41)
            if i + 3 < len(b) and b[i+1] == 0x0C:
                A, B = b[i+2], b[i+3]
                return ((A * 256) + B) / 4.0
        except ValueError:
            pass
        return None

    def parse_speed_kph(self, resp: str):
        b = self._extract_hex_bytes(resp)

        try:
            i = b.index(0x41)
            if i + 2 < len(b) and b[i+1] == 0x0D:
                return float(b[i+2])
        except ValueError:
            pass
        return None
    
    @staticmethod
    def parse_dtcs(resp: str) -> list[str]:
        codes = []
        parts = [p for p in resp.upper().split() if len(p) == 2]

        if parts and parts[0] == "43":
            parts = parts[1:]

        for i in range(0, len(parts) - 1, 2):
            b1, b2 = parts[i], parts[i+1]
            if b1 == "00" and b2 == "00":
                continue
            prefix = DTC_PREFIXES.get(b1[0], "P0")
            codes.append(prefix + b1[1] + b2)

        return codes

    async def read_dtcs(self) -> list[str]:
        resp = await self.send_elm("03", timeout=5.0)
        if not resp or "NO DATA" in resp or "UNABLE" in resp:
            return []
        codes = self.parse_dtcs(resp)
        self.latest["dtcs"] = codes
        await self.broadcast(self.latest)
        return codes

    async def broadcast(self, msg: dict):
        if not self.ws_clients:
            return
        data = json.dumps(msg)
        dead = set()
        for ws in self.ws_clients:
            try:
                await ws.send(data)
            except Exception:
                dead.add(ws)
        self.ws_clients -= dead


async def ws_handler(bridge: ELM327Bridge, websocket):
    bridge.ws_clients.add(websocket)
    try:
        await websocket.send(json.dumps(bridge.latest))
        async for _ in websocket:
            pass
    finally:
        bridge.ws_clients.discard(websocket)


async def main():
    bridge = ELM327Bridge()
    await bridge.connect()

    async def handler(websocket):
        return await ws_handler(bridge, websocket)

    ws_server = await websockets.serve(handler, WS_HOST, WS_PORT)
    print(f"WebSocket server running at ws://{WS_HOST}:{WS_PORT}")

    await bridge.poll_loop()

    await ws_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())