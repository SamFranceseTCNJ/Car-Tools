import os
import re
import json
from dataclasses import asdict
from dotenv import load_dotenv

from google import genai
from google.genai import types

from dtc_db.python.dtc_database import DTCDatabase


DTC_RE = re.compile(r"^[PCBU][0-9A-F]{4}$", re.IGNORECASE)

# Choose a model that works broadly with the Gemini Developer API.
# If you *know* you have access to Gemini 3 preview on your endpoint, you can swap it back.
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def normalize_dtc_code(dtc_code: str) -> str:
    return (dtc_code or "").strip().upper()


def get_dtc_info(db: DTCDatabase, dtc_code: str) -> dict | None:
    """
    Returns a dict of dtc metadata from your DB, or None if not found.
    """
    dtc = db.get_dtc(dtc_code)
    if not dtc:
        return None

    # dtc may be a dataclass or a simple object; handle both
    try:
        payload = asdict(dtc)
    except Exception:
        payload = {
            "code": getattr(dtc, "code", dtc_code),
            "type_name": getattr(dtc, "type_name", ""),
            "description": getattr(dtc, "description", ""),
        }

    # Normalize expected keys
    payload.setdefault("code", dtc_code)
    payload.setdefault("type_name", "")
    payload.setdefault("description", "")
    return payload


def generate_dtc_analysis(dtc_code: str) -> dict:
    """
    Returns a dict:
      - ok: bool
      - error: str (if ok=False)
      - dtc: {code,type_name,description} (if found)
      - analysis: model JSON (if ok=True)
    """
    load_dotenv()

    code = normalize_dtc_code(dtc_code)
    if not DTC_RE.match(code):
        return {
            "ok": False,
            "error": "Invalid DTC format. Use something like P0420 (starts with P/C/B/U + 4 hex digits).",
        }

    db = DTCDatabase()
    dtc_info = get_dtc_info(db, code)
    if not dtc_info:
        return {
            "ok": False,
            "error": f"Information for {code} not found in your DTC database.",
        }

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"ok": False, "error": "Missing GEMINI_API_KEY in environment (.env)."}

    client = genai.Client(api_key=api_key)

    system_instruction = (
        "You are an automotive diagnostics assistant. "
        "You will be given a DTC code, its type, and its description.\n\n"
        "Return ONLY valid JSON with these keys:\n"
        "{\n"
        '  "issue_summary": string,\n'
        '  "severity_1_to_10": integer,\n'
        '  "severity_reasoning": string,\n'
        '  "common_causes": string[],\n'
        '  "quick_checks": string[],\n'
        '  "recommended_actions": string[],\n'
        '  "can_drive": "yes"|"no"|"depends",\n'
        '  "notes": string\n'
        "}\n\n"
        "Be concise and practical. If uncertain, say so in notes."
    )

    contents = (
        f"DTC: {dtc_info['code']}\n"
        f"Type: {dtc_info.get('type_name','')}\n"
        f"Description: {dtc_info.get('description','')}\n"
    )

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            # You can tune these if you want:
            temperature=0.3,
        ),
    )

    text = (response.text or "").strip()

    # Try to parse model JSON; if it isn't valid JSON, return raw text too.
    try:
        analysis = json.loads(text)
        return {"ok": True, "dtc": dtc_info, "analysis": analysis}
    except Exception:
        return {
            "ok": True,
            "dtc": dtc_info,
            "analysis": None,
            "raw_text": text,
            "warning": "Model did not return valid JSON; see raw_text.",
        }


if __name__ == "__main__":
    out = generate_dtc_analysis("P1516")
    print(json.dumps(out, indent=2))