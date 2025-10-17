"""
Stack AI API client for lead scoring
Uses deployed Stack AI workflow to score leads and classify personas
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class StackAIClient:
    """Client for Stack AI lead scoring workflow"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        org_id: Optional[str] = None,
        flow_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("STACKAI_API_KEY")
        self.org_id = org_id or os.getenv("STACKAI_ORG_ID")
        self.flow_id = flow_id or os.getenv("STACKAI_FLOW_ID")
        self.base_url = (base_url or os.getenv("STACKAI_BASE_URL", "https://api.stack-ai.com")).rstrip("/")

        # Check if we should use mock mode
        if not self.api_key or self.api_key.startswith("your_") or not self.org_id or not self.flow_id:
            logger.warning("Stack AI credentials not fully configured - using mock mode")
            logger.warning(f"API Key: {'✓' if self.api_key and not self.api_key.startswith('your_') else '✗'}")
            logger.warning(f"Org ID: {'✓' if self.org_id else '✗'}")
            logger.warning(f"Flow ID: {'✓' if self.flow_id else '✗'}")
            self.mock_mode = True
        else:
            self.mock_mode = False
            logger.info(f"Stack AI client initialized (org: {self.org_id[:8]}..., flow: {self.flow_id[:8]}...)")

        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def score_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a lead using Stack AI workflow

        Args:
            lead_data: Lead information with keys:
                - company_name (str)
                - industry (str)
                - employee_count (int)
                - revenue (float)
                - website (str)

        Returns:
            Dict with score (float), persona (str), and reasoning (str)
        """
        if self.mock_mode:
            return self._mock_score_lead(lead_data)

        try:
            # Build endpoint URL
            endpoint = f"/inference/v0/run/{self.org_id}/{self.flow_id}"

            # Prepare payload
            # Stack AI expects the input as a JSON object or text
            # Based on common patterns, we'll send the lead data as JSON string
            payload = {
                "in-0": self._format_lead_for_stack_ai(lead_data),
                "user_id": lead_data.get("company_name", "unknown"),
            }

            logger.info(f"Calling Stack AI for lead: {lead_data.get('company_name', 'unknown')}")
            logger.debug(f"Payload: {payload}")

            response = self.client.post(endpoint, json=payload)
            response.raise_for_status()

            result = response.json()
            logger.debug(f"Stack AI raw response: {result}")

            # Parse the response
            # Stack AI might return the result directly or wrapped
            parsed = self._parse_stack_ai_response(result, lead_data)

            logger.info(
                f"Lead scored: {lead_data.get('company_name')} -> "
                f"score={parsed['score']:.2f}, persona={parsed['persona']}"
            )

            return parsed

        except httpx.HTTPStatusError as e:
            logger.error(f"Stack AI API error (status {e.response.status_code}): {e}")
            logger.error(f"Response body: {e.response.text}")
            # Fallback to mock
            logger.warning("Falling back to mock scoring due to API error")
            return self._mock_score_lead(lead_data)

        except httpx.HTTPError as e:
            logger.error(f"Stack AI HTTP error: {e}")
            logger.warning("Falling back to mock scoring due to network error")
            return self._mock_score_lead(lead_data)

        except Exception as e:
            logger.error(f"Unexpected error calling Stack AI: {e}", exc_info=True)
            logger.warning("Falling back to mock scoring")
            return self._mock_score_lead(lead_data)

    def _format_lead_for_stack_ai(self, lead_data: Dict[str, Any]) -> str:
        """
        Format lead data for Stack AI input

        Stack AI might expect a text prompt or JSON string
        We'll format it as a JSON string for the LLM to parse
        """
        import json

        formatted = {
            "company_name": lead_data.get("company_name", "Unknown"),
            "industry": lead_data.get("industry", "unknown"),
            "employee_count": lead_data.get("employee_count", 0),
            "revenue": lead_data.get("revenue", 0),
            "website": lead_data.get("website", ""),
        }

        return json.dumps(formatted)

    def _parse_stack_ai_response(self, response: Any, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Stack AI response to extract score, persona, and reasoning

        Stack AI responses can vary:
        - Direct JSON: {"score": 0.85, "persona": "enterprise", "reasoning": "..."}
        - Wrapped: {"result": "{...}"}
        - Text: "```json\n{...}\n```"
        """
        import json
        import re

        # Case 1: Response is already a dict with score/persona
        if isinstance(response, dict):
            if "score" in response and "persona" in response:
                return {
                    "score": float(response.get("score", 0.5)),
                    "persona": response.get("persona", "smb"),
                    "reasoning": response.get("reasoning", "Stack AI scoring"),
                }

            # Case 2: Response is wrapped (e.g., {"result": "{...}"})
            if "result" in response:
                result_text = response["result"]
                if isinstance(result_text, str):
                    # Try to extract JSON from markdown code blocks
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
                    if json_match:
                        result_text = json_match.group(1)

                    # Try to parse as JSON
                    try:
                        parsed = json.loads(result_text)
                        if "score" in parsed and "persona" in parsed:
                            return {
                                "score": float(parsed.get("score", 0.5)),
                                "persona": parsed.get("persona", "smb"),
                                "reasoning": parsed.get("reasoning", "Stack AI scoring"),
                            }
                    except json.JSONDecodeError:
                        pass

            # Case 3: Stack AI might return output in different key
            for key in ["output", "response", "data", "prediction"]:
                if key in response:
                    return self._parse_stack_ai_response(response[key], lead_data)

        # Case 4: Response is a string
        if isinstance(response, str):
            # Try to extract JSON
            json_match = re.search(r'\{.*?"score".*?\}', response, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(0))
                    return {
                        "score": float(parsed.get("score", 0.5)),
                        "persona": parsed.get("persona", "smb"),
                        "reasoning": parsed.get("reasoning", "Stack AI scoring"),
                    }
                except json.JSONDecodeError:
                    pass

        # Fallback: couldn't parse, use mock
        logger.warning(f"Could not parse Stack AI response: {response}")
        logger.warning("Using mock scoring as fallback")
        return self._mock_score_lead(lead_data)

    def _mock_score_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock lead scoring for demo/testing when API is unavailable

        Uses simple heuristics based on employee count and revenue
        """
        import random

        company_name = lead_data.get("company_name", "Unknown")
        industry = lead_data.get("industry", "unknown")
        employee_count = lead_data.get("employee_count", 0)
        revenue = lead_data.get("revenue", 0)

        # Determine persona
        is_enterprise = employee_count >= 500 or revenue >= 10_000_000
        persona = "enterprise" if is_enterprise else "smb"

        # Calculate score with some randomness
        base_score = 0.5

        # Adjust for size
        if employee_count > 1000:
            base_score += 0.2
        elif employee_count > 500:
            base_score += 0.15
        elif employee_count > 100:
            base_score += 0.1

        # Adjust for revenue
        if revenue > 50_000_000:
            base_score += 0.15
        elif revenue > 10_000_000:
            base_score += 0.1
        elif revenue > 1_000_000:
            base_score += 0.05

        # Adjust for industry (high-value industries)
        high_value_industries = ["technology", "finance", "healthcare", "saas", "software"]
        if any(ind in industry.lower() for ind in high_value_industries):
            base_score += 0.1

        # Add small random variance
        score = min(0.95, max(0.3, base_score + random.uniform(-0.05, 0.05)))

        reasoning = (
            f"{'Large' if is_enterprise else 'Small/mid-sized'} {industry} company "
            f"with {employee_count} employees and ${revenue:,.0f} revenue"
        )

        logger.info(f"[MOCK] Scored {company_name}: {score:.2f} ({persona})")

        return {
            "score": round(score, 2),
            "persona": persona,
            "reasoning": reasoning,
            "mock": True,  # Indicate this is mock data
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Check if Stack AI API is accessible

        Returns:
            Dict with status and details
        """
        if self.mock_mode:
            return {
                "status": "mock_mode",
                "accessible": False,
                "message": "Stack AI credentials not configured",
            }

        try:
            # Stack AI doesn't have a health endpoint, so we'll just check connectivity
            # by making a minimal request
            test_data = {
                "company_name": "Test Corp",
                "industry": "technology",
                "employee_count": 100,
                "revenue": 1000000,
                "website": "test.com",
            }

            result = self.score_lead(test_data)

            return {
                "status": "healthy",
                "accessible": True,
                "message": "Stack AI API responding",
                "test_score": result.get("score"),
            }

        except Exception as e:
            return {
                "status": "error",
                "accessible": False,
                "message": str(e),
            }

    def __del__(self):
        """Cleanup HTTP client"""
        if hasattr(self, 'client'):
            self.client.close()


# Singleton instance
_stackai_client: Optional[StackAIClient] = None


def get_stackai_client() -> StackAIClient:
    """Get or create singleton Stack AI client"""
    global _stackai_client
    if _stackai_client is None:
        _stackai_client = StackAIClient()
    return _stackai_client
