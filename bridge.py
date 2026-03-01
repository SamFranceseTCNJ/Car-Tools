import asyncio
import json
import time
from typing import Optional

from bleak import BleakClient, BleakScanner
from TelemetryData import live_metrics, engine_metrics, fuel_air_metrics, status_metrics, diagnostics_metrics, now_ms
import websockets

# ---------- CONFIG ----------
DEVICE_NAME_HINT = "IOS-Vlink"
SCAN_TIMEOUT = 6.0
WS_HOST = "127.0.0.1"
WS_PORT = 8765
# ---------------------------


class ELM327Bridge:
    def __init__(self):
        self.client: Optional[BleakClient] = None
        self.device_address: Optional[str] = None

        self.write_char_uuid: Optional[str] = None
        self.notify_char_uuid: Optional[str] = None

        self._rx_buffer = ""
        self._response_queue = asyncio.Queue()

        self.ws_clients = set()

        self.live_data = live_metrics()
        self.engine_data = engine_metrics()
        self.fuel_air_data = fuel_air_metrics()
        self.status_data = status_metrics()
        self.diagnostics_data = diagnostics_metrics()

        self.live_data_latest = {
            "ts": now_ms(),
            "rpm": None,
            "speed_kph": None,
            "engine_load": None,
            "intake_manifold_pressure": None,
            "throttle_position": None,
        }

        self.engine_data_latest = {
            "ts": now_ms(),
            "coolant_temp": None,
            "intake_air_temp_c": None,
            "timing_advance_deg": None,
        }

        self.fuel_air_data_latest = {
            "ts": now_ms(),            
            "maf_gps": None,
            "short_term_fuel_trim_B1": None,
            "long_term_fuel_trim_B1": None,
            "short_term_fuel_trim_B2": None,
            "long_term_fuel_trim_B2": None,
            "fuel_rate": None,
        }

        self.status_data_latest = {
            "fuel_level": None,
            "control_module_voltage": None,
        }

        self.diagnostics_data_latest = {
            "dtcs": []
        }


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
    

    async def live_poll_loop(self, poll_interval = 0.5):
        while True:
            try:
                rpm = await self.send_elm("010C")
                speed = await self.send_elm("010D")
                engine_load = await self.send_elm("0104")
                intake_manifold_pres = await self.send_elm("010B")
                throttle_pos = await self.send_elm("0111")

                self.live_data_latest = {
                    "ts": now_ms(),
                    "rpm": self.live_data.parse_rpm(rpm),
                    "speed_kph": self.live_data.parse_speed_kph(speed),
                    "engine_load": self.live_data.parse_engine_load(engine_load),
                    "intake_manifold_pressure": self.live_data.parse_intake_manifold_pressure_kpa(intake_manifold_pres),
                    "throttle_position": self.live_data.parse_throttle_position_pct(throttle_pos)
                }

                await self.broadcast(self.live_data_latest)

            except Exception as e:
                print(f"[live_poll_loop] error: {e}")

            await asyncio.sleep(poll_interval)


    async def engine_poll_loop(self, poll_interval = 2):
        while True:
            try:
                coolant_temp = await self.send_elm("0105")
                intake_air_temp = await self.send_elm("010F")
                timing_advance = await self.send_elm("010E")

                self.engine_data_latest = {
                    "ts": now_ms(),
                    "coolant_temp": self.engine_data.parse_coolant_temp_c(coolant_temp),
                    "intake_air_temp_c": self.engine_data.parse_intake_air_temp_c(intake_air_temp),
                    "timing_advance_deg": self.engine_data.parse_timing_advance_deg(timing_advance)
                }

                await self.broadcast(self.engine_data_latest)

            except Exception as e:
                print(f"[engine_poll_loop] error: {e}")

            await asyncio.sleep(poll_interval)
            
    async def fuel_air_poll_loop(self, poll_interval = 2):
        while True:
            try:
                mass_air_flow = await self.send_elm("0110")
                short_term_fuel_trim_B1 = await self.send_elm("0106")
                long_term_fuel_trim_B1 = await self.send_elm("0107")
                short_term_fuel_trim_B2 = await self.send_elm("0108")
                long_term_fuel_trim_B2 = await self.send_elm("0109")
                fuel_rate = await self.send_elm("015E")

                self.fuel_air_data_latest = {
                    "maf_gps": self.parse_maf_gps(mass_air_flow),
                    "short_term_fuel_trim_B1": self.fuel_air_data.parse_stft_bank1_pct(short_term_fuel_trim_B1),
                    "long_term_fuel_trim_B1": self.fuel_air_data.parse_ltft_bank1_pct(long_term_fuel_trim_B1),
                    "short_term_fuel_trim_B2": self.fuel_air_data.parse_stft_bank2_pct(short_term_fuel_trim_B2),
                    "long_term_fuel_trim_B2": self.fuel_air_data.parse_ltft_bank2_pct(long_term_fuel_trim_B2),
                    "fuel_rate": self.fuel_air_data.parse_fuel_rate_lph(fuel_rate)
                }

                await self.broadcast(self.fuel_air_data_latest)

            except Exception as e:
                print(f"[fuel_air_poll_loop] error: {e}")

            await asyncio.sleep(poll_interval)


    async def status_poll_loop(self, poll_interval = 10):
        while True:
            try:
                fuel_lev = await self.send_elm("012F")
                control_module_volt = await self.send_elm("0142")
                
                self.status_data_latest = {
                    "fuel_level": self.status_data.parse_fuel_level_pct(fuel_lev),
                    "control_module_voltage": self.status_data.parse_control_module_voltage_v(control_module_volt)
                }

                await self.broadcast(self.status_data_latest)

            except Exception as e:
                print(f"[status_poll_loop] error: {e}")

            await asyncio.sleep(poll_interval)
    
    async def diagnostics_poll_loop(self, poll_interval = 5):
        while True:
            try:    
                self.diagnostics_data_latest = {
                    "dtcs": await self.diagnostics_data.read_dtcs(send_elm=self.send_elm)
                }

                await self.broadcast(self.diagnostics_data_latest)

            except Exception as e:
                print(f"[diagnostics_poll_loop] error: {e}")

            await asyncio.sleep(poll_interval)

    def _extract_hex_bytes(self, resp: str):
        """
        Convert responses like:
        '41 0C 1A F8'
        '410C1AF8'
        '41 0C 1A F8\r\n'
        into a list of byte ints.
        """
        filtered = []
        for ch in resp:
            if ch in "0123456789abcdefABCDEF ":
                filtered.append(ch)
        s = "".join(filtered).strip()

        if not s:
            return []

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


    def _find_mode01_pid_bytes(self, resp: str, pid: int, data_len: int):
        """
        Find a Mode 01 response '41 <pid> ...' and return the next `data_len` bytes.
        Returns None if not found or not enough bytes.
        """
        b = self._extract_hex_bytes(resp)
        if not b:
            return None

        # Look for sequence: 0x41, pid
        for i in range(len(b) - (2 + data_len) + 1):
            if b[i] == 0x41 and b[i + 1] == pid:
                data = b[i + 2 : i + 2 + data_len]
                if len(data) == data_len:
                    return data
        return None


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