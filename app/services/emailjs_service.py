import logging
import time
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)

TEMPORARY_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class EmailJSService:
    def __init__(
        self,
        client: httpx.Client | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        self.client = client
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def send_email(self, to_email: str, template_params: dict[str, Any]) -> dict[str, Any]:
        email_template_params = dict(template_params)
        template_id = email_template_params.pop("_template_id", None) or settings.EMAILJS_TEMPLATE_ID
        missing_settings = self._missing_settings(template_id)
        if missing_settings:
            return {
                "success": False,
                "status_code": None,
                "response": None,
                "error": f"Missing EmailJS settings: {', '.join(missing_settings)}",
            }

        payload = {
            "service_id": settings.EMAILJS_SERVICE_ID,
            "template_id": template_id,
            "user_id": settings.EMAILJS_PUBLIC_KEY,
            "accessToken": settings.EMAILJS_PRIVATE_KEY,
            "template_params": email_template_params,
        }
        headers = {"Content-Type": "application/json"}

        owns_client = self.client is None
        client = self.client or httpx.Client(timeout=self.timeout_seconds)

        try:
            for attempt in range(self.max_retries + 1):
                try:
                    logger.info(
                        "emailjs_send_attempt",
                        extra={"to_email": to_email, "attempt": attempt + 1},
                    )
                    response = client.post(settings.EMAILJS_API_URL, json=payload, headers=headers)

                    if response.status_code == 403 and settings.EMAILJS_PRIVATE_KEY:
                        logger.warning(
                            "emailjs_private_key_rejected_retrying_public_payload",
                            extra={"to_email": to_email, "attempt": attempt + 1},
                        )
                        public_payload = dict(payload)
                        public_payload.pop("accessToken", None)
                        response = client.post(settings.EMAILJS_API_URL, json=public_payload, headers=headers)

                    if response.status_code < 400:
                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "response": response.text,
                            "error": None,
                        }

                    if response.status_code in TEMPORARY_STATUS_CODES and attempt < self.max_retries:
                        logger.warning(
                            "emailjs_temporary_http_error",
                            extra={"to_email": to_email, "attempt": attempt + 1, "status_code": response.status_code},
                        )
                        time.sleep(1)
                        continue

                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "response": response.text,
                        "error": f"EmailJS HTTP error {response.status_code}",
                    }
                except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
                    if attempt < self.max_retries:
                        logger.warning(
                            "emailjs_temporary_request_error",
                            extra={"to_email": to_email, "attempt": attempt + 1, "error_type": type(exc).__name__},
                        )
                        time.sleep(1)
                        continue

                    return {
                        "success": False,
                        "status_code": None,
                        "response": None,
                        "error": type(exc).__name__,
                    }
        finally:
            if owns_client:
                client.close()

        return {
            "success": False,
            "status_code": None,
            "response": None,
            "error": "EmailJS request failed.",
        }

    @staticmethod
    def _missing_settings(template_id: str | None = None) -> list[str]:
        required_settings = {
            "EMAILJS_SERVICE_ID": settings.EMAILJS_SERVICE_ID,
            "EMAILJS_TEMPLATE_ID": template_id,
            "EMAILJS_PUBLIC_KEY": settings.EMAILJS_PUBLIC_KEY,
            "EMAILJS_PRIVATE_KEY": settings.EMAILJS_PRIVATE_KEY,
            "EMAILJS_API_URL": settings.EMAILJS_API_URL,
        }
        return [name for name, value in required_settings.items() if not value]
