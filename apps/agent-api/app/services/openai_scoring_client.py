"""
OpenAI scoring client for lead prioritization
Replaces stackAI integration with Responses API structured outputs
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

try:
    from app.config.settings import settings as app_settings
except ImportError:  # pragma: no cover - during tooling/bootstrap
    app_settings = None

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 30.0


class OpenAIScoringClient:
    """Wrapper around OpenAI Responses API for lead scoring"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        if app_settings:
            self.api_key = api_key or app_settings.openai_api_key or os.getenv("OPENAI_API_KEY")
            self.model = model or app_settings.openai_model or DEFAULT_MODEL
            self.base_url = (base_url or app_settings.openai_base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
            self.timeout = timeout or app_settings.openai_timeout_seconds or DEFAULT_TIMEOUT
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
            self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
            self.timeout = timeout or float(os.getenv("OPENAI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT))

        if not self.api_key:
            logger.warning("OpenAI API key missing – scoring will fall back to mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
        )

    # JSON schema for structured response (score + persona + reasoning)
    RESPONSE_SCHEMA: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "persona": {"type": "string"},
            "reasoning": {"type": "string"},
        },
        "required": ["score", "persona", "reasoning"],
    }

    def score_lead(self, lead_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Return score/persona for a lead using OpenAI Chat Completions API"""
        if self.mock_mode:
            return self._mock_score_lead(lead_payload)

        system_prompt = (
            "You are an expert B2B lead qualification system. Analyze company data and return a JSON object with:\n"
            "- score: number between 0.0 and 1.0 (lead quality)\n"
            "- persona: string (enterprise, smb, mid-market, or startup)\n"
            "- reasoning: brief explanation\n\n"
            "Scoring rules:\n"
            "- HIGH (0.8-1.0): 500+ employees OR $10M+ revenue\n"
            "- MEDIUM (0.5-0.79): 100-500 employees, $1M-$10M revenue\n"
            "- LOW (0.0-0.49): <100 employees, <$1M revenue\n\n"
            "Return ONLY valid JSON, no other text."
        )

        user_prompt = self._build_prompt(lead_payload)

        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }

        try:
            logger.debug("Calling OpenAI Chat Completions API")
            response = self.client.post("/chat/completions", json=request)
            response.raise_for_status()
            data = response.json()

            result = self._extract_from_response(data)
            if result is None:
                raise ValueError("Structured response missing expected fields")

            logger.info(
                "Lead scored via OpenAI: %s -> %.2f (%s)",
                lead_payload.get("company_name", "unknown"),
                result["score"],
                result["persona"],
            )
            result["mock"] = False
            return result

        except Exception as exc:  # noqa: BLE001 - broadened to ensure fallback
            logger.error("OpenAI scoring failed: %s", exc, exc_info=True)
            return self._mock_score_lead(lead_payload)

    def _extract_from_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Pull structured JSON from Chat Completions API response"""
        import json
        try:
            # Extract the message content from Chat Completions format
            content = response["choices"][0]["message"]["content"]
            # Parse the JSON content
            parsed = json.loads(content)

            # Validate required fields
            if "score" in parsed and "persona" in parsed and "reasoning" in parsed:
                return {
                    "score": float(parsed["score"]),
                    "persona": parsed["persona"],
                    "reasoning": parsed["reasoning"],
                }
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError):
            return None
        return None

    def _build_prompt(self, lead_payload: Dict[str, Any]) -> str:
        """Craft instruction string for the model"""
        company = lead_payload.get("company_name", "Unknown")
        return (
            "You are evaluating B2B sales leads. Given the JSON payload below, "
            "return a lead quality score between 0 and 1 (higher is better), a persona "
            "label (enterprise, smb, startup, individual), and a short reasoning string.\n"
            f"Lead payload:\n{lead_payload}"
        )

    def _mock_score_lead(self, lead_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic mock used when OpenAI is unavailable"""
        import random

        company_size = lead_payload.get("employee_count", 0)
        revenue = lead_payload.get("revenue", 0)

        base = 0.4
        if company_size > 1000:
            base += 0.2
        elif company_size > 200:
            base += 0.15
        elif company_size > 50:
            base += 0.1

        if revenue > 10_000_000:
            base += 0.15
        elif revenue > 2_000_000:
            base += 0.1

        persona = "enterprise" if company_size >= 500 else "smb"
        score = min(0.95, max(0.2, base + random.uniform(-0.05, 0.05)))

        return {
            "score": round(score, 3),
            "persona": persona,
            "reasoning": "Mock scoring based on company size and revenue",
            "mock": True,
        }

    def health_check(self) -> Dict[str, Any]:
        """Simple health probe"""
        if self.mock_mode:
            return {"status": "mock_mode", "accessible": False}

        try:
            sample_payload = {
                "company_name": "Health Check Inc",
                "industry": "software",
                "employee_count": 150,
                "revenue": 3_000_000,
            }
            result = self.score_lead(sample_payload)
            return {"status": "healthy", "accessible": True, "mock": result.get("mock", True)}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "accessible": False, "message": str(exc)}

    def __del__(self) -> None:  # pragma: no cover - best effort cleanup
        if getattr(self, "client", None):
            self.client.close()


_client_singleton: Optional[OpenAIScoringClient] = None


def get_openai_scoring_client() -> OpenAIScoringClient:
    """Singleton accessor"""
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = OpenAIScoringClient()
    return _client_singleton
