import json
import logging
import os
import time
from html.parser import HTMLParser

import requests

logger = logging.getLogger("scraper")

LLM_API_KEY = os.getenv("LLM_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

MODELS = [
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b",
]


class RateLimitError(Exception):
    pass


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())


def html_to_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return " ".join(parser.text)


class LLMService:
    """LLM service using Groq with automatic fallback between models on rate limit."""

    def _chat(self, prompt: str, model: str, json_mode: bool = False) -> str:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(
            GROQ_BASE_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

        if response.status_code == 429:
            raise RateLimitError(f"Rate limited on model {model}")

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _chat_with_fallback(self, prompt: str, json_mode: bool = False) -> str | None:
        last_error = None

        for model in MODELS:
            try:
                logger.info(f"Attempting LLM call with model: {model}")
                result = self._chat(prompt, model, json_mode)
                return result
            except RateLimitError as e:
                logger.warning(f"Rate limited on {model}, trying next. Error: {e}")
                last_error = e
                time.sleep(1)
                continue
            except Exception as e:
                logger.error(f"LLM error with model {model}: {e}")
                last_error = e
                continue

        logger.error(f"All models failed. Last error: {last_error}")
        return None

    def send_prompt(self, prompt: str) -> str | None:
        return self._chat_with_fallback(prompt)

    def extract_article(self, html: str) -> dict:
        plain_text = html_to_text(html)
        result = self._chat_with_fallback(
            f"""Extract the title and main article content from this webpage text.
Ignore navigation menus, ads, footers, and sidebars.
Return ONLY valid JSON like this: {{"title": "...", "content": "..."}}

Page text:
{plain_text[:6000]}""",
            json_mode=True,
        )
        try:
            return json.loads(result) if result else {}
        except Exception:
            return {}
