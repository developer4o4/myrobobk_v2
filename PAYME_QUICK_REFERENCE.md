# 🎯 Payme Quick Reference

## ⚡ Most Used Commands

### Check Payment Status
```python
from apps.payment.models import PaymeTransaction
from apps.payment.utils import get_transaction_status

# Specific transaction
tx = PaymeTransaction.objects.get(id="transaction-id")
print(f"Status: {tx.get_state_display()}, Balance: {tx.amount_som()} som")

# Or use utility
status = get_transaction_status("transaction-id")
print(status)
```

### Get User Balance
```python
from apps.users.models import User
user = User.objects.get(id="user-id")
print(f"Balance: {user.balance} som")
```

### Create Test Transaction
```python
from apps.payment.models import PaymeTransaction
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

tx = PaymeTransaction.objects.create(
    user=user,
    amount_tiyin=100000,  # 1000 som
    state=PaymeTransaction.STATE_PENDING
)
print(f"Created: {tx.id}")
```

### View All Transactions
```python
from apps.payment.models import PaymeTransaction

# All
all_tx = PaymeTransaction.objects.all()

# By user
user_tx = PaymeTransaction.objects.filter(user_id="user-id")

# Completed only
done_tx = PaymeTransaction.objects.filter(state=PaymeTransaction.STATE_DONE)

# Last 10
recent = PaymeTransaction.objects.all()[:10]
```

### Daily Statistics
```python
from apps.payment.utils import get_daily_stats
from datetime import datetime

# Today
stats = get_daily_stats()

# Specific date
stats = get_daily_stats(datetime(2026, 5, 8).date())

print(f"Completed: {stats['completed']['count']} | {stats['completed']['total_som']} som")
print(f"Pending: {stats['pending']['count']} | {stats['pending']['total_som']} som")
print(f"Canceled: {stats['canceled']['count']} | {stats['canceled']['total_som']} som")
```

---

## 🔄 API Requests

### Create Checkout Link
```bash
curl -X POST http://localhost:8000/payment/checkout/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 10000
  }'

# Response
{
  "order_id": "uuid-here",
  "payment_url": "https://checkout.payme.uz/m=...",
  "amount_som": 10000,
  "status": "pending"
}
```

### Get Transaction History
```bash
curl -X GET http://localhost:8000/payment/history/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "transactions": [
    {
      "id": "tx-id",
      "amount_som": 1000,
      "amount_tiyin": 100000,
      "state": 2,
      "state_display": "Done",
      "created_at": "2026-05-08T10:30:00Z",
      "payme_transaction_id": "..."
    }
  ]
}
```

---

## 📊 Admin Commands

### Payment Report
```bash
# Today
python manage.py payment_report

# Specific date
python manage.py payment_report --date 2026-05-07

# Last 7 days
python manage.py payment_report --range 7
```

### Django Shell Commands
```bash
python manage.py shell
```

```python
# Import
from apps.payment.models import PaymeTransaction as Tx
from apps.users.models import User

# Quick stats
done = Tx.objects.filter(state=Tx.STATE_DONE).count()
total = sum(t.amount_som() for t in Tx.objects.filter(state=Tx.STATE_DONE))
print(f"Completed: {done} transactions, Total: {total} som")

# Find pending > 24h
from django.utils import timezone
from datetime import timedelta
old = timezone.now() - timedelta(hours=24)
stuck = Tx.objects.filter(state=Tx.STATE_PENDING, created_at__lt=old)
print(f"Stuck: {stuck.count()}")

# User total spent
user = User.objects.get(phone="998901234567")
from apps.payment.utils import get_user_total_spent
spent = get_user_total_spent(user.id)
print(f"Total spent: {spent} som")
```

---

## 🧪 Testing

### Run Tests
```bash
python manage.py test apps.payment
```

### Test Webhook Locally
```bash
# Get credentials
CREDS=$(echo -n 'Paycom:mCQhHt0kiRkMM#ccT2eOieiZkp84dC5MSUgO' | base64)

# CheckPerformTransaction
curl -X POST http://localhost:8000/payment/payme/webhook/ \
  -H "Authorization: Basic $CREDS" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "CheckPerformTransaction",
    "params": {
      "account": {"user_id": "tx-id"},
      "amount": 100000
    },
    "id": 1
  }'

# CreateTransaction
curl -X POST http://localhost:8000/payment/payme/webhook/ \
  -H "Authorization: Basic $CREDS" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "CreateTransaction",
    "params": {
      "account": {"user_id": "tx-id"},
      "amount": 100000,
      "id": "payme-tx-id",
      "time": 1234567890
    },
    "id": 2
  }'

# PerformTransaction
curl -X POST http://localhost:8000/payment/payme/webhook/ \
  -H "Authorization: Basic $CREDS" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "PerformTransaction",
    "params": {
      "id": "payme-tx-id",
      "time": 1234567891
    },
    "id": 3
  }'
```

---

## 🛠️ Debugging

### Check Transaction Details
```python
from apps.payment.models import PaymeTransaction

tx = PaymeTransaction.objects.get(id="tx-id")

# All fields
print(f"""
ID: {tx.id}
User: {tx.user.phone}
Amount: {tx.amount_som()} som
State: {tx.get_state_display()}
Payme ID: {tx.payme_transaction_id}
Created: {tx.created_at}
Updated: {tx.updated_at}
""")
```

### Check User Balance Changes
```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, balance, date_joined 
        FROM users_user 
        WHERE id = %s
    """, ["user-id"])
    print(cursor.fetchone())
```

### View Recent Transactions
```python
from apps.payment.models import PaymeTransaction

txs = (PaymeTransaction.objects
    .select_related("user")
    .order_by("-created_at")[:20])

for tx in txs:
    print(f"{tx.id} | {tx.user.phone} | {tx.amount_som()} | {tx.get_state_display()}")
```

### Admin Panel Shortcuts
```
1. Go to: http://localhost:8000/admin/payment/paymetransaction/
2. Filter by Status: Completed, Pending, Canceled
3. Search by phone or transaction ID
4. Click transaction to view all details
5. Timestamps in "Timestamps" section (collapsed)
```

---

## ⚠️ Common Issues

### Issue: "Hisob topilmadi" (Account not found)
```python
# Check if transaction exists
from apps.payment.models import PaymeTransaction
tx = PaymeTransaction.objects.filter(id="tx-id").exists()
# If False, create it first
```

### Issue: "Noto'g'ri summa" (Invalid amount)
```python
# Amount must match EXACTLY
# Frontend: amount * 100 = amount_tiyin
# Check: 
tx.amount_tiyin == (frontend_amount * 100)
```

### Issue: Balance not updated
```python
# Check transaction state
from apps.payment.models import PaymeTransaction
tx = PaymeTransaction.objects.get(id="tx-id")
print(f"State: {tx.state} (Should be 2 for DONE)")

# Check user balance
user = tx.user
user.refresh_from_db()
print(f"Balance: {user.balance}")
```

### Issue: Webhook not working
```python
# 1. Check auth header
import base64
auth = "Basic " + base64.b64encode(b"Paycom:mCQhHt0kiRkMM#ccT2eOieiZkp84dC5MSUgO").decode()
print(f"Header: {auth}")

# 2. Check webhook URL in Payme
# https://yourdomain.com/payment/payme/webhook/

# 3. Check Django logs
tail -f logs/web/django.log
```

---

## 📱 Frontend Integration

### React Hook
```jsx
const usePaymeCheckout = (token) => {
  const checkout = async (amount) => {
    const response = await fetch('/payment/checkout/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ amount })
    });
    return response.json();
  };
  return { checkout };
};

// Usage
const { checkout } = usePaymeCheckout(token);
const data = await checkout(10000);
window.location.href = data.payment_url;
```

---

## 📋 State Transitions

```
PENDING (1)
    ↓
    ├─→ DONE (2)         [PerformTransaction] ✅
    │    └─→ CANCELED (-1)  [Not allowed - error]
    │
    └─→ CANCELED (-1)    [CancelTransaction] ❌

Flow:
1. POST /checkout/ → STATE_PENDING (0)
2. Payme CreateTransaction → STATE_PENDING (1)
3. User pays on Payme
4a. Payme PerformTransaction → STATE_DONE (2) + Balance += amount
4b. Payme CancelTransaction → STATE_CANCELED (-1)
```

---

## 💡 Tips & Tricks

### Quick Balance Check
```python
from django.contrib.auth import get_user_model
User = get_user_model()
users = User.objects.values('phone', 'balance').order_by('-balance')[:10]
# Top 10 users by balance
```

### Monthly Revenue
```python
from django.utils import timezone
from datetime import datetime
from apps.payment.models import PaymeTransaction

month = timezone.now().month
year = timezone.now().year

monthly = PaymeTransaction.objects.filter(
    state=PaymeTransaction.STATE_DONE,
    created_at__month=month,
    created_at__year=year
)

total = sum(t.amount_som() for t in monthly)
print(f"Monthly revenue: {total} som")
```

### Export to CSV
```python
import csv
from django.http import HttpResponse
from apps.payment.models import PaymeTransaction

response = HttpResponse(content_type='text/csv')
response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

writer = csv.writer(response)
writer.writerow(['ID', 'User', 'Amount (som)', 'State', 'Created'])

for tx in PaymeTransaction.objects.all():
    writer.writerow([
        tx.id,
        tx.user.phone,
        tx.amount_som(),
        tx.get_state_display(),
        tx.created_at
    ])

return response
```

---

**Last Updated:** 2026-05-08  
**Version:** 1.0
