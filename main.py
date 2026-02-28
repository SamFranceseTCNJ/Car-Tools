import asyncio
from bleak import BleakScanner

async def main():
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Device found: {device.name} ({device.address})")

if __name__ == "__main__":
    asyncio.run(main())
