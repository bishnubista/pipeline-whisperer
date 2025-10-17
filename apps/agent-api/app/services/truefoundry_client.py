"""
Truefoundry API client for deploying and running AI agents
Handles personalized message generation via Truefoundry-hosted micro-agents
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TruefoundryClient:
    """Client for Truefoundry AI agent platform"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        workspace: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("TRUEFOUNDRY_API_KEY")
        self.workspace = workspace or os.getenv("TRUEFOUNDRY_WORKSPACE")
        self.base_url = (base_url or os.getenv("TRUEFOUNDRY_BASE_URL", "https://api.truefoundry.com")).rstrip("/")

        if not self.api_key or self.api_key.startswith("your_"):
            logger.warning("Truefoundry API key not configured - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False

        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def generate_personalized_message(
        self,
        template: str,
        lead_data: Dict[str, Any],
        personalization_prompt: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Generate personalized outreach message using Truefoundry AI agent

        Args:
            template: Message template with {{variables}}
            lead_data: Lead information for personalization
            personalization_prompt: Instructions for AI personalization
            config: Additional configuration (tone, length, etc.)

        Returns:
            Dict with 'subject' and 'body' keys
        """
        if self.mock_mode:
            return self._mock_generate_message(template, lead_data)

        try:
            payload = {
                "workspace": self.workspace,
                "template": template,
                "lead_data": lead_data,
                "personalization_instructions": personalization_prompt or "Personalize this message professionally",
                "config": config or {},
            }

            response = self.client.post("/v1/agents/personalize", json=payload)
            response.raise_for_status()

            result = response.json()
            return {
                "subject": result.get("subject", ""),
                "body": result.get("body", template),
            }

        except httpx.HTTPError as e:
            logger.error(f"Truefoundry API error: {e}")
            # Fallback to template rendering
            return self._mock_generate_message(template, lead_data)

    def _mock_generate_message(self, template: str, lead_data: Dict[str, Any]) -> Dict[str, str]:
        """Mock message generation for testing/demo"""
        # Simple variable replacement
        body = template
        for key, value in lead_data.items():
            body = body.replace(f"{{{{{key}}}}}", str(value))

        # Extract subject if template has it
        subject = lead_data.get("company_name", "Your Company") + " x Pipeline Whisperer"

        logger.info(f"Mock mode: Generated message for {lead_data.get('contact_name', 'contact')}")

        return {
            "subject": subject,
            "body": body,
        }

    def deploy_agent(self, agent_config: Dict[str, Any]) -> str:
        """
        Deploy a new AI agent to Truefoundry platform

        Args:
            agent_config: Agent configuration (model, prompts, tools, etc.)

        Returns:
            Agent deployment ID
        """
        if self.mock_mode:
            logger.info("Mock mode: Skipping agent deployment")
            return "mock-agent-deployment-id"

        try:
            response = self.client.post("/v1/agents/deploy", json=agent_config)
            response.raise_for_status()
            result = response.json()
            return result.get("deployment_id", "")

        except httpx.HTTPError as e:
            logger.error(f"Truefoundry deployment error: {e}")
            raise

    def __del__(self):
        """Cleanup HTTP client"""
        if hasattr(self, 'client'):
            self.client.close()


# Singleton instance
_truefoundry_client: Optional[TruefoundryClient] = None


def get_truefoundry_client() -> TruefoundryClient:
    """Get or create singleton Truefoundry client"""
    global _truefoundry_client
    if _truefoundry_client is None:
        _truefoundry_client = TruefoundryClient()
    return _truefoundry_client
