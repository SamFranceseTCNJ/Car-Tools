import asyncio
import os
from bleak import BleakClient
from dotenv import load_dotenv

MODEL_NBR_UUID = "2A24"
load_dotenv()
address = os.getenv("MAC_ADDRESS")

async def main(address):
    async with BleakClient(address) as client:
        model_number = await client.read_gatt_char(MODEL_NBR_UUID)
        print(f"Model Number: {model_number.decode()}")

asyncio.run(main(address))