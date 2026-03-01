import asyncio
import json
import time
from typing import Optional


DTC_PREFIXES = {
    "0": "P0", "1": "P1", "2": "P2", "3": "P3",
    "4": "C0", "5": "C1", "6": "C2", "7": "C3",
    "8": "B0", "9": "B1", "A": "B2", "B": "B3",
    "C": "U0", "D": "U1", "E": "U2", "F": "U3",
}


def now_ms() -> int:
    return int(time.time() * 1000)


class metrics_helpers:
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
    

    def parse_throttle_position_pct(self, resp: str) -> Optional[float]:
        # PID 0x11: A
        data = self._find_mode01_pid_bytes(resp, 0x11, 1)
        if not data:
            return None
        A = data[0]
        return (A / 255.0) * 100.0
    

    def parse_engine_load(self, resp: str) -> Optional[float]:
        # PID 0x04: A
        data = self._find_mode01_pid_bytes(resp, 0x04, 1)
        if not data:
            return None
        A = data[0]
        return (A / 255.0) * 100.0

    def parse_intake_manifold_pressure_kpa(self, resp: str) -> Optional[float]:
        # PID 0x0B: A
        data = self._find_mode01_pid_bytes(resp, 0x0B, 1)
        if not data:
            return None
        A = data[0]
        return float(A)
    
    
    def parse_coolant_temp_c(self, resp: str) -> Optional[float]:
        # PID 0x05: A
        data = self._find_mode01_pid_bytes(resp, 0x05, 1)
        if not data:
            return None
        A = data[0]
        return float(A - 40)


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
    

    def parse_fuel_rate_lph(self, resp: str) -> Optional[float]:
        # PID 0x5E: A B
        data = self._find_mode01_pid_bytes(resp, 0x5E, 2)
        if not data:
            return None
        A, B = data
        return ((A * 256) + B) / 20.0

    
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


    async def read_dtcs(self, send_elm: callable) -> list[str]:
        resp = await send_elm("03", timeout=5.0)
        if not resp or "NO DATA" in resp or "UNABLE" in resp:
            return []
        return self.parse_dtcs(resp)
    