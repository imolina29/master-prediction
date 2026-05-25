from unittest.mock import MagicMock

import pytest

from backend.subscriptions.models import Payment, Subscription
from backend.subscriptions.service import SubscriptionService


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def service(mock_client):
    return SubscriptionService(mock_client)


def test_subscription_model():
    sub = Subscription(
        telegram_user_id="12345",
        telegram_username="testuser",
        stripe_customer_id="cus_test",
        stripe_subscription_id="sub_test",
        plan="monthly",
        status="active",
    )
    assert sub.telegram_user_id == "12345"
    assert sub.plan == "monthly"
    assert sub.status == "active"


def test_payment_model():
    pay = Payment(
        subscription_id="uuid-123",
        stripe_payment_intent_id="pi_test",
        amount_usd=19.99,
        status="succeeded",
    )
    assert pay.amount_usd == 19.99
    assert pay.status == "succeeded"


def test_create_subscription(service, mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "uuid-1", "telegram_user_id": "12345", "status": "active"}]
    )

    result = service.create_subscription(
        telegram_user_id="12345",
        telegram_username="testuser",
        stripe_customer_id="cus_test",
        stripe_subscription_id="sub_test",
        plan="monthly",
    )
    assert result["telegram_user_id"] == "12345"
    mock_client.table.assert_called_with("subscriptions")


def test_get_active_subscription(service, mock_client):
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "uuid-1", "status": "active", "telegram_user_id": "12345"}]
    )

    result = service.get_active_subscription("12345")
    assert result is not None
    assert result["status"] == "active"


def test_get_active_subscription_none(service, mock_client):
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )

    result = service.get_active_subscription("99999")
    assert result is None


def test_cancel_subscription(service, mock_client):
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[{"id": "uuid-1", "status": "cancelled"}])
    )

    service.cancel_subscription("sub_test")
    mock_client.table.assert_called_with("subscriptions")


def test_record_payment(service, mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "pay-1"}]
    )

    result = service.record_payment(
        subscription_id="uuid-1",
        stripe_payment_intent_id="pi_test",
        amount_usd=19.99,
        status="succeeded",
    )
    assert result is not None
    mock_client.table.assert_called_with("payments")


def test_get_all_subscriptions(service, mock_client):
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value.order.return_value.execute.return_value = MagicMock(
        data=[
            {"id": "1", "status": "active", "plan": "monthly"},
            {"id": "2", "status": "cancelled", "plan": "quarterly"},
        ]
    )

    result = service.get_all_subscriptions()
    assert len(result) == 2


def test_get_all_payments(service, mock_client):
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value.order.return_value.execute.return_value = MagicMock(
        data=[{"id": "p1", "amount_usd": 19.99}]
    )

    result = service.get_all_payments()
    assert len(result) == 1
