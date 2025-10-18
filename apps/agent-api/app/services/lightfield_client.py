"""
Lightfield API client for sending outreach messages
Handles email/LinkedIn messaging via Lightfield platform
"""
import os
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone

try:
    from app.config.settings import settings as app_settings
except ImportError:
    app_settings = None

logger = logging.getLogger(__name__)


class LightfieldClient:
    """Client for Lightfield outreach platform"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        simulate: Optional[bool] = None,
    ):
        if app_settings:
            self.api_key = api_key or app_settings.lightfield_api_key or os.getenv("LIGHTFIELD_API_KEY")
            self.base_url = (base_url or app_settings.lightfield_base_url or os.getenv("LIGHTFIELD_BASE_URL", "https://api.lightfield.ai/v1")).rstrip("/")
            default_simulate = app_settings.simulate_lightfield
        else:
            self.api_key = api_key or os.getenv("LIGHTFIELD_API_KEY")
            self.base_url = (base_url or os.getenv("LIGHTFIELD_BASE_URL", "https://api.lightfield.ai/v1")).rstrip("/")
            default_simulate = os.getenv("SIMULATE_LIGHTFIELD", "true").lower() == "true"

        # Check if we should simulate (for demo/testing)
        if simulate is None:
            simulate = default_simulate
        self.simulate = bool(simulate)

        if not self.api_key or self.api_key.startswith("your_") or self.simulate:
            logger.info("Lightfield API in simulation mode (API key not configured or SIMULATE_LIGHTFIELD=true)")
            self.mock_mode = True
        else:
            self.mock_mode = False

        self.client = None
        if not self.mock_mode:
            self.client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        from_name: Optional[str] = None,
        tracking_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send personalized email via Lightfield

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject line
            body: Email body (HTML or plain text)
            from_name: Sender name (optional)
            tracking_id: Internal tracking ID for this message

        Returns:
            Dict with message_id and status
        """
        if self.mock_mode:
            return self._mock_send_email(to_email, to_name, subject, tracking_id)

        try:
            payload = {
                "to": {
                    "email": to_email,
                    "name": to_name,
                },
                "from": {
                    "name": from_name or "Pipeline Whisperer",
                },
                "subject": subject,
                "body": body,
                "tracking_id": tracking_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            response = self.client.post("/messages/email/send", json=payload)
            response.raise_for_status()

            result = response.json()
            return {
                "message_id": result.get("message_id"),
                "status": "sent",
                "provider": "lightfield",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }

        except httpx.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            body = getattr(getattr(e, "response", None), "text", None)
            logger.error(f"Lightfield API error status={status}: {e}; body={body}")
            return {
                "message_id": None,
                "status": "failed",
                "error": str(e),
            }

    def _mock_send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        tracking_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mock email sending for testing/demo"""
        import uuid

        message_id = f"lf_msg_{uuid.uuid4().hex[:16]}"

        logger.info(
            f"📧 [SIMULATED] Email sent to {to_name} <{to_email}>\n"
            f"   Subject: {subject}\n"
            f"   Message ID: {message_id}\n"
            f"   Tracking ID: {tracking_id}"
        )

        return {
            "message_id": message_id,
            "status": "sent",
            "provider": "lightfield-simulator",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "simulated": True,
        }

    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get delivery/engagement status of a sent message

        Args:
            message_id: Lightfield message ID

        Returns:
            Dict with status, opened_at, clicked_at, etc.
        """
        if self.mock_mode:
            return {
                "message_id": message_id,
                "status": "delivered",
                "delivered_at": datetime.now(timezone.utc).isoformat(),
                "simulated": True,
            }

        try:
            response = self.client.get(f"/messages/{message_id}/status")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            body = getattr(getattr(e, "response", None), "text", None)
            logger.error(f"Lightfield status check error status={status}: {e}; body={body}")
            return {"message_id": message_id, "status": "unknown", "error": str(e)}

    def close(self):
        """Explicitly close HTTP client"""
        if getattr(self, 'client', None):
            self.client.close()

    def __del__(self):
        """Cleanup HTTP client"""
        self.close()


# Singleton instance
_lightfield_client: Optional[LightfieldClient] = None


def get_lightfield_client() -> LightfieldClient:
    """Get or create singleton Lightfield client"""
    global _lightfield_client
    if _lightfield_client is None:
        _lightfield_client = LightfieldClient()
    return _lightfield_client
