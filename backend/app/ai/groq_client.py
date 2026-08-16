from __future__ import annotations

from typing import Any, Dict, List, Optional
import os

from app.logging.logger import get_logger
from app.ai.safety import AISafetyWrapper

logger = get_logger(__name__)


class GroqClient:
    """
    Optional Groq LLM client for the Enterprise Decision Engine.

    All answers are grounded in data analysis; the LLM is used only
    for natural language generation on top of verified analytics results.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self._client = None
        if self.api_key:
            try:
                from groq import Groq as _GroqClient
                self._client = _GroqClient(api_key=self.api_key)
            except Exception as exc:
                logger.warning("[Groq] Could not initialize client: %s", exc)

    def is_configured(self) -> bool:
        return self._client is not None

    def generate(
        self,
        prompt: str,
        system_prompt: str = "You are an expert business analyst. Ground every answer in the provided evidence. Never hallucinate.",
        model: str = "llama-3.3-70b-vers-versatile",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        evidence_block: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._client:
            return {"content": "", "error": "Groq client not configured", "model": model}

        if evidence_block:
            prompt = AISafetyWrapper.enforce_evidence_in_llm_prompt(system_prompt, evidence_block, prompt)

        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content if response.choices else ""
            usage = {}
            if hasattr(response, "usage"):
                usage = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                }
            return {
                "content": content,
                "model": model,
                "error": None,
                "usage": usage,
            }
        except Exception as exc:
            logger.error("[Groq] Generation failed: %s", exc)
            return {"content": "", "error": str(exc), "model": model}
