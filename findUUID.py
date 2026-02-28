import asyncio
from bleak import BleakClient

async def find_model_uuid(address):
    async with BleakClient(address) as client:
        # Iterate through all services discovered on the device
        for service in client.services:
            for char in service.characteristics:
                # Bleak automatically provides descriptions for standard SIG UUIDs
                if "Model Number String" in char.description:
                    print(f"Found Model Number UUID: {char.uuid}")
                    
                    # Optional: Read the actual model number
                    value = await client.read_gatt_char(char.uuid)
                    print(f"Device Model: {value.decode()}")
                    return char.uuid
    print("Model Number characteristic not found.")

# Replace with your device's MAC address (or UUID on macOS)
asyncio.run(find_model_uuid("C0:6B:FC:01:0A:E7"))
