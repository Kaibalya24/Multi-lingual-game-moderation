import json
import os
import re
from enum import Enum
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY:
    GEMINI_API_KEY = "AQ.Ab8RN6K-IG2yfWS6I4fMHm6fhAlRTDRC79QV9CercTzq-1pzbw"

client = genai.Client(api_key=GEMINI_API_KEY)

class ModerationVerdict(str, Enum):
    CLEAN = "CLEAN"
    TOXIC = "TOXIC"
    HARASSMENT = "HARASSMENT"


class GeminiModerator:
    """Uses official google-genai SDK with multi-model fallback and local safety guard."""

    # Models available on your account to try if one experiences a 503 spike
    ACTIVE_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]

    # Local guard to catch severe threats even during network/503 hiccups
    EMERGENCY_HARASSMENT_REGEX = [
        r"\b(jaan\s*se\s*maar|maar\s*dunga|goli\s*maar|murder|ter[ae]\s*ghar\s*aake)\b",
        r"\b(rape|mar\s*ja|suicide|bkl|madarchod|behenchod|bsdk|chutiya|gandu)\b"
    ]

    SYSTEM_PROMPT = """
You are a real-time multiplayer gaming chat moderator and multilingual translator specializing in casual code-mixed slang (e.g. Hinglish, Tanglish, regional gaming jargon).

Analyze the input message and perform two tasks:
1. CLASSIFY:
   - "HARASSMENT": Direct death threats, physical violence threats, severe sexual harassment, extreme abusive slurs (e.g., "jaan se maar dunga", "bkl", "tere ghar aake maarunga").
   - "TOXIC": Competitive gaming trash talk, calling someone a noob/loser/trash, telling them to uninstall, mild insults (e.g., "tera dimag kharab hai noob", "uninstall game idiot").
   - "CLEAN": Friendly banter, praise, normal gameplay chat, greetings (e.g., "bhai mast move tha", "nice game", "well played", "hello").

2. TRANSLATE:
   - Translate the natural meaning of the text into the requested Target Language.
   - If verdict is "HARASSMENT", set translated to "".

Return strictly JSON matching:
{
  "verdict": "CLEAN" | "TOXIC" | "HARASSMENT",
  "reason": "short explanation",
  "detected_lang": "detected language or dialect",
  "translated": "translated sentence in target language"
}
"""

    @classmethod
    def _local_check(cls, text: str) -> bool:
        low = text.lower()
        return any(re.search(pat, low) for pat in cls.EMERGENCY_HARASSMENT_REGEX)

    @classmethod
    def process_chat(cls, text: str, target_lang: str) -> dict:
        prompt = f"""
{cls.SYSTEM_PROMPT}

Input Message: "{text}"
Target Language: "{target_lang}"
"""
        last_error = None

        # Try models in order; if 3.8 is busy (503), automatically use 3.5
        for model_id in cls.ACTIVE_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )

                raw_json = response.text.strip()
                data = json.loads(raw_json)

                verdict = data.get("verdict", "CLEAN").upper()
                if verdict not in ["CLEAN", "TOXIC", "HARASSMENT"]:
                    verdict = "CLEAN"

                translated = data.get("translated", text)
                print(f"[Gemini Success: {model_id}] Verdict: {verdict} | Translated: '{translated}'")

                return {
                    "verdict": verdict,
                    "translated": translated,
                    "detected_lang": data.get("detected_lang", "Code-Mixed"),
                    "reason": data.get("reason", "")
                }
            except Exception as e:
                last_error = e
                continue

        # If all API endpoints temporarily 503, execute local safety guard
        print(f"\n[API 503 Notice]: Models busy, using fail-safe: {last_error}")
        if cls._local_check(text):
            return {
                "verdict": "HARASSMENT",
                "translated": "",
                "detected_lang": "Hinglish",
                "reason": "Detected explicit harassment/threat pattern (Local Fail-safe)"
            }

        return {
            "verdict": "CLEAN",
            "translated": text,
            "detected_lang": "Unknown",
            "reason": "Temporary network delay"
        }