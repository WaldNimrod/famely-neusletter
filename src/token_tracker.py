"""
Famely Neuslettr — Token Tracker
Wraps Claude API calls, logs token usage per LOD400 §11.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from .db import Database

logger = logging.getLogger('famely.tokens')

# Pricing per million tokens (USD)
PRICING = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
}


class TokenTracker:
    """Wraps Anthropic client. Logs every API call to token_usage table."""

    def __init__(self, db: Database, api_key: Optional[str] = None, mock: bool = False):
        self.db = db
        self.mock = mock
        self.client = None

        if not mock:
            api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                try:
                    import anthropic
                    self.client = anthropic.Anthropic(api_key=api_key)
                except ImportError:
                    logger.warning("anthropic SDK not available, falling back to requests")
                    self._api_key = api_key
            else:
                logger.warning("No ANTHROPIC_API_KEY, falling back to mock mode")
                self.mock = True

    def generate(self, module: str, operation: str,
                 prompt: str, max_tokens: int,
                 model: str = "claude-sonnet-4-6",
                 newsletter_date: Optional[str] = None,
                 system: Optional[str] = None) -> str:
        """Call Claude API and log usage. Returns response text."""
        if self.mock:
            return self._mock_generate(module, operation, prompt, model, newsletter_date)

        # Try anthropic SDK first, then fall back to requests
        for attempt in range(3):
            try:
                if self.client:
                    return self._call_sdk(module, operation, prompt, max_tokens,
                                          model, newsletter_date, system)
                else:
                    return self._call_http(module, operation, prompt, max_tokens,
                                           model, newsletter_date, system)
            except Exception as e:
                wait = 2 ** (attempt + 1)
                logger.warning(f"[TokenTracker] Attempt {attempt+1} failed: {e}. Retrying in {wait}s")
                time.sleep(wait)

        logger.error(f"[TokenTracker] All retries failed for {module}/{operation}")
        raise RuntimeError(f"Claude API failed after 3 retries: {module}/{operation}")

    def _call_sdk(self, module, operation, prompt, max_tokens, model, newsletter_date, system):
        """Call via anthropic SDK."""
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        text = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        self._log(module, operation, model, input_tokens, output_tokens, cost, newsletter_date)
        return text

    def _call_http(self, module, operation, prompt, max_tokens, model, newsletter_date, system):
        """Call via HTTP requests (fallback if SDK unavailable)."""
        import requests

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system

        resp = requests.post("https://api.anthropic.com/v1/messages",
                            headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        text = data["content"][0]["text"]
        input_tokens = data["usage"]["input_tokens"]
        output_tokens = data["usage"]["output_tokens"]
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        self._log(module, operation, model, input_tokens, output_tokens, cost, newsletter_date)
        return text

    def _mock_generate(self, module, operation, prompt, model, newsletter_date):
        """Return mock responses for testing."""
        mock_cost = 0.001
        self._log(module, operation, model, 100, 50, mock_cost, newsletter_date)

        if operation == 'greeting':
            return "בוקר טוב, בית ולד! ☀️ היום ב-9 באפריל 1865 הסתיימה מלחמת האזרחים האמריקנית. יום מצוין לקריאה!"
        elif operation == 'greeting_en':
            return "Good morning! On this day in 1865, the American Civil War ended. A great day for reading!"
        elif operation == 'puzzle':
            return "חידת היום 🧩\nבכיתה של צליל יש 30 תלמידים. כל תלמיד לוחץ יד לכל תלמיד אחר בדיוק פעם אחת. כמה לחיצות יד בסה\"כ?\n\n(רמז: חשבו על צירופים)\n\nתשובת אתמול: 42"
        elif operation == 'puzzle_answer':
            return "435 (30×29÷2)"
        elif operation == 'survey':
            return "מה הכתבה שהכי הפתיעה אתכם היום? למה?"
        elif operation == 'survey_en':
            return "What article surprised you most today? Why?"
        elif operation == 'summary':
            return _mock_summary(prompt)
        elif operation == 'headline':
            return _mock_headline(prompt)
        elif operation == 'submission_edit':
            return json.dumps({"headline": "ידיעה מהמשפחה", "summary": "תוכן שנשלח על ידי בן משפחה."}, ensure_ascii=False)
        elif operation == 'bridge':
            return "נימרוד חשב שזה יעניין אותך!"
        else:
            return f"[Mock response for {operation}]"

    def _log(self, module, operation, model, input_tokens, output_tokens, cost, newsletter_date):
        """Log token usage to DB."""
        ts = datetime.now(timezone.utc).isoformat()
        try:
            self.db.log_token_usage(ts, module, operation, model,
                                     input_tokens, output_tokens, cost, newsletter_date)
        except Exception as e:
            logger.error(f"Failed to log token usage: {e}")
        logger.info(f"[Tokens] {module}/{operation}: {input_tokens}+{output_tokens} tokens, ${cost:.4f}")

    @staticmethod
    def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost based on Anthropic pricing."""
        pricing = PRICING.get(model, PRICING["claude-sonnet-4-6"])
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        return round(cost, 6)


def _mock_summary(prompt: str) -> str:
    """Generate context-appropriate mock summary."""
    if 'sailing' in prompt.lower() or 'הפלגה' in prompt:
        return "מדריך מקיף למסלולי הפלגה חדשים בים התיכון, כולל עגינות חדשות ונקודות חן מוסתרות."
    elif 'kite' in prompt.lower() or 'קייט' in prompt:
        return "טכנולוגיית הידרופויל חדשה משנה את עולם הקייטסרפינג התחרותי עם מהירויות חסרות תקדים."
    elif 'architecture' in prompt.lower() or 'אדריכלות' in prompt:
        return "פרויקט בנייה ירוקה חדשני בתל אביב משלב passive house עם עיצוב ישראלי. חיסכון של 60% באנרגיה."
    elif 'chemistry' in prompt.lower():
        return "A novel catalyst enables previously impossible organic reactions at room temperature, opening new synthesis pathways."
    elif 'circus' in prompt.lower() or 'קרקס' in prompt:
        return "בית הספר CNAC בצרפת פתח הרשמה לאודישנים. הזדמנות מצוינת לאמנים צעירים."
    elif 'math' in prompt.lower() or 'מתמטיקה' in prompt:
        return "סרטון חדש של Numberphile חוקר בעיות מתמטיות שוות מיליון דולר ומסביר למה עדיין לא נפתרו."
    return "תוכן מעניין ורלוונטי שנמצא עבורך במקורות המידע שלנו."


def _mock_headline(prompt: str) -> str:
    """Generate mock headline."""
    if 'sailing' in prompt.lower():
        return "מדריך ההפלגות של 2026 בים התיכון"
    elif 'kite' in prompt.lower():
        return "טכנולוגיית פויל חדשה שוברת שיאי מהירות"
    return "כותרת לדוגמה"
