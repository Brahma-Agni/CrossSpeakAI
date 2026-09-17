"""Minimal Razorpay client and signature validation for paid-plan checkout."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class BillingError(RuntimeError):
    """A safe, user-facing billing failure."""


def _hmac_sha256(message: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_payment_signature(
    order_id: str,
    payment_id: str,
    received_signature: str,
    key_secret: str,
) -> bool:
    """Validate the signature returned by Razorpay Checkout."""
    expected = _hmac_sha256(
        f"{order_id}|{payment_id}".encode("utf-8"), key_secret
    )
    return hmac.compare_digest(expected, received_signature)


def verify_webhook_signature(
    raw_body: bytes, received_signature: str, webhook_secret: str
) -> bool:
    """Validate a Razorpay webhook against its unmodified request body."""
    expected = _hmac_sha256(raw_body, webhook_secret)
    return hmac.compare_digest(expected, received_signature)


@dataclass(frozen=True)
class RazorpayClient:
    """Small REST client; avoids adding a payment SDK for three API calls."""

    key_id: str
    key_secret: str
    base_url: str = "https://api.razorpay.com/v1"

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        credentials = base64.b64encode(
            f"{self.key_id}:{self.key_secret}".encode("utf-8")
        ).decode("ascii")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                details = json.loads(exc.read().decode("utf-8"))
                description = details.get("error", {}).get("description")
            except Exception:
                description = None
            raise BillingError(description or "Payment provider rejected the request.") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise BillingError("Payment provider is temporarily unavailable.") from exc

    def create_order(
        self, amount: int, currency: str, receipt: str
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/orders",
            {
                "amount": amount,
                "currency": currency,
                "receipt": receipt,
            },
        )

    def fetch_payment(self, payment_id: str) -> dict[str, Any]:
        safe_id = quote(payment_id, safe="")
        return self._request("GET", f"/payments/{safe_id}")


def validate_captured_payment(
    payment: dict[str, Any],
    *,
    payment_id: str,
    order_id: str,
    amount: int,
    currency: str,
) -> None:
    """Reject a provider response that does not exactly match our order."""
    if str(payment.get("id")) != payment_id:
        raise BillingError("Payment identifier did not match the order.")
    if str(payment.get("order_id")) != order_id:
        raise BillingError("Payment was made for a different order.")
    if int(payment.get("amount", -1)) != amount:
        raise BillingError("Payment amount did not match the order.")
    if str(payment.get("currency", "")).upper() != currency.upper():
        raise BillingError("Payment currency did not match the order.")
    if str(payment.get("status", "")) != "captured" or not payment.get(
        "captured", False
    ):
        raise BillingError("Payment has not been captured yet.")
