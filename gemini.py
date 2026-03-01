from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from dtc_db.python.dtc_database import DTCDatabase

def get_dtc_info(dtc_code):
    db = DTCDatabase()
    dtc = db.get_dtc(dtc_code)
    if dtc:
        return f"{dtc.code} ({dtc.type_name}): {dtc.description}"
    else:
        return "DTC code not found in database."

def generate_content(dtc_code):
    if not dtc_code.startswith(("P", "C", "B", "U")) or len(dtc_code) != 5:
        return "Invalid DTC code format. Please provide a code like 'P0420'."
    dtc_info = get_dtc_info(dtc_code)
    if "DTC code not found in database." in dtc_info:
        return f"Information for {dtc_code} not found in database. Please check the code and try again."

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        config=types.GenerateContentConfig(
            system_instruction="You are a helpful assistant that provides information about cars." \
            " You will be given a DTC code, its type name, and its description. You should respond with a brief description of the " \
            "issue and possible causes. If you don't know the answer, say you don't know. Additionally," \
            "rank the severity of the issue on a scale of 1 to 10, with 10 being the most severe. Justify" \
            "your reasoning. Finally, provide a recommended course of action."),
        contents=dtc_info
    )
    return response.text

if __name__ == "__main__":
    response = generate_content("P1516")
    print(response)