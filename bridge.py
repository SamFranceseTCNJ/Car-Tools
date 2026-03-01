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
            "engine_load": None,
            "coolant_temp": None,
            "intake_manifold_pressure": None,
            "timing_advance_deg": None,
            "intake_air_temp_c": None,
            "maf_gps": None,
            "throttle_position": None,
            "short_term_fuel_trim_B1": None,
            "long_term_fuel_trim_B1": None,
            "short_term_fuel_trim_B2": None,
            "long_term_fuel_trim_B2": None,
            "fuel_level": None,
            "control_module_voltage": None,
            "fuel_rate": None,
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
                rpm = await self.send_elm("010C")
                speed = await self.send_elm("010D")
                coolant_temp = await self.send_elm("0105")
                throttle_pos = await self.send_elm("0111")
                intake_air_temp = await self.send_elm("010F")
                mass_air_flow = await self.send_elm("0110")
                intake_manifold_pres = await self.send_elm("010B")
                calc_eng_load = await self.send_elm("0104")
                fuel_lev = await self.send_elm("012F")
                short_term_fuel_trim_B1 = await self.send_elm("0106")
                long_term_fuel_trim_B1 = await self.send_elm("0107")
                short_term_fuel_trim_B2 = await self.send_elm("0108")
                long_term_fuel_trim_B2 = await self.send_elm("0109")
                timing_advance = await self.send_elm("010E")
                control_module_volt = await self.send_elm("0142")
                fuel_rate = await self.send_elm("015E")

                self.latest = {
                    "ts": now_ms(),
                    "rpm": self.parse_rpm(rpm),
                    "speed_kph": self.parse_speed_kph(speed),
                    "engine_load": self.parse_engine_load(calc_eng_load),
                    "coolant_temp": self.parse_coolant_temp_c(coolant_temp),
                    "intake_manifold_pressure": self.parse_intake_manifold_pressure_kpa(intake_manifold_pres),
                    "timing_advance_deg": self.parse_timing_advance_deg(timing_advance),
                    "intake_air_temp_c": self.parse_intake_air_temp_c(intake_air_temp),
                    "maf_gps": self.parse_maf_gps(mass_air_flow),
                    "throttle_position": self.parse_throttle_position_pct(throttle_pos),
                    "short_term_fuel_trim_B1": self.parse_stft_bank1_pct(short_term_fuel_trim_B1),
                    "long_term_fuel_trim_B1": self.parse_ltft_bank1_pct(long_term_fuel_trim_B1),
                    "short_term_fuel_trim_B2": self.parse_stft_bank2_pct(short_term_fuel_trim_B2),
                    "long_term_fuel_trim_B2": self.parse_ltft_bank2_pct(long_term_fuel_trim_B2),
                    "fuel_level": self.parse_fuel_level_pct(fuel_lev),
                    "control_module_voltage": self.parse_control_module_voltage_v(control_module_volt),
                    "fuel_rate": self.parse_fuel_rate_lph(fuel_rate),
                }

                print(self.latest)
                print()

                await self.broadcast(self.latest)

            except Exception as e:
                print(f"[poll_loop] error: {e}")

            await asyncio.sleep(POLL_INTERVAL)


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
    

    def parse_engine_load(self, resp: str) -> Optional[float]:
        # PID 0x04: A
        data = self._find_mode01_pid_bytes(resp, 0x04, 1)
        if not data:
            return None
        A = data[0]
        return (A / 255.0) * 100.0


    def parse_coolant_temp_c(self, resp: str) -> Optional[float]:
        # PID 0x05: A
        data = self._find_mode01_pid_bytes(resp, 0x05, 1)
        if not data:
            return None
        A = data[0]
        return float(A - 40)


    def parse_intake_manifold_pressure_kpa(self, resp: str) -> Optional[float]:
        # PID 0x0B: A
        data = self._find_mode01_pid_bytes(resp, 0x0B, 1)
        if not data:
            return None
        A = data[0]
        return float(A)


    def parse_rpm(self, resp: str) -> Optional[float]:
        # PID 0x0C: A B
        data = self._find_mode01_pid_bytes(resp, 0x0C, 2)
        if not data:
            return None
        A, B = data
        return ((A * 256) + B) / 4.0


    def parse_speed_kph(self, resp: str) -> Optional[float]:
        # PID 0x0D: A
        data = self._find_mode01_pid_bytes(resp, 0x0D, 1)
        if not data:
            return None
        A = data[0]
        return float(A)


    def parse_timing_advance_deg(self, resp: str) -> Optional[float]:
        # PID 0x0E: A
        data = self._find_mode01_pid_bytes(resp, 0x0E, 1)
        if not data:
            return None
        A = data[0]
        return (A / 2.0) - 64.0


    def parse_intake_air_temp_c(self, resp: str) -> Optional[float]:
        # PID 0x0F: A
        data = self._find_mode01_pid_bytes(resp, 0x0F, 1)
        if not data:
            return None
        A = data[0]
        return float(A - 40)


    def parse_maf_gps(self, resp: str) -> Optional[float]:
        # PID 0x10: A B
        data = self._find_mode01_pid_bytes(resp, 0x10, 2)
        if not data:
            return None
        A, B = data
        return ((A * 256) + B) / 100.0


    def parse_throttle_position_pct(self, resp: str) -> Optional[float]:
        # PID 0x11: A
        data = self._find_mode01_pid_bytes(resp, 0x11, 1)
        if not data:
            return None
        A = data[0]
        return (A / 255.0) * 100.0


    def parse_fuel_trim_pct(self, resp: str, pid: int) -> Optional[float]:
        """
        Fuel trims share the same formula:
        STFT B1: PID 0x06
        LTFT B1: PID 0x07
        STFT B2: PID 0x08
        LTFT B2: PID 0x09
        Formula: ((A - 128) / 128) * 100
        """
        data = self._find_mode01_pid_bytes(resp, pid, 1)
        if not data:
            return None
        A = data[0]
        return ((A - 128) / 128.0) * 100.0


    def parse_stft_bank1_pct(self, resp: str) -> Optional[float]:
        return self.parse_fuel_trim_pct(resp, 0x06)

    def parse_ltft_bank1_pct(self, resp: str) -> Optional[float]:
        return self.parse_fuel_trim_pct(resp, 0x07)

    def parse_stft_bank2_pct(self, resp: str) -> Optional[float]:
        return self.parse_fuel_trim_pct(resp, 0x08)

    def parse_ltft_bank2_pct(self, resp: str) -> Optional[float]:
        return self.parse_fuel_trim_pct(resp, 0x09)


    def parse_fuel_level_pct(self, resp: str) -> Optional[float]:
        # PID 0x2F: A
        data = self._find_mode01_pid_bytes(resp, 0x2F, 1)
        if not data:
            return None
        A = data[0]
        return (A / 255.0) * 100.0


    def parse_control_module_voltage_v(self, resp: str) -> Optional[float]:
        # PID 0x42: A B
        data = self._find_mode01_pid_bytes(resp, 0x42, 2)
        if not data:
            return None
        A, B = data
        return ((A * 256) + B) / 1000.0


    def parse_fuel_rate_lph(self, resp: str) -> Optional[float]:
        # PID 0x5E: A B
        data = self._find_mode01_pid_bytes(resp, 0x5E, 2)
        if not data:
            return None
        A, B = data
        return ((A * 256) + B) / 20.0


    def parse_dtcs(self, resp: str) -> list[str]:
        """
        Decode Mode 03 (stored) DTC response using the SAE bit layout.

        Expected payload contains bytes like:
        43 A1 B1 A2 B2 ...
        where each (Ai, Bi) pair is one DTC.
        """

        parts = [p for p in resp.upper().split() if len(p) == 2 and all(ch in "0123456789ABCDEF" for ch in p)]
        if not parts:
            return []
        
        try:
            idx = parts.index("43")
            parts = parts[idx + 1 :]
        except ValueError:
            pass

        codes: list[str] = []

        for i in range(0, len(parts) - 1, 2):
            A = int(parts[i], 16)
            B = int(parts[i + 1], 16)

            if A == 0x00 and B == 0x00:
                continue

            system_bits = (A >> 6) & 0b11
            system = ["P", "C", "B", "U"][system_bits]

            first_digit = (A >> 4) & 0b11

            third_digit = A & 0x0F

            code = f"{system}{first_digit}{third_digit:X}{B:02X}"
            codes.append(code)

        return codes

    async def read_dtcs(self) -> list[str]:
        resp = await self.send_elm("03", timeout=5.0)
        if not resp or "NO DATA" in resp or "UNABLE" in resp:
            return []
        return self.parse_dtcs(resp)

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