"""Security and configuration regression checks for paid checkout."""

from __future__ import annotations

import hashlib
import hmac
import os
import unittest
from unittest.mock import patch

from core.billing import (
    BillingError,
    validate_captured_payment,
    verify_payment_signature,
    verify_webhook_signature,
)
from core.config import get_settings


class BillingTests(unittest.TestCase):
    def test_checkout_signature_uses_stored_order_and_payment(self) -> None:
        secret = "test-secret"
        signature = hmac.new(
            secret.encode(), b"order_123|pay_456", hashlib.sha256
        ).hexdigest()
        self.assertTrue(
            verify_payment_signature("order_123", "pay_456", signature, secret)
        )
        self.assertFalse(
            verify_payment_signature("order_changed", "pay_456", signature, secret)
        )

    def test_webhook_signature_is_over_raw_body(self) -> None:
        body = b'{"event":"payment.captured"}'
        signature = hmac.new(b"hook-secret", body, hashlib.sha256).hexdigest()
        self.assertTrue(
            verify_webhook_signature(body, signature, "hook-secret")
        )
        self.assertFalse(
            verify_webhook_signature(body + b" ", signature, "hook-secret")
        )

    def test_only_exact_captured_payment_is_accepted(self) -> None:
        payment = {
            "id": "pay_456",
            "order_id": "order_123",
            "amount": 49900,
            "currency": "INR",
            "status": "captured",
            "captured": True,
        }
        validate_captured_payment(
            payment,
            payment_id="pay_456",
            order_id="order_123",
            amount=49900,
            currency="INR",
        )
        with self.assertRaises(BillingError):
            validate_captured_payment(
                {**payment, "amount": 499},
                payment_id="pay_456",
                order_id="order_123",
                amount=49900,
                currency="INR",
            )

    def test_checkout_requires_every_server_secret_and_explicit_flag(self) -> None:
        environment = {
            "SUPABASE_ENABLED": "true",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test",
            "SUPABASE_SECRET_KEY": "sb_secret_test",
            "PAYMENTS_ENABLED": "true",
            "RAZORPAY_KEY_ID": "rzp_test_123",
            "RAZORPAY_KEY_SECRET": "provider-secret",
            "RAZORPAY_WEBHOOK_SECRET": "webhook-secret",
        }
        with patch.dict(os.environ, environment, clear=True):
            self.assertTrue(get_settings().billing_ready)
        environment.pop("RAZORPAY_WEBHOOK_SECRET")
        with patch.dict(os.environ, environment, clear=True):
            self.assertFalse(get_settings().billing_ready)


if __name__ == "__main__":
    unittest.main()
