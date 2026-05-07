"""
Tests for Payme payment integration
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
import base64

from .models import PaymeTransaction
from .services import payme_checkout_link

User = get_user_model()


class PaymeTransactionModelTests(TestCase):
    """Test PaymeTransaction model"""

    def setUp(self):
        self.user = User.objects.create_user(phone="998901234567")

    def test_create_transaction(self):
        """Test creating a transaction"""
        tx = PaymeTransaction.objects.create(
            user=self.user,
            amount_tiyin=100000,  # 1000 som
            state=PaymeTransaction.STATE_PENDING,
        )
        self.assertEqual(tx.user, self.user)
        self.assertEqual(tx.amount_tiyin, 100000)
        self.assertEqual(tx.amount_som(), 1000)
        self.assertEqual(tx.state, PaymeTransaction.STATE_PENDING)

    def test_transaction_str(self):
        """Test transaction string representation"""
        tx = PaymeTransaction.objects.create(
            user=self.user,
            amount_tiyin=100000,
            state=PaymeTransaction.STATE_PENDING,
        )
        self.assertIn("1000.00", str(tx))
        self.assertIn("Pending", str(tx))


class PaymeCheckoutLinkAPITests(APITestCase):
    """Test Payme checkout link creation"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(phone="998901234567", password="test")
        self.token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token.access_token}")

    def test_create_checkout_link(self):
        """Test creating checkout link"""
        response = self.client.post(
            "/payment/checkout/",
            {"amount": 10000},
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("payment_url", response.data)
        self.assertIn("order_id", response.data)
        self.assertEqual(response.data["amount_som"], 10000)

    def test_invalid_amount(self):
        """Test with invalid amount"""
        response = self.client.post(
            "/payment/checkout/",
            {"amount": 0},
            format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_request(self):
        """Test without authentication"""
        client = APIClient()
        response = client.post(
            "/payment/checkout/",
            {"amount": 10000},
            format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_transaction_created(self):
        """Test that transaction is created in database"""
        response = self.client.post(
            "/payment/checkout/",
            {"amount": 5000},
            format="json"
        )
        self.assertEqual(response.status_code, 200)
        
        # Check transaction in DB
        tx = PaymeTransaction.objects.get(id=response.data["order_id"])
        self.assertEqual(tx.user, self.user)
        self.assertEqual(tx.amount_tiyin, 500000)
        self.assertEqual(tx.state, PaymeTransaction.STATE_PENDING)


class PaymeWebhookTests(TestCase):
    """Test Payme webhook endpoints"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(phone="998901234567")
        self.login = "Paycom"
        self.password = "mCQhHt0kiRkMM#ccT2eOieiZkp84dC5MSUgO"

    def _get_auth_header(self):
        """Get Basic auth header"""
        credentials = base64.b64encode(
            f"{self.login}:{self.password}".encode()
        ).decode()
        return f"Basic {credentials}"

    def test_webhook_auth_required(self):
        """Test that webhook requires authentication"""
        response = self.client.post(
            "/payment/payme/webhook/",
            content_type="application/json",
            data='{"jsonrpc": "2.0", "method": "CheckPerformTransaction", "id": 1}'
        )
        self.assertEqual(response.status_code, 401)

    def test_check_perform_transaction_not_found(self):
        """Test CheckPerformTransaction with non-existent transaction"""
        response = self.client.post(
            "/payment/payme/webhook/",
            content_type="application/json",
            HTTP_AUTHORIZATION=self._get_auth_header(),
            data='''{
                "jsonrpc": "2.0",
                "method": "CheckPerformTransaction",
                "params": {"account": {"user_id": "non-existent"}, "amount": 100000},
                "id": 1
            }'''
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("error", response_data)
        self.assertEqual(response_data["error"]["code"], -31050)

    def test_create_transaction_flow(self):
        """Test full transaction creation flow"""
        # 1. Create transaction via API
        tx = PaymeTransaction.objects.create(
            user=self.user,
            amount_tiyin=100000,
            state=PaymeTransaction.STATE_PENDING,
        )

        # 2. Send CreateTransaction webhook
        response = self.client.post(
            "/payment/payme/webhook/",
            content_type="application/json",
            HTTP_AUTHORIZATION=self._get_auth_header(),
            data=f'''{{
                "jsonrpc": "2.0",
                "method": "CreateTransaction",
                "params": {{
                    "account": {{"user_id": "{tx.id}"}},
                    "amount": 100000,
                    "id": "payme-123",
                    "time": 1234567890
                }},
                "id": 1
            }}'''
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("result", response_data)

        # 3. Verify transaction updated
        tx.refresh_from_db()
        self.assertEqual(tx.payme_transaction_id, "payme-123")
        self.assertEqual(tx.state, PaymeTransaction.STATE_PENDING)

    def test_perform_transaction_adds_balance(self):
        """Test that PerformTransaction adds balance to user"""
        initial_balance = self.user.balance
        
        # Create transaction
        tx = PaymeTransaction.objects.create(
            user=self.user,
            amount_tiyin=100000,
            payme_transaction_id="payme-123",
            create_time=1234567890,
            state=PaymeTransaction.STATE_PENDING,
        )

        # Send PerformTransaction
        response = self.client.post(
            "/payment/payme/webhook/",
            content_type="application/json",
            HTTP_AUTHORIZATION=self._get_auth_header(),
            data=f'''{{
                "jsonrpc": "2.0",
                "method": "PerformTransaction",
                "params": {{
                    "id": "payme-123",
                    "time": 1234567891
                }},
                "id": 2
            }}'''
        )
        self.assertEqual(response.status_code, 200)

        # Verify balance updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, initial_balance + Decimal("1000"))

        # Verify transaction state
        tx.refresh_from_db()
        self.assertEqual(tx.state, PaymeTransaction.STATE_DONE)

    def test_cancel_transaction(self):
        """Test CancelTransaction"""
        tx = PaymeTransaction.objects.create(
            user=self.user,
            amount_tiyin=100000,
            payme_transaction_id="payme-123",
            create_time=1234567890,
            state=PaymeTransaction.STATE_PENDING,
        )

        response = self.client.post(
            "/payment/payme/webhook/",
            content_type="application/json",
            HTTP_AUTHORIZATION=self._get_auth_header(),
            data=f'''{{
                "jsonrpc": "2.0",
                "method": "CancelTransaction",
                "params": {{
                    "id": "payme-123",
                    "time": 1234567891,
                    "reason": 1
                }},
                "id": 3
            }}'''
        )
        self.assertEqual(response.status_code, 200)

        tx.refresh_from_db()
        self.assertEqual(tx.state, PaymeTransaction.STATE_CANCELED)


class PaymeServicesTests(TestCase):
    """Test Payme service functions"""

    def test_payme_checkout_link(self):
        """Test checkout link generation"""
        link = payme_checkout_link(
            order_id="test-123",
            amount_tiyin=100000,
            lang="uz"
        )
        self.assertIn("https://checkout.payme.uz", link)
        self.assertIn("test-123", link)
        self.assertIn("1000000", link)


class PaymentUtilsTests(TestCase):
    """Test payment utilities"""

    def setUp(self):
        self.user = User.objects.create_user(phone="998901234567")

    def test_get_user_balance(self):
        """Test getting user balance"""
        from .utils import get_user_balance
        
        balance = get_user_balance(self.user.id)
        self.assertEqual(balance, Decimal("0"))

    def test_add_balance(self):
        """Test adding balance"""
        from .utils import add_balance
        
        new_balance = add_balance(self.user.id, Decimal("1000"))
        self.assertEqual(new_balance, Decimal("1000"))
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("1000"))

    def test_get_transaction_status(self):
        """Test getting transaction status"""
        from .utils import get_transaction_status
        
        tx = PaymeTransaction.objects.create(
            user=self.user,
            amount_tiyin=100000,
            state=PaymeTransaction.STATE_DONE,
        )
        
        status = get_transaction_status(tx.id)
        self.assertEqual(status["user_id"], self.user.id)
        self.assertEqual(status["amount_som"], 1000)
        self.assertTrue(status["is_completed"])

    def test_daily_stats(self):
        """Test daily statistics"""
        from .utils import get_daily_stats
        
        # Create some transactions
        PaymeTransaction.objects.create(
            user=self.user,
            amount_tiyin=100000,
            state=PaymeTransaction.STATE_DONE,
        )
        
        stats = get_daily_stats()
        self.assertEqual(stats["completed"]["count"], 1)
        self.assertEqual(stats["completed"]["total_som"], 1000)
