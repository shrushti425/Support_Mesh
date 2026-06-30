import logging
import httpx
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger("supportmesh.webhook")

class WebhookService:
    async def trigger_webhook(self, payload: Dict[str, Any]) -> bool:
        if not settings.WEBHOOK_URL:
            logger.info("Webhook URL is not configured. Skipping webhook trigger.")
            return False

        logger.info(f"Triggering webhook to {settings.WEBHOOK_URL}...")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    settings.WEBHOOK_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook delivered successfully: Status {response.status_code}")
                    return True
                else:
                    logger.error(f"Webhook delivered with warning: Status {response.status_code}, Response: {response.text}")
                    return False
        except httpx.HTTPError as e:
            logger.error(f"HTTP error while calling webhook: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error calling webhook: {e}")
            return False

# Singleton instance
webhook_service = WebhookService()
