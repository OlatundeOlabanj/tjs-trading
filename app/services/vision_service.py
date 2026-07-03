"""
Vision Service — reads Bybit trade screenshots using Groq's vision model.
Extracts symbol, side, entry/exit price, P&L % so the user doesn't have
to type outcome data by hand. User still confirms before it's saved —
this is a pre-fill assistant, not an auto-submit.
"""
import base64
import json
import logging
import re
from typing import Optional

from groq import Groq

logger = logging.getLogger(__name__)

# Groq's vision-capable model. Update here if Groq deprecates/renames it —
# this is the only place the vision model string lives.
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

VISION_PROMPT = """You are reading a screenshot of a closed crypto trade from a trading app (likely Bybit).

Extract the following information from the image:
- symbol: the trading pair shown (e.g. "BTCUSDT", "ETHUSDT")
- side: "Buy"/"Long" or "Sell"/"Short"
- entry_price: the entry/avg price shown
- exit_price: the closing/mark price shown
- pnl_pct: the realized PNL percentage shown (include the sign, e.g. -5.2 or +42.0)
- pnl_amount: the realized PNL in currency if shown (e.g. 12.45)
- result: classify as one of "hit_target" (clear win, PNL positive and matches a target),
  "stopped_out" (clear loss), "partial" (small win, less than expected), or "missed" if unclear

If any field is not visible or not present in the screenshot, set it to null.
Be precise — only extract numbers you can actually see, never guess.

Return ONLY a raw JSON object, no markdown, no explanation:

{
  "symbol": "<string or null>",
  "side": "<string or null>",
  "entry_price": <float or null>,
  "exit_price": <float or null>,
  "pnl_pct": <float or null>,
  "pnl_amount": <float or null>,
  "result": "<hit_target|stopped_out|partial|missed>",
  "confidence": "<high|medium|low>",
  "notes": "<one short sentence describing what you saw>"
}"""


class VisionService:
    def __init__(self, api_key: str):
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set.")
        self.client = Groq(api_key=api_key)

    def read_trade_screenshot(self, image_bytes: bytes, mime_type: str = "image/png") -> Optional[dict]:
        """
        Send a screenshot to Groq's vision model and extract trade outcome data.
        Returns a dict matching the Outcome model fields, or None on failure.
        """
        try:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{b64_image}"

            response = self.client.chat.completions.create(
                model=GROQ_VISION_MODEL,
                max_tokens=512,
                temperature=0.1,  # low temp — this is extraction, not creativity
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_PROMPT},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
            )

            raw = response.choices[0].message.content
            if not raw:
                logger.warning("Empty vision response")
                return None

            return self._parse(raw)

        except Exception as e:
            logger.error(f"Vision read error: {e}")
            return None

    def _parse(self, raw: str) -> Optional[dict]:
        text = re.sub(r"```(?:json)?", "", raw.strip()).strip().rstrip("`")
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            logger.error(f"No JSON in vision response: {text[:150]}")
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            logger.error(f"Vision JSON parse error: {e}")
            return None

        if data.get("result") not in ("hit_target", "stopped_out", "partial", "missed"):
            data["result"] = "missed"

        return data
