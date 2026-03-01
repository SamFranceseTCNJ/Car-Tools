from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

def generate_content(dtc_code):
    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        config=types.GenerateContentConfig(
            system_instruction="You are a helpful assistant that provides information about cars." \
            " You will be given a DTC code and you should respond with a brief description of the " \
            "issue and possible causes. If you don't know the answer, say you don't know. Additionally," \
            "rank the severity of the issue on a scale of 1 to 10, with 10 being the most severe. Justify" \
            "your reasoning. Finally, provide a recommended course of action."),
        contents=dtc_code
    )
    return response.text

if __name__ == "__main__":
    response = generate_content("P1516")
    print(response)